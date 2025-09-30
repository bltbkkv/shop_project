from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from django.core.validators import validate_email, MinValueValidator, MaxValueValidator
from django.utils.translation import gettext_lazy as _
from decimal import Decimal


class User(AbstractUser):
    email = models.EmailField(_("Email address"), unique=True, validators=[validate_email])

    ROLE_CHOICES = (
        ("customer", _("Покупатель")),
        ("manager", _("Менеджер")),
    )
    role = models.CharField(_("Роль"), max_length=20, choices=ROLE_CHOICES, default="customer")

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["username"]

    def __str__(self):
        return self.email


class Category(models.Model):
    name = models.CharField(_("Название категории"), max_length=200)
    slug = models.SlugField(_("Слаг"), unique=True)

    class Meta:
        verbose_name = _("Категория")
        verbose_name_plural = _("Категории")

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name="products", verbose_name=_("Категория"))
    name = models.CharField(_("Название товара"), max_length=255)
    description = models.TextField(_("Описание"), blank=True)
    price_usd = models.DecimalField(_("Цена (USD)"), max_digits=10, decimal_places=2)
    image = models.ImageField(_("Изображение"), upload_to="products/", blank=True, null=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    stock = models.PositiveIntegerField(_("Остаток на складе"), default=0)

    def price_in_currency(self, currency: str) -> Decimal:
        rates = getattr(settings, "CURRENCY_RATES", {"USD": 1})
        base = self.price_usd
        rate = Decimal(rates.get(currency.upper(), 1))
        return (base * rate).quantize(Decimal("0.01"))

    def __str__(self):
        return self.name


class PromoCode(models.Model):
    code = models.CharField(_("Промокод"), max_length=50, unique=True)
    discount_percent = models.PositiveIntegerField(
        _("Скидка (%)"),
        validators=[MinValueValidator(1), MaxValueValidator(100)],
        null=True, blank=True
    )
    discount_amount = models.DecimalField(
        _("Скидка (фикс.)"),
        max_digits=10, decimal_places=2, null=True, blank=True
    )
    active = models.BooleanField(_("Активен"), default=True)
    valid_until = models.DateTimeField(_("Действителен до"), null=True, blank=True)

    def apply_discount(self, amount: Decimal) -> Decimal:
        if not self.active:
            return amount
        if self.discount_percent:
            amount -= amount * Decimal(self.discount_percent) / Decimal(100)
        if self.discount_amount:
            amount -= self.discount_amount
        return max(amount, Decimal("0.00"))

    def __str__(self):
        return self.code


class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="cart", verbose_name=_("Пользователь"))
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="carts", verbose_name=_("Промокод"))

    def total(self, currency="USD") -> Decimal:
        items = self.items.all()
        total = sum([i.subtotal(currency) for i in items], Decimal("0.00"))
        if self.promo_code:
            total = self.promo_code.apply_discount(total)
        return total

    def __str__(self):
        return f"Cart({self.user.email})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items", verbose_name=_("Корзина"))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Товар"))
    quantity = models.PositiveIntegerField(_("Количество"), default=1)

    def subtotal(self, currency="USD") -> Decimal:
        return self.product.price_in_currency(currency) * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Order(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders", verbose_name=_("Пользователь"))
    promo_code = models.ForeignKey(PromoCode, null=True, blank=True,
                                   on_delete=models.SET_NULL, related_name="orders", verbose_name=_("Промокод"))
    total_price = models.DecimalField(
        _("Итоговая сумма"),
        max_digits=12,
        decimal_places=2,
        default=0
    )
    currency = models.CharField(_("Валюта"), max_length=3, default="USD")
    paid = models.BooleanField(_("Оплачен"), default=False)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    address = models.ForeignKey("Address", null=True, blank=True, on_delete=models.SET_NULL, related_name="orders", verbose_name=_("Адрес"))

    STATUS_CHOICES = (
        ("new", _("Новый")),
        ("paid", _("Оплачен")),
        ("cancelled", _("Отменён")),
        ("delivered", _("Доставлен")),
    )

    status = models.CharField(_("Статус"), max_length=20, choices=STATUS_CHOICES, default="new")

    def __str__(self):
        return f"Order {self.id} by {self.user.email}"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items", verbose_name=_("Заказ"))
    product = models.ForeignKey(Product, on_delete=models.CASCADE, verbose_name=_("Товар"))
    price = models.DecimalField(_("Цена"), max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField(_("Количество"), default=1)

    def subtotal(self):
        return self.price * self.quantity

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"


class Review(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("Товар"))
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="reviews", verbose_name=_("Пользователь"))
    rating = models.PositiveIntegerField(_("Оценка"), validators=[MinValueValidator(1), MaxValueValidator(5)])
    text = models.TextField(_("Текст отзыва"), blank=True)
    created_at = models.DateTimeField(_("Дата создания"), auto_now_add=True)
    approved = models.BooleanField(_("Одобрен"), default=False)
    status = models.CharField(
        _("Статус модерации"),
        choices=[
            ("pending", _("Ожидает")),
            ("approved", _("Одобрен")),
            ("rejected", _("Отклонён"))
        ],
        default="pending"
    )

    class Meta:
        unique_together = ("product", "user")
        verbose_name = _("Отзыв")
        verbose_name_plural = _("Отзывы")

    def __str__(self):
        return f"{self.user.email} on {self.product.name}: {self.rating}"


class Address(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="addresses", verbose_name=_("Пользователь"))
    street = models.CharField(_("Улица"), max_length=255)
    city = models.CharField(_("Город"), max_length=100)
    postal_code = models.CharField(_("Почтовый индекс"), max_length=20)
    country = models.CharField(_("Страна"), max_length=100)
    is_default = models.BooleanField(_("По умолчанию"), default=False)

    def __str__(self):
        return f"{self.street}, {self.city}, {self.country}"
