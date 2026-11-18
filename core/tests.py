from django.test import TestCase
import re

from datetime import timedelta

from django.test import TestCase, override_settings
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password
from django.utils import timezone

from django.core import mail

from rest_framework.test import APIClient

from .models import PasswordResetOTP
# Create your tests here.


class AdminRegistrationTests(TestCase):

    def setUp(self):
        self.User = get_user_model()

        self.admin = self.User.objects.create_user(
            username="testadmin",
            email="admin_test@example.com",
            password="Admin@12345",
            is_staff=True
        )

        self.client_api = APIClient()

        self.client_api.force_authenticate(
            user=self.admin
        )

        self.url = reverse("admin_register_api")

    def test_admin_registration_success(self):

        data = {
            "username": "newadmin",
            "email": "newadmin@example.com",
            "first_name": "New",
            "last_name": "Admin",
            "password": "NewAdmin@12345"
        }

        response = self.client_api.post(
            self.url,
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 201)

        new_user = self.User.objects.get(
            username="newadmin"
        )

        self.assertEqual(
            new_user.email,
            "newadmin@example.com"
        )

        self.assertTrue(new_user.is_staff)
        self.assertFalse(new_user.is_superuser)
        self.assertTrue(
            new_user.check_password("NewAdmin@12345")
        )

    def test_admin_registration_duplicate_email(self):

        data = {
            "username": "anotheradmin",
            "email": "admin_test@example.com",
            "first_name": "Another",
            "last_name": "Admin",
            "password": "AnotherAdmin@12345"
        }

        response = self.client_api.post(
            self.url,
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_registration_weak_password(self):

        data = {
            "username": "weakadmin",
            "email": "weak@example.com",
            "first_name": "Weak",
            "last_name": "Admin",
            "password": "123"
        }

        response = self.client_api.post(
            self.url,
            data,
            format="json"
        )

        self.assertEqual(response.status_code, 400)

    def test_admin_registration_requires_admin_permission(self):

        self.client_api.force_authenticate(user=None)

        data = {
            "username": "unauthorized",
            "email": "unauthorized@example.com",
            "first_name": "Test",
            "last_name": "User",
            "password": "TestPassword@123"
        }

        response = self.client_api.post(
            self.url,
            data,
            format="json"
        )

        self.assertIn(response.status_code, [401, 403])


@override_settings(
    MAILERS={
        "default": {
            "BACKEND": "django.core.mail.backends.locmem.EmailBackend"
        }
    },
    DEFAULT_FROM_EMAIL="test@example.com"
)
class AdminPasswordRecoveryTests(TestCase):

    def setUp(self):

        self.User = get_user_model()

        self.admin = self.User.objects.create_user(
            username="recoveryadmin",
            email="recovery@example.com",
            password="OldPassword@123",
            is_staff=True,
            is_active=True
        )

        self.forgot_url = reverse("admin_forgot_password")
        self.verify_url = reverse("admin_verify_otp")
        self.reset_url = reverse("admin_reset_password")

    def request_otp(self):

        response = self.client.post(
            self.forgot_url,
            {"email": self.admin.email}
        )

        self.assertEqual(response.status_code, 302)

        self.assertEqual(len(mail.outbox), 1)

        otp_record = PasswordResetOTP.objects.get(
            user=self.admin,
            is_used=False
        )

        email_body = mail.outbox[0].body

        otp_match = re.search(
            r"\b\d{6}\b",
            email_body
        )

        self.assertIsNotNone(otp_match)

        otp = otp_match.group(0)

        self.assertTrue(
            check_password(otp, otp_record.otp_hash)
        )

        return otp

    def test_otp_email_sent_successfully(self):

        self.request_otp()

        self.assertEqual(
            mail.outbox[0].to,
            [self.admin.email]
        )

        self.assertIn(
            "Password Recovery OTP",
            mail.outbox[0].subject
        )

    def test_invalid_otp_rejected(self):

        self.request_otp()

        response = self.client.post(
            self.verify_url,
            {"otp": "000000"}
        )

        self.assertEqual(response.status_code, 200)

        otp_record = PasswordResetOTP.objects.get(
            user=self.admin,
            is_used=False
        )

        self.assertEqual(otp_record.attempts, 1)
        self.assertFalse(otp_record.is_verified)

    def test_valid_otp_verification(self):

        otp = self.request_otp()

        response = self.client.post(
            self.verify_url,
            {"otp": otp}
        )

        self.assertEqual(response.status_code, 302)

        self.assertTrue(
            self.client.session.get("admin_otp_verified")
        )

        otp_record = PasswordResetOTP.objects.get(
            user=self.admin,
            is_used=False
        )

        self.assertTrue(otp_record.is_verified)

    def test_expired_otp_rejected(self):

        self.request_otp()

        otp_record = PasswordResetOTP.objects.get(
            user=self.admin,
            is_used=False
        )

        otp_record.expires_at = (
            timezone.now() - timedelta(minutes=1)
        )

        otp_record.save()

        response = self.client.post(
            self.verify_url,
            {"otp": "123456"}
        )

        self.assertEqual(response.status_code, 302)

        otp_record.refresh_from_db()

        self.assertFalse(otp_record.is_verified)

    def test_password_reset_successfully(self):

        otp = self.request_otp()

        self.client.post(
            self.verify_url,
            {"otp": otp}
        )

        response = self.client.post(
            self.reset_url,
            {
                "password": "NewPassword@123",
                "confirm_password": "NewPassword@123"
            }
        )

        self.assertEqual(response.status_code, 302)

        self.admin.refresh_from_db()

        self.assertTrue(
            self.admin.check_password("NewPassword@123")
        )

        self.assertFalse(
            self.admin.check_password("OldPassword@123")
        )

        otp_record = PasswordResetOTP.objects.get(
            user=self.admin
        )

        self.assertTrue(otp_record.is_used)
        # Verify login using the new password
        self.assertTrue(
        self.client.login(
        username="recoveryadmin",
        password="NewPassword@123"
    )
)

# Old password should no longer work
        self.client.logout()

        self.assertFalse(
        self.client.login(
        username="recoveryadmin",
        password="OldPassword@123"
    )
)

    def test_password_confirmation_mismatch(self):

        otp = self.request_otp()

        self.client.post(
            self.verify_url,
            {"otp": otp}
        )

        response = self.client.post(
            self.reset_url,
            {
                "password": "NewPassword@123",
                "confirm_password": "DifferentPassword@123"
            }
        )

        self.assertEqual(response.status_code, 200)

        self.admin.refresh_from_db()

        self.assertTrue(
            self.admin.check_password("OldPassword@123")
        )


from django.test import TestCase
from .forms import ProductForm
from .models import Category


class ProductValidationTests(TestCase):

    def valid_product_data(self):
        return {
            'name': 'Wireless Mouse',
            'product_code': 'TEST-PROD-101',
            'category': str(self.category.pk),            
            'description': 'Wireless optical mouse',
            'price': '500.00',
            'stock': '20',
            'unit': 'piece',
            'gst_rate': '18',
            'barcode': 'TESTBARCODE101',
            'is_active': True,
        }

    def test_valid_product(self):
        form = ProductForm(data=self.valid_product_data())

        self.assertTrue(
            form.is_valid(),
            form.errors
        )

    def test_empty_product_name(self):
        data = self.valid_product_data()
        data['name'] = ''

        form = ProductForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_zero_price(self):
        data = self.valid_product_data()
        data['price'] = '0'

        form = ProductForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('price', form.errors)

    def test_negative_stock(self):
        data = self.valid_product_data()
        data['stock'] = '-5'

        form = ProductForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('stock', form.errors)

    def test_invalid_gst(self):
        data = self.valid_product_data()
        data['gst_rate'] = '150'

        form = ProductForm(data=data)

        self.assertFalse(form.is_valid())
        self.assertIn('gst_rate', form.errors)

    def setUp(self):
        self.category = Category.objects.create(
            name="Electronics",
            description="Electronic products",
            is_active=True
        )
