from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import User, Department
from django.utils.translation import gettext_lazy as _

admin.site.site_header = 'QHub'
EMPTY_VALUE_DISPLAY = '<пусто>'


@admin.register(User)
class UserAdmin(UserAdmin):
    """Панель настройки пользователей"""
    list_display = ["username", "email", "first_name",
                    "last_name", "work_phone", "last_login"]
    search_fields = ["username", "email", "first_name", "last_name"]
    list_filter = ["department", "is_active", "is_staff", "is_superuser"]
    fieldsets = (
        (None, {"fields": ("username", "password")}),
        (_("Личная информация"),
            {"fields":
                ("last_name", "first_name", "middle_name", "email",
                    "birth_date", "rank")}),
        (_("Служебная информация"),
            {"fields":
                ("department", "work_phone")}),
        (_("Permissions"),
            {"fields":
                ("role", "is_active", "is_staff", "is_superuser",
                    "groups", "user_permissions")}),
        (_("Important dates"),
            {"fields":
                ("last_login", "date_joined")})
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": (
                "username",
                "first_name",
                "last_name",
                "password1",
                "password2",
                "email",
                "work_phone",
                "department"
            ),
        }),
    )
    readonly_fields = ("last_login", "date_joined")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    """Панель настройки департаментов/центров"""
    search_fields = ["title"]
