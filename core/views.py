import secrets
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth import (
    authenticate,
    get_user_model,
    login,
    logout,
)
import re
import os
import json
import base64
import qrcode
import cv2
import numpy as np
from PIL import Image
import cv2
import numpy as np
import json
from PIL import Image
from .qr_utils import decode_qr_image
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from rest_framework import generics
from rest_framework.authentication import SessionAuthentication
from rest_framework.permissions import IsAuthenticated
from .forms import InvoiceReportFilterForm
from .serializers import CustomerRegistrationSerializer
from .api_permissions import IsDistributor
from django.shortcuts import render
from datetime import datetime
from django.contrib.auth.decorators import login_required, user_passes_test
from django.template.loader import render_to_string
from django.db.models import Count, Prefetch
from django.conf import settings
from django.contrib.staticfiles import finders
from io import BytesIO
from django.http import HttpResponse, HttpResponseForbidden
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import get_template
from xhtml2pdf import pisa
from .models import Invoice
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models.deletion import ProtectedError
from django.db.models import Q
from django.db.models import Count
from .models import Customer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import request
from django.shortcuts import render
from .models import Product
from .forms import ProductForm, ProductUpdateForm
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Sum, Count, Avg
from .models import Invoice, Product, Customer
from django.utils.dateparse import parse_date
from django.http import HttpResponseForbidden
from django.contrib.auth.hashers import make_password, check_password
from django.core.mail import send_mail
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import DistributorProfile
from django.contrib.auth.models import Group
from .models import Customer
from django.db.models import Max
from .models import Invoice, InvoiceItem, Customer, Product
from decimal import Decimal, InvalidOperation
from .models import PasswordResetOTP
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import DistributorProfile
from decimal import Decimal,InvalidOperation
from .forms import InvoiceForm, InvoiceItemFormSet

User = get_user_model()

def generate_otp():
    """Generate a secure six-digit OTP."""
    return f"{secrets.randbelow(1_000_000):06d}"


def create_otp_for_user(user, request):
    now = timezone.now()
    otp = generate_otp()

    # Invalidate previous unused OTPs.
    PasswordResetOTP.objects.filter(
        user=user,
        is_used=False,
    ).update(is_used=True)

    # Store the OTP as a hash in the database.
    record = PasswordResetOTP.objects.create(
        user=user,
        otp_hash=make_password(otp),
        expires_at=now + timedelta(minutes=5),
        last_sent_at=now,
    )

    # Store only the record ID in the session.
    request.session["password_reset_otp_id"] = record.pk
    request.session.pop("password_reset_verified", None)

    # Development testing only: show OTP in the VS Code terminal.
    print(
        f"\n[BillFlow DEV OTP] Email={user.email} | "
        f"OTP={otp} | Expires at={record.expires_at}\n",
        flush=True,
    )

    return record

# ---------------- HOME PAGE ----------------

def home(request):
    return render(request, 'home.html')


# ---------------- ROLE CHECKS ----------------

def is_admin(user):
    return user.is_authenticated and user.is_active and user.is_staff


def is_distributor(user):
    return (
        user.is_authenticated
        and user.is_active
        and user.groups.filter(name='Distributor').exists()
    )


def forgot_password(request):
    notice = ""
    error = ""
    template_name = "forgot_password.html"

    if request.method == "POST":
        action = request.POST.get("action", "")

        # Step 1: Request an OTP
        if action == "request_otp":
            email = request.POST.get("email", "").strip()

            user = User.objects.filter(
                email__iexact=email,
                is_active=True,
            ).first()

            notice = (
                "If an active account uses that email, an OTP "
                "has been generated. Check the VS Code terminal."
            )

            if user:
                create_otp_for_user(user, request)
                template_name = "reset_password.html"

        # Step 2: Resend an OTP
        elif action == "resend_otp":
            template_name = "reset_password.html"
            otp_id = request.session.get("password_reset_otp_id")

            record = PasswordResetOTP.objects.filter(
                pk=otp_id,
                is_used=False,
                is_verified=False,
                user__is_active=True,
            ).first() if otp_id else None

            if not record:
                error = "Please request an OTP first."
                template_name = "forgot_password.html"
            else:
                seconds_passed = (
                    timezone.now() - record.last_sent_at
                ).total_seconds()

                if seconds_passed < 60:
                    wait = int(60 - seconds_passed)
                    error = (
                        f"Please wait {wait} seconds before resending."
                    )
                else:
                    create_otp_for_user(record.user, request)
                    notice = (
                        "A new OTP was generated. "
                        "Check the VS Code terminal."
                    )

        # Step 3: Verify the OTP
        elif action == "verify_otp":
            template_name = "reset_password.html"
            code = request.POST.get("otp", "").strip()
            otp_id = request.session.get("password_reset_otp_id")

            record = PasswordResetOTP.objects.filter(
                pk=otp_id,
                is_used=False,
                user__is_active=True,
            ).first() if otp_id else None

            if not record:
                error = "Please request a new OTP."
            elif timezone.now() >= record.expires_at:
                record.is_used = True
                record.save(update_fields=["is_used"])
                error = "OTP expired. Please request a new OTP."
            elif record.is_verified:
                notice = "OTP already verified. You can reset your password."
            elif record.attempts >= 5:
                record.is_used = True
                record.save(update_fields=["is_used"])
                error = "Too many attempts. Please request a new OTP."
            else:
                record.attempts += 1
                record.save(update_fields=["attempts"])

                if (
                    len(code) == 6
                    and code.isdigit()
                    and check_password(code, record.otp_hash)
                ):
                    record.is_verified = True
                    record.save(update_fields=["is_verified"])
                    request.session["password_reset_verified"] = record.pk
                    notice = "OTP verified successfully."
                else:
                    error = "Invalid OTP. Please try again."

        # Step 4: Reset the password
        elif action == "reset_password":
            template_name = "reset_password.html"
            otp_id = request.session.get("password_reset_verified")

            record = PasswordResetOTP.objects.filter(
                pk=otp_id,
                is_verified=True,
                is_used=False,
                user__is_active=True,
            ).first() if otp_id else None

            password = request.POST.get("new_password", "")
            confirm_password = request.POST.get("confirm_password", "")

            if not record:
                error = "Verify your OTP before resetting the password."
            elif timezone.now() >= record.expires_at:
                record.is_used = True
                record.save(update_fields=["is_used"])
                request.session.pop("password_reset_verified", None)
                error = "OTP expired. Please request a new one."
            elif password != confirm_password:
                error = "Passwords do not match."
            else:
                try:
                    validate_password(password, user=record.user)
                except ValidationError as exc:
                    error = " ".join(exc.messages)
                else:
                    user = record.user
                    user.set_password(password)
                    user.save(update_fields=["password"])

                    record.is_used = True
                    record.save(update_fields=["is_used"])

                    request.session.pop("password_reset_otp_id", None)
                    request.session.pop("password_reset_verified", None)

                    messages.success(
                        request,
                        "Password reset successfully. Please log in.",
                    )

                    return redirect(
                        "admin_login" if user.is_staff
                        else "distributor_login"
                    )

        else:
            error = "Invalid request. Please try again."

    return render(
        request,
        template_name,
        {"notice": notice, "error": error},
    )


