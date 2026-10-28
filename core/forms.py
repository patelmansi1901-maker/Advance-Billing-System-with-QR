
from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Product, Category


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product
        fields = [
            "name",
            "product_code",
            "category",
            "description",
            "price",
            "stock",
            "gst_rate",
            "unit",
            "barcode",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product name",
            }),
            "product_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "e.g. PRD001",
            }),
            "category": forms.Select(attrs={
                "class": "form-control",
            }),
            "description": forms.Textarea(attrs={
                "class": "form-control",
                "rows": 3,
                "placeholder": "Optional product description",
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter price",
                "min": "0.01",
                "step": "0.01",
            }),
            "stock": forms.NumberInput(attrs={
                "class": "form-control",
                "placeholder": "Enter available stock",
                "min": "0",
                "step": "1",
            }),
            "gst_rate": forms.Select(attrs={
                "class": "form-control",
            }),
            "unit": forms.Select(attrs={
                "class": "form-control",
            }),
            "barcode": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Optional barcode",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        # Show only active categories in the product form.
        self.fields["category"].queryset = Category.objects.filter(
            is_active=True
        )

        # Display useful required-field messages.
        for field in self.fields.values():
            field.error_messages.setdefault(
                "required", "This field is required."
            )

        self.fields["description"].required = False
        self.fields["barcode"].required = False

    def clean_name(self):
        name = self.cleaned_data["name"].strip()

        if not name:
            raise ValidationError("Product name cannot be empty.")

        return name

    def clean_product_code(self):
        code = self.cleaned_data["product_code"].strip()

        if not code:
            raise ValidationError("Product code is required.")

        return code

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price <= Decimal("0"):
            raise ValidationError("Price must be greater than 0.")

        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]

        if stock < 0:
            raise ValidationError("Stock cannot be negative.")

        return stock

    def clean_barcode(self):
        barcode = self.cleaned_data.get("barcode")

        if barcode:
            barcode = barcode.strip()

        return barcode or None
