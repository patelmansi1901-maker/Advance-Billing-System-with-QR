
import qrcode
from io import BytesIO
from django.core.files.base import ContentFile
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import Invoice


@receiver(post_save, sender=Invoice)
def generate_invoice_qr(sender, instance, created, **kwargs):

    # Generate QR code only when a new invoice is created
    if created and not instance.qr_code:

        invoice_data = (
            f"Invoice ID: {instance.id}\n"
            f"Invoice Number: {instance.invoice_number}\n"
            f"Customer: {instance.customer.name}\n"
            f"Total Amount: {instance.grand_total}\n"
            f"Invoice Date: {instance.invoice_date}"
        )

        # Create QR code
        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_L,
            box_size=10,
            border=4
        )

        qr.add_data(invoice_data)
        qr.make(fit=True)

        qr_image = qr.make_image(
            fill_color="black",
            back_color="white"
        )

        # Store image in memory
        buffer = BytesIO()
        qr_image.save(buffer, format="PNG")

        # Save QR image to Invoice model
        filename = f"invoice_{instance.id}.png"

        instance.qr_code.save(
            filename,
            ContentFile(buffer.getvalue()),
            save=False
        )

        # Update only the QR field without triggering another signal
        Invoice.objects.filter(pk=instance.pk).update(
            qr_code=instance.qr_code.name
        )
