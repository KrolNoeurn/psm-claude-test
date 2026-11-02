from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import Branch, User


@admin.register(Branch)
class BranchAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "kind", "is_active"]


@admin.register(User)
class PMSUserAdmin(UserAdmin):
    list_display = ["username", "first_name", "last_name", "role", "branch", "is_active"]
    fieldsets = UserAdmin.fieldsets + (("Pharmacy", {"fields": ("role", "branch", "phone")}),)
