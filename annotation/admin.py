from django.contrib import admin

from django.apps import apps
from django.contrib import admin


class ListAdminMixin(object):
    def __init__(self, model, admin_site):
        self.list_display = [field.name for field in model._meta.fields]
        self.search_fields = [field.name for field in model._meta.fields if not field.is_relation]
        super(ListAdminMixin, self).__init__(model, admin_site)


models = apps.get_models()
for model in models:
    admin_class = type('AdminClass', (ListAdminMixin, admin.ModelAdmin), {})
    try:
        if str(model.__name__) == "FCMDevice":
            continue
        admin.site.register(model, admin_class)
    except admin.sites.AlreadyRegistered:
        pass

# Register your models here.
