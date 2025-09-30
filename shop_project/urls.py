from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    UserViewSet, CategoryViewSet, ProductViewSet,
    CartViewSet, OrderViewSet, ReviewViewSet, AddressViewSet,RegisterView,ProfileView, FakePaymentView
)

router = DefaultRouter()
router.register("users", UserViewSet, basename="user")
router.register("categories", CategoryViewSet, basename="category")
router.register("products", ProductViewSet, basename="product")
router.register("orders", OrderViewSet, basename="order")
router.register("reviews", ReviewViewSet, basename="review")
router.register("addresses", AddressViewSet, basename="address")

urlpatterns = [
    path("cart/", CartViewSet.as_view({"get": "list"}), name="cart-detail"),
    path("cart/add/", CartViewSet.as_view({"post": "add"}), name="cart-add"),
    path("cart/apply-promo/", CartViewSet.as_view({"post": "apply_promo"}), name="cart-apply-promo"),
    path("cart/checkout/", CartViewSet.as_view({"post": "checkout"}), name="cart-checkout"),
    path("register/", RegisterView.as_view(), name="register"),
    path("api/fake-payment/", FakePaymentView.as_view(), name="fake-payment"),
    path("profile/", ProfileView.as_view(), name="profile"),
    path("", include(router.urls)),
]
