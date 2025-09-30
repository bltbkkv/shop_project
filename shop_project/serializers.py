from rest_framework import serializers
from django.contrib.auth import get_user_model
from django.utils.translation import gettext_lazy as _
from .models import Category, Product, Cart, CartItem, Order, OrderItem, Review, PromoCode, Address

User = get_user_model()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "username"]
        extra_kwargs = {
            "email": {"label": _("Электронная почта")},
            "username": {"label": _("Имя пользователя")},
        }


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ["id", "name", "slug"]
        extra_kwargs = {
            "name": {"label": _("Название категории")},
            "slug": {"label": _("Слаг")},
        }


class ProductSerializer(serializers.ModelSerializer):
    price_converted = serializers.SerializerMethodField(label=_("Цена в выбранной валюте"))

    class Meta:
        model = Product
        fields = ["id", "name", "description", "price_usd", "price_converted", "image", "category"]
        extra_kwargs = {
            "name": {"label": _("Название товара")},
            "description": {"label": _("Описание")},
            "price_usd": {"label": _("Цена (USD)")},
            "image": {"label": _("Изображение")},
            "category": {"label": _("Категория")},
        }

    def get_price_converted(self, obj):
        request = self.context.get("request")
        currency = request.query_params.get("currency", "USD") if request else "USD"
        return obj.price_in_currency(currency)


class PromoCodeSerializer(serializers.ModelSerializer):
    class Meta:
        model = PromoCode
        fields = ["code", "discount_percent", "discount_amount", "active", "valid_until"]
        extra_kwargs = {
            "code": {"label": _("Промокод")},
            "discount_percent": {"label": _("Скидка (%)")},
            "discount_amount": {"label": _("Скидка (фикс.)")},
            "active": {"label": _("Активен")},
            "valid_until": {"label": _("Действителен до")},
        }


class CartItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField(label=_("Сумма"))

    class Meta:
        model = CartItem
        fields = ["id", "product", "quantity", "subtotal"]
        extra_kwargs = {
            "quantity": {"label": _("Количество")},
        }

    def get_subtotal(self, obj):
        request = self.context.get("request")
        currency = request.query_params.get("currency", "USD") if request else "USD"
        return obj.subtotal(currency)


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total = serializers.SerializerMethodField(label=_("Итоговая сумма"))
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = Cart
        fields = ["id", "user", "promo_code", "items", "total"]
        extra_kwargs = {
            "promo_code": {"label": _("Промокод")},
        }

    def get_total(self, obj):
        request = self.context.get("request")
        currency = request.query_params.get("currency", "USD") if request else "USD"
        return obj.total(currency)


class OrderItemSerializer(serializers.ModelSerializer):
    product = ProductSerializer(read_only=True)
    subtotal = serializers.SerializerMethodField(label=_("Сумма"))

    class Meta:
        model = OrderItem
        fields = ["id", "product", "price", "quantity", "subtotal"]
        extra_kwargs = {
            "price": {"label": _("Цена")},
            "quantity": {"label": _("Количество")},
        }

    def get_subtotal(self, obj):
        return obj.subtotal()


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    promo_code = PromoCodeSerializer(read_only=True)

    class Meta:
        model = Order
        fields = ["id", "user", "promo_code", "total_price", "currency", "paid", "created_at", "items"]
        extra_kwargs = {
            "total_price": {"label": _("Итоговая сумма")},
            "currency": {"label": _("Валюта")},
            "paid": {"label": _("Оплачен")},
            "created_at": {"label": _("Дата создания")},
        }


class ReviewSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)

    class Meta:
        model = Review
        fields = ["id", "product", "user", "rating", "text", "created_at"]
        extra_kwargs = {
            "rating": {"label": _("Оценка")},
            "text": {"label": _("Текст отзыва")},
            "created_at": {"label": _("Дата создания")},
        }


class AddressSerializer(serializers.ModelSerializer):
    class Meta:
        model = Address
        fields = ["id", "street", "city", "postal_code", "country", "is_default"]
        extra_kwargs = {
            "street": {"label": _("Улица")},
            "city": {"label": _("Город")},
            "postal_code": {"label": _("Почтовый индекс")},
            "country": {"label": _("Страна")},
            "is_default": {"label": _("По умолчанию")},
        }