# ---------------- ADMIN LOGIN ----------------

def admin_login(request):
    if request.user.is_authenticated:
        if is_admin(request.user):
            return redirect('admin_dashboard')

        if is_distributor(request.user):
            return redirect('distributor_dashboard')

        logout(request)

    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')

        user = authenticate(
            request,
            username=username,
            password=password
        )

        if user is not None and is_admin(user):
            login(request, user)
            return redirect('admin_dashboard')

        messages.error(
            request,
            'Invalid credentials or admin access not permitted.'
        )

    return render(request, 'admin_login.html')


# ---------------- DISTRIBUTOR LOGIN ----------------

def distributor_login(request):
    # If the user is already logged in as a Distributor
    if request.user.is_authenticated:
        if request.user.groups.filter(name="Distributor").exists():
            return redirect("distributor_dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        # Initialize the variable before using it
        matching_user = None

        # Authenticate the submitted credentials
        matching_user = authenticate(
            request,
            username=username,
            password=password
        )

        if matching_user is not None:
            # Allow only users belonging to the Distributor group
            if matching_user.groups.filter(name="Distributor").exists():
                login(request, matching_user)
                messages.success(
                    request,
                    "Welcome! You have logged in successfully."
                )
                return redirect("distributor_dashboard")

            messages.error(
                request,
                "Access denied. This account is not registered as a Distributor."
            )
        else:
            messages.error(
                request,
                "Invalid username or password."
            )

    # Display the login page for GET requests
    return render(request, "distributor_login.html")

@login_required(login_url="distributor_login")
def distributor_profile(request):
    # Only distributors can access this page
    if not request.user.groups.filter(name="Distributor").exists():
        return redirect("distributor_login")

    try:
        profile = request.user.distributor_profile
    except DistributorProfile.DoesNotExist:
        profile = None

    return render(
        request,
        "distributor_profile.html",
        {
            "user": request.user,
            "profile": profile,
        },
    )

# ---------------- ADMIN DASHBOARD ----------------

@login_required(login_url='admin_login')
def admin_dashboard(request):
    if not is_admin(request.user):
        if is_distributor(request.user):
            return redirect('distributor_dashboard')
        logout(request)
        messages.error(request, 'Admin access required.')
        return redirect('admin_login')

    context = {
        "total_customers": Customer.objects.count(),
        "total_distributors": DistributorProfile.objects.count(),
        "recent_customers": Customer.objects.order_by("-created_at")[:5],
        "total_products": Product.objects.count(),
    }
    return render(request, 'admin_dashboard.html', context)


# ---------------- DISTRIBUTOR DASHBOARD ----------------

@login_required(login_url='distributor_login')
def distributor_dashboard(request):
    if not is_distributor(request.user):
        if is_admin(request.user):
            return redirect('admin_dashboard')
        logout(request)
        messages.error(request, 'Distributor access required.')
        return redirect('distributor_login')

    # Customer has no distributor-owner field yet, so do not expose all
    # customers to each distributor. Add ownership before listing their data.
    
    my_customers = Customer.objects.filter(distributor=request.user).order_by("-id")

    context = {
    "my_customers": my_customers.count(),
    "recent_customers": my_customers[:5],
    "total_products": Product.objects.count(),
}
    return render(request, 'distributor_dashboard.html', context)


@login_required(login_url="distributor_login")
def update_distributor_profile(request):
    # Only distributors can update their profile
    if not request.user.groups.filter(name="Distributor").exists():
        return redirect("distributor_login")

    try:
        profile = request.user.distributor_profile
    except DistributorProfile.DoesNotExist:
        messages.error(
            request,
            "Your distributor profile was not found. Please contact the administrator."
        )
        return redirect("distributor_dashboard")

    errors = {}
    values = {
        "name": request.user.get_full_name(),
        "email": request.user.email,
        "phone": profile.phone,
    }

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()

        values = {
            "name": name,
            "email": email,
            "phone": phone,
        }

        User = request.user.__class__

        # Validate name
        if not name:
            errors["name"] = "Full name is required."
        elif len(name) < 2 or len(name) > 100:
            errors["name"] = "Name must be between 2 and 100 characters."
        elif not re.fullmatch(r"[A-Za-z][A-Za-z '\-]*", name):
            errors["name"] = "Enter a valid name using letters, spaces, apostrophes or hyphens."

        # Validate email
        if not email:
            errors["email"] = "Email address is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        # Prevent duplicate email addresses
        if email and User.objects.filter(
            email__iexact=email
        ).exclude(pk=request.user.pk).exists():
            errors["email"] = "This email is already in use."

        # Validate phone
        if not re.fullmatch(r"[0-9]{10}", phone):
            errors["phone"] = "Phone number must contain exactly 10 digits."
        elif DistributorProfile.objects.filter(
            phone=phone
        ).exclude(pk=profile.pk).exists():
            errors["phone"] = "This phone number is already in use."

        # Save only if all fields are valid
        if not errors:
            first_name, _, last_name = name.partition(" ")

            with transaction.atomic():
                request.user.first_name = first_name
                request.user.last_name = last_name
                request.user.email = email
                request.user.save(
                    update_fields=["first_name", "last_name", "email"]
                )

                profile.phone = phone
                profile.save(update_fields=["phone"])

            messages.success(request, "Your profile was updated successfully!")
            return redirect("distributor_profile")

    return render(
        request,
        "update_distributor_profile.html",
        {
            "errors": errors,
            "values": values,
        },
    )


def distributor_register(request):
    errors = {}
    values = {
        "name": "",
        "email": "",
        "phone": "",
    }

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip().lower()
        phone = request.POST.get("phone", "").strip()
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        values = {
            "name": name,
            "email": email,
            "phone": phone,
        }

        # Validate name
        if not name:
            errors["name"] = "Name is required."
        elif len(name) < 2 or len(name) > 100:
            errors["name"] = "Name must be between 2 and 100 characters."
        elif not re.fullmatch(r"[A-Za-z][A-Za-z '\-]*", name):
            errors["name"] = "Enter a valid name."

        # Validate email
        if not email:
            errors["email"] = "Email is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        # Validate phone
        if not re.fullmatch(r"[0-9]{10}", phone):
            errors["phone"] = "Phone number must contain exactly 10 digits."
        elif DistributorProfile.objects.filter(phone=phone).exists():
            errors["phone"] = "This phone number is already registered."

        User = get_user_model()

        # Check duplicate email
        if email and User.objects.filter(email__iexact=email).exists():
            errors["email"] = "This email is already registered."

        # Validate password
        if not password:
            errors["password"] = "Password is required."
        elif len(password) < 8:
            errors["password"] = "Password must contain at least 8 characters."
        elif len(password) > 128:
            errors["password"] = "Password cannot exceed 128 characters."

        if password != confirm_password:
            errors["confirm_password"] = "Passwords do not match."

        # Save only if all fields are valid
        if not errors:
            try:
                with transaction.atomic():
                    # Build a unique username from the email
                    base_username = re.sub(
                        r"[^a-zA-Z0-9_.@+-]",
                        "",
                        email.split("@")[0]
                    )[:140] or "distributor"

                    username = base_username
                    counter = 1

                    while User.objects.filter(
                        username=username
                    ).exists():
                        username = f"{base_username[:140]}{counter}"
                        counter += 1

                    # Create user with a securely hashed password
                    first_name, _, last_name = name.partition(" ")

                    user = User.objects.create_user(
                        username=username,
                        email=email,
                        first_name=first_name,
                        last_name=last_name,
                        password=password,
                    )

                    # Store the phone number
                    DistributorProfile.objects.create(
                        user=user,
                        phone=phone,
                    )

                    # Assign the Distributor role
                    distributor_group, _ = Group.objects.get_or_create(
                        name="Distributor"
                    )
                    user.groups.add(distributor_group)

                messages.success(
                    request,
                    "Registration successful! Please log in with your email and password."
                )
                return redirect("distributor_login")

            except Exception:
                # The transaction rolls back if saving fails.
                errors["general"] = (
                    "Registration could not be completed. "
                    "Please check your details and try again."
                )

    return render(
        request,
        "distributor_register.html",
        {
            "errors": errors,
            "values": values,
        },
    )


def customer_add(request):
    errors = {}
    values = {
        "name": "",
        "email": "",
        "phone": "",
        "address": "",
        "city": "",
        "state": "",
        "postal_code": "",
        "gst_number": "",
    }

    if request.method == "POST":
        for field in values:
            values[field] = request.POST.get(field, "").strip()

        name = values["name"]
        email = values["email"].lower()
        phone = values["phone"]
        address = values["address"]
        city = values["city"]
        state = values["state"]
        postal_code = values["postal_code"]
        gst_number = values["gst_number"].upper()

        values["email"] = email
        values["gst_number"] = gst_number

        # Name validation
        if not name:
            errors["name"] = "Customer name is required."
        elif len(name) < 2 or len(name) > 100:
            errors["name"] = "Name must contain 2 to 100 characters."

        # Email validation
        if not email:
            errors["email"] = "Email address is required."
        else:
            try:
                validate_email(email)
            except ValidationError:
                errors["email"] = "Enter a valid email address."

        # Phone validation
        if not re.fullmatch(r"[0-9]{10}", phone):
            errors["phone"] = "Phone number must contain exactly 10 digits."

        # Check whether this GST number already exists
        if gst_number and Customer.objects.filter(gst_number=gst_number).exists():
            messages.error(request,"This GST number is already registered. Please enter a different GST number."
         )
            return redirect("customer_add")

        # Address validation
        if not address:
            errors["address"] = "Billing address is required."
        elif len(address) > 500:
            errors["address"] = "Address cannot exceed 500 characters."

        # City validation
        if not city:
            errors["city"] = "City is required."
        elif len(city) > 100:
            errors["city"] = "City cannot exceed 100 characters."

        # State validation
        if not state:
            errors["state"] = "State is required."
        elif len(state) > 100:
            errors["state"] = "State cannot exceed 100 characters."

        # PIN code validation (India: 6 digits, first digit non-zero)
        if not re.fullmatch(r"[1-9][0-9]{5}", postal_code):
            errors["postal_code"] = "Enter a valid 6-digit PIN code."

        # Optional GSTIN validation
        if gst_number and not re.fullmatch(
            r"[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][A-Z0-9]Z[A-Z0-9]",
            gst_number,
        ):
            errors["gst_number"] = "Enter a valid 15-character GST number."

        # Save only when every field is valid
        if not errors:
            try:
                Customer.objects.create(
                    name=name,
                    email=email,
                    phone=phone,
                    address=address,
                    city=city,
                    state=state,
                    postal_code=postal_code,
                    gst_number=gst_number or None,
                    distributor=request.user,
                )

                messages.success(
                    request,
                    f"Customer '{name}' was added successfully!"
                )
                return redirect("customer_add")

            except ValidationError:
                errors["general"] = (
                    "Customer details could not be saved. "
                    "Please check the information."
                )

    return render(
        request,
        "customer_add.html",
        {
            "errors": errors,
            "values": values,
        },
    )


def customer_list(request):
    # Get the search text from the URL
    search_query = request.GET.get("q", "").strip()

    # Fetch all customers from the database
    customers = Customer.objects.all()

    # Filter customers if a search term is entered
    if search_query:
        customers = customers.filter(
            Q(name__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(phone__icontains=search_query)
            | Q(gst_number__icontains=search_query)
        )

    # Count the customers displayed after searching
    total_customers = customers.count()

    context = {
        "customers": customers,
        "search_query": search_query,
        "total_customers": total_customers,
    }

    return render(request, "customer_list.html", context)


@login_required
def customer_edit(request, customer_id):
    # Staff can edit any customer; other users can edit only their own.
    if request.user.is_staff:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(
            Customer,
            id=customer_id,
            distributor=request.user
        )

    if request.method == "POST":
        name = request.POST.get("name", "").strip()
        email = request.POST.get("email", "").strip()
        phone = request.POST.get("phone", "").strip()
        gst_number = request.POST.get("gst_number", "").strip()
        address = request.POST.get("address", "").strip()
        city = request.POST.get("city", "").strip()
        state = request.POST.get("state", "").strip()
        postal_code = request.POST.get("postal_code", "").strip()

        # Required field validation
        if not all([name, email, phone, address, city, state, postal_code]):
            messages.error(request, "Please fill in all required fields.")
            return render(
                request, "customer_edit.html", {"customer": customer}
            )

        # Check whether another customer already uses this GST number
        if gst_number and Customer.objects.filter(
            gst_number=gst_number
        ).exclude(id=customer.id).exists():
            messages.error(
                request,
                "This GST number is already registered to another customer."
            )
            return render(
                request, "customer_edit.html", {"customer": customer}
            )

        # Update the existing record
        customer.name = name
        customer.email = email
        customer.phone = phone
        customer.gst_number = gst_number or None
        customer.address = address
        customer.city = city
        customer.state = state
        customer.postal_code = postal_code
        customer.save()

        messages.success(request, "Customer information updated successfully!")
        return redirect("customer_list")

    return render(
        request,
        "customer_edit.html",
        {"customer": customer}
    )


@login_required
@require_POST
def customer_delete(request, customer_id):
    # Staff can delete any customer.
    # Other users can delete only customers assigned to them.
    if request.user.is_staff:
        customer = get_object_or_404(Customer, id=customer_id)
    else:
        customer = get_object_or_404(
            Customer,
            id=customer_id,
            distributor=request.user
        )

    customer.delete()

    messages.success(
        request,
        "Customer deleted successfully."
    )

    return redirect("admin_dashboard" if request.user.is_staff else "customer_list")


from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.shortcuts import render, redirect

from .forms import ProductForm


def can_manage_products(user):
    return (
        user.is_authenticated
        and user.is_active
        and (
            user.is_staff
            or user.groups.filter(name="Distributor").exists()
        )
    )



@user_passes_test(
    can_manage_products,
    login_url="/distributor-login/"
)
def add_product(request):

    if request.method == "POST":
        form = ProductForm(request.POST)

        if form.is_valid():
            product = form.save()

            messages.success(
                request,
                f"Product '{product.name}' added successfully!"
            )

            return redirect("product_list")

        messages.error(
            request,
            "Please correct the errors shown below."
        )

    else:
        form = ProductForm()

    return render(
        request,
        "product_form.html",
        {"form": form}
    )



@user_passes_test(
    can_manage_products,
    login_url="/distributor-login/"
)
def product_list(request):

    search_query = request.GET.get("q", "").strip()

    products = Product.objects.select_related(
        "category"
    ).all()

    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(product_code__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    paginator = Paginator(products.order_by("-id"), 10)

    page_obj = paginator.get_page(
        request.GET.get("page")
    )

    context = {
    "page_obj": page_obj,
    "products": page_obj.object_list,
    "search_query": search_query,

    # Product statistics
    "total_products": products.count(),
    "available_products": products.filter(stock__gt=0).count(),
    "out_of_stock": products.filter(stock=0).count(),
    }

    return render(
        request,
        "product_list.html",
        context
    )



from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from .models import Product
from .forms import ProductUpdateForm



@user_passes_test(
    can_manage_products,
    login_url="/distributor-login/"
)
def update_product(request, product_id):

    product = get_object_or_404(
        Product,
        pk=product_id
    )

    if request.method == "POST":

        form = ProductUpdateForm(
            request.POST,
            instance=product
        )

        if form.is_valid():

            form.save()

            messages.success(
                request,
                f"Product '{product.name}' updated successfully!"
            )

            return redirect("product_list")

        messages.error(
            request,
            "Please correct the errors in the form."
        )

    else:
        form = ProductUpdateForm(
            instance=product
        )

    return render(
        request,
        "update_product.html",
        {
            "form": form,
            "product": product,
        }
    )



@user_passes_test(
    can_manage_products,
    login_url="/distributor-login/"
)
@require_POST
def delete_product(request, product_id):

    product = get_object_or_404(
        Product,
        pk=product_id
    )

    product_name = product.name

    try:
        product.delete()

        messages.success(
            request,
            f"Product '{product_name}' deleted successfully!"
        )

    except ProtectedError:

        messages.error(
            request,
            f"Cannot delete '{product_name}' because it is used in existing invoices."
        )

    return redirect("product_list")

@login_required
def invoice_add(request):

    # Show invoice form
    if request.method == "GET":

        customers = Customer.objects.all()
        products = Product.objects.all()

        return render(request, "invoice_add.html", {
            "customers": customers,
            "products": products
        })

    # Save invoice when form is submitted
    if request.method == "POST":

        try:
            customer_id = request.POST.get("customer")

            product_ids = request.POST.getlist("product[]")
            quantities = request.POST.getlist("quantity[]")

            if not customer_id:
                messages.error(request, "Please select a customer.")
                return redirect("invoice_add")

            if not product_ids or len(product_ids) != len(quantities):
                messages.error(request, "Please add at least one valid product.")
                return redirect("invoice_add")

            customer = get_object_or_404(Customer, id=customer_id)

            # Make sure distributor can only invoice their own customers
            if not request.user.is_staff:
                if customer.distributor_id != request.user.id:
                    messages.error(request, "You cannot create an invoice for this customer.")
                    return redirect("invoice_add")

            invoice_rows = []
            subtotal = Decimal("0.00")
            gst_amount = Decimal("0.00")

            # Validate products and calculate totals before saving
            for product_id, quantity_value in zip(product_ids, quantities):

                if not product_id:
                    raise ValueError("Please select a product.")

                quantity = int(quantity_value)

                if quantity <= 0:
                    raise ValueError("Quantity must be greater than zero.")

                product = get_object_or_404(Product, id=product_id)

                if product.stock < quantity:
                    raise ValueError(
                        f"Insufficient stock for {product.name}."
                    )

                price = Decimal(str(product.price))
                gst_rate = Decimal(str(product.gst_rate))

                item_subtotal = price * quantity
                item_gst = item_subtotal * gst_rate / Decimal("100")
                item_total = item_subtotal + item_gst

                subtotal += item_subtotal
                gst_amount += item_gst

                invoice_rows.append({
                    "product": product,
                    "quantity": quantity,
                    "price": price,
                    "gst_rate": gst_rate,
                    "total": item_total
                })

            grand_total = subtotal + gst_amount

            # Save invoice and items together
            with transaction.atomic():

                invoice_number = (
                    "INV-" + timezone.now().strftime("%Y%m%d%H%M%S%f")
                )

                invoice = Invoice.objects.create(
                    invoice_number=invoice_number,
                    customer=customer,
                    distributor=request.user,
                    subtotal=subtotal,
                    gst_amount=gst_amount,
                    grand_total=grand_total
                )

                for row in invoice_rows:

                    InvoiceItem.objects.create(
                        invoice=invoice,
                        product=row["product"],
                        quantity=row["quantity"],
                        price=row["price"],
                        gst_rate=row["gst_rate"],
                        total=row["total"]
                    )

                    # Reduce product stock
                    product = row["product"]
                    product.stock -= row["quantity"]
                    product.save(update_fields=["stock"])

            messages.success(
                request,
                f"Invoice {invoice.invoice_number} created successfully!"
            )

            return redirect("invoice_list")

        except (ValueError, InvalidOperation, TypeError):
            messages.error(
                request,
                "Invalid invoice details. Please check the entered values."
            )
            return redirect("invoice_add")



@login_required
def invoice_create(request):

    # Fetch products for JavaScript calculations
    products = Product.objects.all()

    product_data = [
        {
            "id": product.id,
            "name": product.name,
            "price": str(product.price),
            "gst": str(product.gst_rate),
        }
        for product in products
    ]

    if request.method == "POST":

        invoice_form = InvoiceForm(request.POST)
        item_formset = InvoiceItemFormSet(
            request.POST,
            prefix="items"
        )

        if invoice_form.is_valid() and item_formset.is_valid():

            try:
                with transaction.atomic():

                    # Create invoice without saving immediately
                    invoice = invoice_form.save(commit=False)

                    # Assign logged-in distributor
                    invoice.distributor = request.user

                    # Generate a unique invoice number
                    last_invoice = (
                        Invoice.objects
                        .order_by("-id")
                        .first()
                    )

                    if last_invoice and last_invoice.invoice_number:
                        try:
                            last_number = int(
                                last_invoice.invoice_number.replace(
                                    "INV-", ""
                                )
                            )
                            next_number = last_number + 1

                        except (ValueError, AttributeError):
                            next_number = Invoice.objects.count() + 1
                    else:
                        next_number = 1

                    invoice.invoice_number = f"INV-{next_number:05d}"

                    # Save invoice
                    invoice.save()

                    # Connect formset to the saved invoice
                    item_formset.instance = invoice

                    # Get invoice items
                    items_to_save = item_formset.save(commit=False)

                    # Delete removed items
                    for deleted_item in item_formset.deleted_objects:
                        deleted_item.delete()

                    subtotal = Decimal("0.00")
                    gst_amount = Decimal("0.00")
                    grand_total = Decimal("0.00")

                    # Save each invoice item
                    for item in items_to_save:

                        if not item.product_id:
                            continue

                        # Get price and GST from selected product
                        price = Decimal(str(item.product.price))
                        gst_rate = Decimal(str(item.product.gst_rate))
                        quantity = int(item.quantity)

                        if quantity <= 0:
                            raise ValueError(
                                "Quantity must be greater than zero."
                            )

                        # Calculate item amounts
                        item_subtotal = price * quantity

                        item_gst = (
                            item_subtotal * gst_rate
                            / Decimal("100")
                        )

                        item_total = item_subtotal + item_gst

                        # Assign correct model fields
                        item.price = price
                        item.gst_rate = gst_rate
                        item.total = item_total

                        item.save()

                        # Add to invoice totals
                        subtotal += item_subtotal
                        gst_amount += item_gst
                        grand_total += item_total

                    # Save final invoice amounts
                    invoice.subtotal = subtotal
                    invoice.gst_amount = gst_amount
                    invoice.grand_total = grand_total

                    invoice.save(
                        update_fields=[
                            "subtotal",
                            "gst_amount",
                            "grand_total",
                        ]
                    )

                messages.success(
                    request,
                    f"Invoice {invoice.invoice_number} created successfully!"
                )

                return redirect("invoice_list")

            except (ValueError, InvalidOperation, TypeError) as error:

                messages.error(
                    request,
                    f"Invoice could not be created: {error}"
                )

        else:
            messages.error(
                request,
                "Please correct the customer and product details."
            )

    else:

        invoice_form = InvoiceForm()
        item_formset = InvoiceItemFormSet(prefix="items")

    context = {
        "invoice_form": invoice_form,
        "item_formset": item_formset,
        "product_data": product_data,
    }

    return render(
        request,
        "invoice_create.html",
        context
    )


@login_required
def invoice_list(request):

    if request.user.is_staff:
        invoices = Invoice.objects.select_related(
            "customer", "distributor"
        ).order_by("-id")
    else:
        invoices = Invoice.objects.filter(
            distributor=request.user
        ).select_related(
            "customer", "distributor"
        ).order_by("-id")

    return render(request, "invoice_list.html", {
        "invoices": invoices
    })


@login_required

def invoice_pdf(request, invoice_id):
    invoice = get_object_or_404(
        Invoice.objects.prefetch_related('items__product'),
        id=invoice_id
    )

    items = invoice.items.select_related('product').all()

    context = {
        'invoice': invoice,
        'items': items,
    }

    html = render_to_string('invoice_pdf.html', context)

    pdf_file = BytesIO()
    pisa_status = pisa.CreatePDF(html, dest=pdf_file)

    if pisa_status.err:
        return HttpResponse(
            'Error generating PDF',
            status=500
        )

    response = HttpResponse(
        pdf_file.getvalue(),
        content_type='application/pdf'
    )

    response['Content-Disposition'] = (
        f'attachment; filename="Invoice_{invoice.invoice_number}.pdf"'
    )

    return response

# 9. Resolve local static and media image paths for xhtml2pdf
def link_callback(uri, rel):

    if uri.startswith(settings.MEDIA_URL):
        path = os.path.join(
            str(settings.MEDIA_ROOT),
            uri[len(settings.MEDIA_URL):]
        )

    elif uri.startswith(settings.STATIC_URL):
        path = finders.find(
            uri[len(settings.STATIC_URL):]
        )

    else:
        return uri

    if not path or not os.path.isfile(path):
        raise Exception(
            f'PDF image file not found: {uri}'
        )

    return path


@login_required
def invoice_list(request):

    # 1. Fetch invoice data and related customer/product information
    invoices = Invoice.objects.select_related(
        'customer',
        'distributor'
    ).prefetch_related(
        'items__product'
    ).annotate(
        product_count=Count('items', distinct=True)
    ).order_by('-invoice_date', '-id')

    # 2. Distributor can see their own invoices.
    # Admin can see all invoices.
    if not request.user.is_staff:
        invoices = invoices.filter(distributor=request.user)

    # 3. Pagination: 10 invoices per page
    paginator = Paginator(invoices, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 4. Generate QR code using actual invoice and item data
    for invoice in page_obj:

        product_summary = []

        for item in invoice.items.all():
            product_summary.append({
                'product_name': item.product.name,
                'quantity': item.quantity,
                'price': str(item.price),
                'gst_rate': str(item.gst_rate),
                'total': str(item.total),
            })

        invoice_data = {
            'invoice_number': invoice.invoice_number,
            'customer_name': invoice.customer.name,
            'invoice_date': (
                invoice.invoice_date.isoformat()
                if invoice.invoice_date else ''
            ),
            'product_count': invoice.product_count,
            'products': product_summary,
            'subtotal': str(invoice.subtotal),
            'gst_amount': str(invoice.gst_amount),
            'grand_total': str(invoice.grand_total),
        }

        qr = qrcode.QRCode(
            version=1,
            error_correction=qrcode.constants.ERROR_CORRECT_M,
            box_size=8,
            border=4
        )

        qr.add_data(json.dumps(invoice_data))
        qr.make(fit=True)

        qr_image = qr.make_image(
            fill_color='black',
            back_color='white'
        )

        buffer = BytesIO()
        qr_image.save(buffer, format='PNG')

        invoice.qr_code = base64.b64encode(
            buffer.getvalue()
        ).decode('utf-8')

    # 5. Send dynamic data to HTML template
    context = {
        'invoices': page_obj,
        'page_obj': page_obj,
    }

    return render(
        request,
        'invoice_list.html',
        context
    )

# Check whether logged-in user is an admin
def is_admin_user(user):
    return user.is_authenticated and user.is_staff


# Admin Registration Frontend Page
@login_required(login_url='admin_login')
@user_passes_test(is_admin_user, login_url='admin_login')
def admin_register_page(request):

    return render(request, 'admin_register.html')


def admin_forgot_password(request):

    if request.method == "POST":

        email = request.POST.get("email", "").strip()

        User = get_user_model()

        admin_user = User.objects.filter(
            email__iexact=email,
            is_staff=True,
            is_active=True
        ).first()

        if admin_user:

            now = timezone.now()

            # Check 60-second OTP request restriction
            previous_otp = PasswordResetOTP.objects.filter(
                user=admin_user,
                is_used=False
            ).order_by("-created_at").first()

            if (
                previous_otp
                and previous_otp.last_sent_at
                and now - previous_otp.last_sent_at < timedelta(seconds=60)
            ):
                messages.error(
                    request,
                    "Please wait 60 seconds before requesting another OTP."
                )
                return redirect("admin_forgot_password")

            # Generate a six-digit OTP
            otp = str(secrets.randbelow(900000) + 100000)

            # Delete previous unused OTP records
            PasswordResetOTP.objects.filter(
                user=admin_user,
                is_used=False
            ).delete()

            # Store hashed OTP in database
            otp_record = PasswordResetOTP.objects.create(
                user=admin_user,
                otp_hash=make_password(otp),
                expires_at=now + timedelta(minutes=10),
                last_sent_at=now
            )

            # Send OTP email
            try:

                subject = (
                    "Advanced Billing System - Password Recovery OTP"
                )

                message = f"""
Hello {admin_user.username},

We received a request to reset your admin password.

Your One-Time Password (OTP) is:

{otp}

This OTP is valid for 10 minutes.

Please do not share this OTP with anyone.

Regards,
Advanced Billing System with QR
"""

                html_message = f"""
                <html>
                <body style="font-family: Arial;
                             background: #f4f6fa;
                             padding: 20px;">

                    <div style="background: white;
                                padding: 25px;
                                border-radius: 10px;
                                max-width: 500px;
                                margin: auto;">

                        <h2 style="color: #1769aa;">
                            Advanced Billing System with QR
                        </h2>

                        <p>Hello {admin_user.username},</p>

                        <p>Your password recovery OTP is:</p>

                        <h1 style="color: #1769aa;
                                   letter-spacing: 8px;">
                            {otp}
                        </h1>

                        <p>This OTP is valid for
                           <b>10 minutes</b>.</p>

                        <p>Do not share this OTP with anyone.</p>

                        <hr>

                        <p>
                            Regards,<br>
                            Advanced Billing System Team
                        </p>

                    </div>
                </body>
                </html>
                """

                sent = send_mail(
                    subject=subject,
                    message=message,
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[admin_user.email],
                    html_message=html_message,
                    fail_silently=False
                )

                if sent == 1:

                    request.session["admin_reset_user_id"] = (
                        admin_user.id
                    )

                    messages.success(
                        request,
                        "OTP sent successfully to your registered email."
                    )

                    return redirect("admin_verify_otp")

                raise Exception("Email could not be sent.")

            except Exception as e:

                otp_record.delete()

                print("OTP Email Error:", str(e))

                messages.error(
                    request,
                    "Unable to send OTP. Check your email configuration."
                )

        else:

            messages.error(
                request,
                "If the email belongs to an admin account, "
                "an OTP will be sent."
            )

    return render(request, "forgot_password.html")


def admin_verify_otp(request):

    user_id = request.session.get("admin_reset_user_id")

    if not user_id:
        messages.error(request, "Please request a new OTP.")
        return redirect("admin_forgot_password")

    User = get_user_model()

    admin_user = User.objects.filter(
        id=user_id,
        is_staff=True,
        is_active=True
    ).first()

    if not admin_user:
        request.session.pop("admin_reset_user_id", None)
        return redirect("admin_forgot_password")

    otp_record = PasswordResetOTP.objects.filter(
        user=admin_user,
        is_used=False
    ).order_by("-created_at").first()

    if not otp_record:
        messages.error(request, "OTP not found. Request a new OTP.")
        return redirect("admin_forgot_password")

    if request.method == "POST":

        entered_otp = request.POST.get("otp", "").strip()

        if timezone.now() > otp_record.expires_at:
            messages.error(request, "OTP has expired. Request a new OTP.")
            return redirect("admin_forgot_password")

        if otp_record.attempts >= 5:
            otp_record.is_used = True
            otp_record.save()

            messages.error(
                request,
                "Maximum OTP attempts exceeded. Request a new OTP."
            )
            return redirect("admin_forgot_password")

        otp_record.attempts += 1
        otp_record.save()

        if check_password(entered_otp, otp_record.otp_hash):

            otp_record.is_verified = True
            otp_record.save()

            request.session["admin_otp_verified"] = True

            messages.success(
                request,
                "OTP verified successfully. Create your new password."
            )

            return redirect("admin_reset_password")

        messages.error(request, "Invalid OTP. Please try again.")

    return render(request, "verify_otp.html")

def admin_reset_password(request):

    user_id = request.session.get("admin_reset_user_id")

    if not user_id or not request.session.get("admin_otp_verified"):
        messages.error(request, "Please verify your OTP first.")
        return redirect("admin_forgot_password")

    User = get_user_model()

    admin_user = User.objects.filter(
        id=user_id,
        is_staff=True,
        is_active=True
    ).first()

    if not admin_user:
        request.session.flush()
        return redirect("admin_forgot_password")

    otp_record = PasswordResetOTP.objects.filter(
        user=admin_user,
        is_used=False,
        is_verified=True
    ).order_by("-created_at").first()

    if not otp_record or timezone.now() > otp_record.expires_at:
        messages.error(
            request,
            "Your OTP verification has expired. Please start again."
        )
        request.session.flush()
        return redirect("admin_forgot_password")

    if request.method == "POST":

        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if len(password) < 8:
            messages.error(
                request,
                "Password must contain at least 8 characters."
            )

        elif password != confirm_password:
            messages.error(
                request,
                "Passwords do not match."
            )

        else:

            admin_user.set_password(password)
            admin_user.save()

            otp_record.is_used = True
            otp_record.save()

            request.session.flush()

            messages.success(
                request,
                "Admin password changed successfully. Please log in."
            )

            return redirect("admin_login")

    return render(request, "reset_password.html")


class DistributorCustomerRegistrationAPI(generics.ListCreateAPIView):

    serializer_class = CustomerRegistrationSerializer

    authentication_classes = [SessionAuthentication]

    permission_classes = [
        IsAuthenticated,
        IsDistributor,
    ]

    def get_queryset(self):
        return Customer.objects.filter(
            distributor=self.request.user
        ).order_by('-id')

    def perform_create(self, serializer):
        serializer.save(
            distributor=self.request.user
        )

@login_required
def distributor_customer_register_page(request):

    # Check whether the logged-in user belongs to Distributor group
    if not request.user.groups.filter(name="Distributor").exists():
        return HttpResponseForbidden(
            "Only distributors can access this page."
        )

    return render(
        request,
        "distributor_customer_register.html"
    )



@login_required
def admin_reports(request):
    invoices = Invoice.objects.all().order_by('-invoice_date')

    start_date = request.GET.get('start_date', '').strip()
    end_date = request.GET.get('end_date', '').strip()

    errors = []
    filtered_invoices = Invoice.objects.none()

    # Run validation only after the user submits the form.
    if request.GET.get('generate') == '1':

        # Validate empty dates
        if not start_date:
            errors.append("Please select a start date.")

        if not end_date:
            errors.append("Please select an end date.")

        # Validate date format
        start = None
        end = None

        if start_date:
            try:
                start = datetime.strptime(
                    start_date, '%Y-%m-%d'
                ).date()
            except ValueError:
                errors.append("Please enter a valid start date.")

        if end_date:
            try:
                end = datetime.strptime(
                    end_date, '%Y-%m-%d'
                ).date()
            except ValueError:
                errors.append("Please enter a valid end date.")

        # Validate date range
        if start and end and start > end:
            errors.append(
                "Start date cannot be later than end date."
            )

        # Filter invoices only when validation succeeds
        if not errors:
            filtered_invoices = invoices.filter(
                invoice_date__range=(start, end)
            ).order_by('-invoice_date')

    context = {
        'invoices': filtered_invoices,
        'start_date': start_date,
        'end_date': end_date,
        'errors': errors,
        'total_invoices': filtered_invoices.count(),
    }

    return render(request, 'reports.html', context)


def admin_reports_pdf(request):

    # Check admin permission
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponseForbidden(
            "You are not authorized to download this report."
        )

    # Get date filter form
    report_form = InvoiceReportFilterForm(request.GET or None)

    # Start with all invoices
    invoices = Invoice.objects.select_related(
        "customer"
    ).all()

    # Validate and apply selected dates
    if not report_form.is_valid():
        return HttpResponse(
            "Invalid date range. Please check your selected dates.",
            status=400
        )

    start_date = report_form.cleaned_data.get("start_date")
    end_date = report_form.cleaned_data.get("end_date")

    if start_date:
        invoices = invoices.filter(
            invoice_date__date__gte=start_date
        )

    if end_date:
        invoices = invoices.filter(
            invoice_date__date__lte=end_date
        )

    invoices = invoices.order_by("-invoice_date")

    # Calculate invoice summary
    summary = invoices.aggregate(
        total_invoices=Count("id"),
        total_amount=Sum("grand_total")
    )

    total_invoices = summary["total_invoices"] or 0
    total_amount = summary["total_amount"] or 0

    # PDF template data
    context = {
        "invoice_report": invoices,
        "total_invoices": total_invoices,
        "total_amount": total_amount,
        "start_date": start_date,
        "end_date": end_date,
    }

    # Generate HTML from PDF template
    html = render_to_string(
        "reports_pdf.html",
        context
    )

    # Create PDF in memory
    pdf_file = BytesIO()

    pdf_status = pisa.CreatePDF(
        html,
        dest=pdf_file,
        encoding="UTF-8"
    )

    # Check PDF generation
    if pdf_status.err:
        return HttpResponse(
            "Error occurred while generating PDF.",
            status=500
        )

    # Return downloadable PDF
    response = HttpResponse(
        pdf_file.getvalue(),
        content_type="application/pdf"
    )

    response["Content-Disposition"] = (
        'attachment; filename="invoice_report.pdf"'
    )

    return response



@login_required
def qr_code_decoder(request):

    if request.method != 'POST':
        return JsonResponse({
            'success': False,
            'message': 'Only POST requests are allowed.'
        }, status=405)

    # Get uploaded QR image
    uploaded_file = request.FILES.get('image')

    if not uploaded_file:
        return JsonResponse({
            'success': False,
            'message': 'Please upload a QR code image.'
        }, status=400)

    # Validate image size
    if uploaded_file.size > 5 * 1024 * 1024:
        return JsonResponse({
            'success': False,
            'message': 'Image size must not exceed 5 MB.'
        }, status=400)

    # Validate file extension
    allowed_extensions = ['.png', '.jpg', '.jpeg']

    file_name = uploaded_file.name.lower()

    if not any(file_name.endswith(ext) for ext in allowed_extensions):
        return JsonResponse({
            'success': False,
            'message': 'Only PNG and JPG images are allowed.'
        }, status=400)

    try:
        # Read uploaded image
        image_bytes = uploaded_file.read()

        # Decode QR using OpenCV utility
        decoded_data = decode_qr_image(image_bytes)

        if not decoded_data:
            return JsonResponse({
                'success': False,
                'message': 'No QR code found in the image.'
            }, status=400)

        # Return decoded QR data
        return JsonResponse({
            'success': True,
            'message': 'QR code read successfully.',
            'decoded_data': decoded_data
        }, status=200)

    except ValueError as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=400)

    except Exception:
        return JsonResponse({
            'success': False,
            'message': 'An unexpected error occurred while reading QR code.'
        }, status=500)





def decode_qr_invoice(request):

    invoice_data = None

    if request.method == "POST":

        # Get uploaded image
        image_file = request.FILES.get("qr_image")

        if not image_file:
            messages.error(
                request,
                "Please select a QR code image before submitting."
            )

        elif image_file.size == 0:
            messages.error(
                request,
                "The uploaded file is empty."
            )

        elif image_file.size > 5 * 1024 * 1024:
            messages.error(
                request,
                "File size must not exceed 5 MB."
            )

        else:
            try:
                # Read uploaded image
                image_bytes = image_file.read()

                if not image_bytes:
                    raise ValueError("The uploaded image is empty.")

                # Convert image bytes into OpenCV image
                image_array = np.frombuffer(
                    image_bytes,
                    dtype=np.uint8
                )

                image = cv2.imdecode(
                    image_array,
                    cv2.IMREAD_COLOR
                )

                if image is None:
                    raise ValueError(
                        "Invalid image. Please upload PNG or JPG."
                    )

                # Improve QR detection using grayscale and resizing
                gray = cv2.cvtColor(
                    image,
                    cv2.COLOR_BGR2GRAY
                )

                gray = cv2.resize(
                    gray,
                    None,
                    fx=2,
                    fy=2,
                    interpolation=cv2.INTER_CUBIC
                )

                detector = cv2.QRCodeDetector()

                # First try resized grayscale image
                qr_data, points, _ = detector.detectAndDecode(gray)

                # Try original image if first attempt fails
                if not qr_data or not qr_data.strip():
                    qr_data, points, _ = detector.detectAndDecode(image)

                if not qr_data or not qr_data.strip():
                    raise ValueError(
                        "No QR code found. Please upload a clear, valid QR code image."
                    )

                # Convert decoded QR text into JSON
                data = json.loads(qr_data)

                if not isinstance(data, dict):
                    raise ValueError("Invalid invoice QR code data.")

                # Validate required invoice fields
                required_fields = [
                    "invoice_number",
                    "customer_name",
                    "total_amount"
                ]

                missing_fields = [
                    field for field in required_fields
                    if field not in data
                    or data[field] is None
                    or (
                        isinstance(data[field], str)
                        and not data[field].strip()
                    )
                ]

                if missing_fields:
                    raise ValueError(
                        "Missing invoice fields: "
                        + ", ".join(missing_fields)
                    )

                # Validate invoice items
                items = data.get("items", [])

                if not isinstance(items, list):
                    raise ValueError("Invalid product details.")

                # Validate total amount
                total_amount = float(data["total_amount"])

                if not np.isfinite(total_amount) or total_amount < 0:
                    raise ValueError("Invalid invoice total.")

                # Validate each product
                for item in items:

                    if not isinstance(item, dict):
                        raise ValueError(
                            "Invalid product information."
                        )

                    product_name = item.get("product_name")

                    quantity = int(item.get("quantity", 0))

                    price = float(item.get("price", 0))

                    if (
                        not isinstance(product_name, str)
                        or not product_name.strip()
                    ):
                        raise ValueError("Invalid product name.")

                    if (
                        quantity <= 0
                        or not np.isfinite(price)
                        or price < 0
                    ):
                        raise ValueError(
                            "Invalid quantity or price."
                        )

                    # Calculate subtotal
                    item["quantity"] = quantity
                    item["price"] = price
                    item["subtotal"] = quantity * price

                # Prepare invoice information for template
                invoice_data = {
                    "invoice_number": data["invoice_number"],
                    "customer_name": data["customer_name"],
                    "product_count": data.get(
                        "product_count",
                        len(items)
                    ),
                    "total_amount": total_amount,
                    "items": items
                }

                # Success message
                messages.success(
                    request,
                    "QR Code decoded successfully! Invoice details loaded."
                )

            except json.JSONDecodeError:
                messages.error(
                    request,
                    "Invalid QR data. The QR code does not contain valid JSON."
                )

            except (ValueError, TypeError, OverflowError) as e:
                messages.error(request, str(e))

            except Exception as e:
                messages.error(
                    request,
                    f"Unable to process the QR image: {str(e)}"
                )

    return render(
        request,
        "qr_invoice_details.html",
        {
            "invoice_data": invoice_data
        }
    )


# ---------------- LOGOUT ----------------

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


