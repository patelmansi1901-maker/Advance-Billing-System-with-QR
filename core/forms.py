from decimal import Decimal

from django import forms
from django.core.exceptions import ValidationError

from .models import Product, Category



from django import forms
from .models import Product


class ProductForm(forms.ModelForm):

    class Meta:
        model = Product

        fields = [
            'name',
            'product_code',
            'category',
            'description',
            'price',
            'stock',
            'gst_rate',
            'unit',
            'barcode',
            'is_active',
        ]

        widgets = {
            'name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product name'
            }),

            'product_code': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Enter product code'
            }),

            'category': forms.Select(attrs={
                'class': 'form-control'
            }),

            'description': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3
            }),

            'price': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0.01',
                'step': '0.01'
            }),

            'stock': forms.NumberInput(attrs={
                'class': 'form-control',
                'min': '0'
            }),

            'gst_rate': forms.Select(attrs={
                'class': 'form-control'
            }),

            'unit': forms.Select(attrs={
                'class': 'form-control'
            }),

            'barcode': forms.TextInput(attrs={
                'class': 'form-control'
            }),
        }

    def clean_name(self):
        name = self.cleaned_data.get('name')

        if not name or not name.strip():
            raise forms.ValidationError(
                "Product name is required."
            )

        return name.strip()

    def clean_price(self):
        price = self.cleaned_data.get('price')

        if price is None or price <= 0:
            raise forms.ValidationError(
                "Product price must be greater than zero."
            )

        return price

    def clean_stock(self):
        stock = self.cleaned_data.get('stock')

        if stock is None or stock < 0:
            raise forms.ValidationError(
                "Stock quantity cannot be negative."
            )

        return stock

    def clean_gst_rate(self):
            gst = self.cleaned_data.get("gst_rate")

            if not gst:
                return gst

            try:
                gst_value = Decimal(str(gst))
            except (TypeError, ValueError):
                raise forms.ValidationError(
                    "Please enter a valid GST rate."
             )

            if gst_value < 0 or gst_value > 100:
                raise forms.ValidationError(
                    "GST rate must be between 0 and 100."
                )

        # Keep the original string because GST uses model choices.
            return str(gst)
    
    def clean_product_code(self):
        code = self.cleaned_data.get('product_code')

        if code:
            code = code.strip()

            existing = Product.objects.filter(
                product_code__iexact=code
            )

            if self.instance.pk:
                existing = existing.exclude(
                    pk=self.instance.pk
                )

            if existing.exists():
                raise forms.ValidationError(
                    "This product code already exists."
                )

        return code

    def clean_barcode(self):
        barcode = self.cleaned_data.get('barcode')

        if barcode:
            barcode = barcode.strip()

            existing = Product.objects.filter(
                barcode=barcode
            )

            if self.instance.pk:
                existing = existing.exclude(
                    pk=self.instance.pk
                )

            if existing.exists():
                raise forms.ValidationError(
                    "This barcode already exists."
                )

        return barcode

from django import forms
from .models import Product


class ProductUpdateForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = [
            "name",
            "product_code",
            "category",
            "price",
            "gst_rate",
            "stock",
            "unit",
            "is_active",
        ]

        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product name",
            }),
            "product_code": forms.TextInput(attrs={
                "class": "form-control",
                "placeholder": "Enter product code",
            }),
            "category": forms.Select(attrs={
                "class": "form-control",
            }),
            "price": forms.NumberInput(attrs={
                "class": "form-control",
                "step": "0.01",
                "min": "0",
            }),
            "gst_rate": forms.Select(attrs={
                "class": "form-control",
            }),
            "stock": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "0",
            }),
            "unit": forms.Select(attrs={
                "class": "form-control",
            }),
            "is_active": forms.CheckboxInput(attrs={
                "class": "form-check-input",
            }),
        }

    def clean_price(self):
        price = self.cleaned_data["price"]

        if price < 0:
            raise forms.ValidationError(
                "Price cannot be negative."
            )

        return price

    def clean_stock(self):
        stock = self.cleaned_data["stock"]

        if stock < 0:
            raise forms.ValidationError(
                "Stock cannot be negative."
            )

        return stock

from django import forms
from django.forms import inlineformset_factory

from .models import Customer, Product, Invoice, InvoiceItem


class InvoiceForm(forms.ModelForm):

    customer = forms.ModelChoiceField(
        queryset=Customer.objects.all(),
        empty_label="Select Customer",
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )

    class Meta:
        model = Invoice
        fields = ["customer"]


class InvoiceItemForm(forms.ModelForm):

    product = forms.ModelChoiceField(
        queryset=Product.objects.all(),
        empty_label="Select Product",
        widget=forms.Select(attrs={
            "class": "form-control"
        })
    )

    class Meta:
        model = InvoiceItem
        fields = ["product", "quantity"]

        widgets = {
            "quantity": forms.NumberInput(attrs={
                "class": "form-control",
                "min": "1",
                "placeholder": "Enter quantity"
            })
        }


InvoiceItemFormSet = inlineformset_factory(
    Invoice,
    InvoiceItem,
    form=InvoiceItemForm,
    extra=1,
    can_delete=True
)


from django import forms
from django.core.exceptions import ValidationError


class InvoiceReportFilterForm(forms.Form):
    start_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
        }),
        label="Start Date"
    )

    end_date = forms.DateField(
        required=False,
        widget=forms.DateInput(attrs={
            "type": "date",
            "class": "form-control",
        }),
        label="End Date"
    )

    def clean(self):
        cleaned_data = super().clean()

        start_date = cleaned_data.get("start_date")
        end_date = cleaned_data.get("end_date")

        if start_date and end_date and start_date > end_date:
            raise ValidationError(
                "Start date cannot be later than end date."
            )

        return cleaned_data
