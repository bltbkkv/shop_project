from django.apps import AppConfig

class ShopProjectConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop_project"

    def ready(self):
        import shop_project.signals
