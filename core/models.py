
from django.conf import settings
from decimal import Decimal
from django.db import models


class PasswordResetOTP(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="password_reset_otps",
    )
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    last_sent_at = models.DateTimeField()
    attempts = models.PositiveSmallIntegerField(default=0)
    is_verified = models.BooleanField(default=False)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"OTP record for user ID {self.user_id}"


class DistributorProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="distributor_profile",
    )
    phone = models.CharField(max_length=10, unique=True)

    def __str__(self):
        return self.user.email


class Customer(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(max_length=254)
    phone = models.CharField(max_length=10)
    address = models.TextField()
    city = models.CharField(max_length=100)
    state = models.CharField(max_length=100)
    postal_code = models.CharField(max_length=10)

    gst_number = models.CharField(
        max_length=15,
        blank=True,
        null=True,
        unique=True,
    )

    # Link each customer to the distributor who created the record.
    distributor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="customers",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["name"]
        verbose_name = "Customer"
        verbose_name_plural = "Customers"


from django.db import models
from django.core.validators import MinValueValidator


class Category(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name_plural = "Categories"
        ordering = ["name"]

    def __str__(self):
        return self.name


class Product(models.Model):

    GST_CHOICES = [
        ("0", "0%"),
        ("5", "5%"),
        ("12", "12%"),
        ("18", "18%"),
        ("28", "28%"),
    ]

    UNIT_CHOICES = [
        ("piece", "Piece"),
        ("kg", "Kilogram"),
        ("gram", "Gram"),
        ("litre", "Litre"),
        ("ml", "Millilitre"),
        ("box", "Box"),
        ("packet", "Packet"),
        ("dozen", "Dozen"),
    ]

    name = models.CharField(max_length=200)

    product_code = models.CharField(
        max_length=50,
        unique=True
    )

    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name="products"
    )

    description = models.TextField(blank=True)

    price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    stock = models.PositiveIntegerField(default=0)

    gst_rate = models.CharField(
        max_length=5,
        choices=GST_CHOICES,
        default="18"
    )

    unit = models.CharField(
        max_length=20,
        choices=UNIT_CHOICES,
        default="piece"
    )

    barcode = models.CharField(
        max_length=100,
        unique=True,
        blank=True,
        null=True
    )

    is_active = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return f"{self.name} ({self.product_code})"


from django.db import models
from django.utils import timezone
import uuid


class Invoice(models.Model):
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("paid", "Paid"),
        ("pending", "Pending"),
        ("cancelled", "Cancelled"),
    ]

    invoice_number = models.CharField(
        max_length=30,
        unique=True,
        blank=True
    )

    customer = models.ForeignKey(
        "core.Customer",
        on_delete=models.PROTECT,
        related_name="invoices"
    )

    invoice_date = models.DateTimeField(default=timezone.now)

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending"
    )

    subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    gst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    total_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if not self.invoice_number:
            self.invoice_number = (
                f"INV-{uuid.uuid4().hex[:12].upper()}"
            )
        super().save(*args, **kwargs)

    def __str__(self):
        return self.invoice_number


class InvoiceItem(models.Model):
    invoice = models.ForeignKey(
        Invoice,
        on_delete=models.CASCADE,
        related_name="items"
    )

    product = models.ForeignKey(
        "core.Product",
        on_delete=models.PROTECT,
        related_name="invoice_items"
    )

    quantity = models.PositiveIntegerField(default=1)

    unit_price = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    gst_rate = models.DecimalField(
        max_digits=5,
        decimal_places=2,
        default=0
    )

    line_subtotal = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    gst_amount = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    line_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0
    )

    
from decimal import Decimal

def save(self, *args, **kwargs):

    # Get price and GST from the selected product
    if self.product_id:
        self.unit_price = self.product.price
        self.gst_rate = self.product.gst_rate

    # Convert values into Decimal
    self.unit_price = Decimal(str(self.unit_price))
    self.gst_rate = Decimal(str(self.gst_rate or 0))

    # Calculate invoice item amounts
    self.line_subtotal = self.unit_price * self.quantity

    self.gst_amount = (
        self.line_subtotal * self.gst_rate / Decimal("100")
    )

    self.line_total = self.line_subtotal + self.gst_amount

    super().save(*args, **kwargs)