from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.mail import send_mail
from django.conf import settings
from .models import Order


@receiver(post_save, sender=Order)
def send_order_email(sender, instance: Order, created, **kwargs):
    """

    """
    if created:
        subject = f"Ваш заказ #{instance.id} принят"
        message = (
            f"Здравствуйте, {instance.user.username or instance.user.email}!\n\n"
            f"Спасибо за ваш заказ.\n"
            f"Номер заказа: {instance.id}\n"
            f"Сумма: {instance.total_price} {instance.currency}\n"
            f"Статус оплаты: {'оплачен' if instance.paid else 'ожидает оплаты'}\n\n"
            f"С уважением,\nКоманда Shop"
        )
        recipient = [instance.user.email]
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, recipient)
