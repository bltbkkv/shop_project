import stripe
from decimal import Decimal
from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import get_object_or_404
from django.utils.translation import gettext as translate
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.permissions import (
    AllowAny, IsAuthenticated, IsAuthenticatedOrReadOnly
)
from rest_framework.response import Response
from rest_framework.views import APIView
from django_filters.rest_framework import DjangoFilterBackend
from rest_framework.filters import SearchFilter

from django.contrib.auth import get_user_model
from .permissions import IsManager
from .models import (
    Category, Product, Cart, CartItem, Order, OrderItem,
    Review, PromoCode, Address
)
from .serializers import (
    UserSerializer, CategorySerializer, ProductSerializer,
    CartSerializer, OrderSerializer, ReviewSerializer,
    PromoCodeSerializer, AddressSerializer
)

User = get_user_model()
stripe.api_key = settings.STRIPE_SECRET_KEY


class UserViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [AllowAny]


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all().select_related("category")
    serializer_class = ProductSerializer
    filter_backends = [DjangoFilterBackend, SearchFilter]
    filterset_fields = ['category', 'price_usd']
    search_fields = ['name', 'description']

    def get_permissions(self):
        if self.action in ["create", "update", "partial_update", "destroy"]:
            return [IsManager()]
        return [IsAuthenticatedOrReadOnly()]


class CartViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def add(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        product_id = request.data.get("product_id")
        quantity = int(request.data.get("quantity", 1))
        product = get_object_or_404(Product, id=product_id)

        existing_item = CartItem.objects.filter(cart=cart, product=product).first()
        current_quantity = existing_item.quantity if existing_item else 0

        if current_quantity + quantity > product.stock:
            return Response({"error": translate("Недостаточно товара на складе")}, status=400)

        item, created_item = CartItem.objects.get_or_create(cart=cart, product=product)
        item.quantity = current_quantity + quantity
        item.save()

        return Response({"status": translate("Товар добавлен в корзину")}, status=201)

    @action(detail=False, methods=["post"])
    def apply_promo(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        code = request.data.get("code")
        promo = get_object_or_404(PromoCode, code=code, active=True)
        cart.promo_code = promo
        cart.save()
        return Response({"status": translate("Промокод применён")})

    @action(detail=False, methods=["post"])
    def checkout(self, request):
        cart, created = Cart.objects.get_or_create(user=request.user)
        currency = request.data.get("currency", "USD")
        address_id = request.data.get("address_id")
        address = get_object_or_404(Address, id=address_id, user=request.user)

        total = cart.total(currency)

        if total < Decimal("0.50"):
            return Response(
                {"error": translate("Минимальная сумма для оплаты — 0.50 USD")},
                status=status.HTTP_400_BAD_REQUEST
            )

        order = Order.objects.create(
            user=request.user,
            promo_code=cart.promo_code,
            total_price=total,
            currency=currency,
            paid=False,
            address=address,
        )

        for item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=item.product,
                price=item.product.price_in_currency(currency),
                quantity=item.quantity,
            )
            item.product.stock -= item.quantity
            item.product.save()

        cart.items.all().delete()

        if settings.STRIPE_SECRET_KEY:
            intent = stripe.PaymentIntent.create(
                amount=int(total * 100),
                currency=currency.lower(),
                metadata={"order_id": order.id},
            )
            return Response({"client_secret": intent.client_secret, "order_id": order.id})
        else:
            order.paid = True
            order.save()

            send_mail(
                subject=translate("Подтверждение заказа"),
                message=translate(
                    f"Здравствуйте, {request.user.username}!\n\n"
                    f"Ваш заказ №{order.id} успешно оформлен.\n"
                    f"Сумма: {order.total_price} {order.currency}\n"
                    f"Статус: {'Оплачен' if order.paid else 'Ожидает оплату'}\n\n"
                    f"Спасибо за покупку!"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[request.user.email],
                fail_silently=False,
            )

            return Response({"status": translate("Оплачено"), "order_id": order.id})


class OrderViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user)

class ReviewViewSet(viewsets.ModelViewSet):
    serializer_class = ReviewSerializer
    permission_classes = [IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        user = self.request.user
        if user.is_authenticated and user.role == "manager":
            return Review.objects.all()
        return Review.objects.filter(status="approved")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class AddressViewSet(viewsets.ModelViewSet):
    serializer_class = AddressSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Address.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        username = request.data.get("username")
        email = request.data.get("email")
        password = request.data.get("password")

        if not username or not email or not password:
            return Response({"error": translate("Заполните все поля")}, status=400)

        if User.objects.filter(username=username).exists():
            return Response({"error": translate("Имя пользователя уже занято")}, status=400)

        user = User.objects.create_user(username=username, email=email, password=password)
        return Response({"message": translate("Регистрация прошла успешно")}, status=201)


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role,
            "is_staff": user.is_staff,
        })


class FakePaymentView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        order_id = request.data.get("order_id")
        order = get_object_or_404(Order, id=order_id, user=request.user)
        order.status = "paid"
        order.paid = True
        order.save()
        return Response({"message": translate("Оплата прошла успешно")})
