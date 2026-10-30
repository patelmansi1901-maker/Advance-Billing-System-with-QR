
from django.contrib import admin
from .models import Customer

from django.contrib import admin
from .models import DistributorProfile, PasswordResetOTP


@admin.register(DistributorProfile)
class DistributorProfileAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "phone")
    search_fields = ("user__username", "user__email", "phone")


@admin.register(PasswordResetOTP)
class PasswordResetOTPAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "created_at",
        "expires_at",
        "attempts",
        "is_verified",
        "is_used",
    )
    search_fields = ("user__username", "user__email")
    list_filter = ("is_verified", "is_used", "created_at")
    readonly_fields = ("otp_hash",)


@admin.register(Customer)
class CustomerAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "email",
        "phone",
        "city",
        "state",
        "created_at",
    )

    search_fields = (
        "name",
        "email",
        "phone",
        "gst_number",
    )

    list_filter = ("city", "state", "created_at")


from django.contrib import admin
from .models import Category, Product


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active", "created_at")
    search_fields = ("name",)
    list_filter = ("is_active",)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "product_code",
        "category",
        "price",
        "stock",
        "gst_rate",
        "unit",
        "is_active",
    )

    search_fields = (
        "name",
        "product_code",
        "barcode",
    )

    list_filter = (
        "category",
        "gst_rate",
        "is_active",
    )

    list_editable = ("price", "stock", "is_active")

    readonly_fields = ("created_at", "updated_at")

    fieldsets = (
        ("Product Information", {
            "fields": (
                "name",
                "product_code",
                "category",
                "description",
            )
        }),
        ("Pricing and Inventory", {
            "fields": (
                "price",
                "stock",
                "gst_rate",
                "unit",
            )
        }),
        ("Barcode and Status", {
            "fields": (
                "barcode",
                "is_active",
            )
        }),
        ("Timestamps", {
            "fields": (
                "created_at",
                "updated_at",
            )
        }),
    )


from django.contrib import admin
from .models import Invoice, InvoiceItem


class InvoiceItemInline(admin.TabularInline):
    model = InvoiceItem
    extra = 1


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        "invoice_number",
        "customer",
        "invoice_date",
        "status",
        "total_amount",
    )

    list_filter = ("status", "invoice_date")
    search_fields = ("invoice_number", "customer__name")
    inlines = [InvoiceItemInline]


@admin.register(InvoiceItem)
class InvoiceItemAdmin(admin.ModelAdmin):
    list_display = (
        "invoice",
        "product",
        "quantity",
        "unit_price",
        "gst_rate",
        "line_total",
    )

    list_filter = ("gst_rate",)
    search_fields = ("invoice__invoice_number", "product__name")

