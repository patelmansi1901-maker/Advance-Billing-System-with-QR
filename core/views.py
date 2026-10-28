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
from django.shortcuts import render
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from .models import Customer
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import request
from django.shortcuts import render
from .models import Product
from django.shortcuts import render, redirect, get_object_or_404
from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib.auth.hashers import make_password, check_password
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.shortcuts import render, redirect
from django.utils import timezone
from django.views.decorators.http import require_POST
from .models import DistributorProfile
from django.contrib.auth.models import Group
from .models import Customer
from .models import PasswordResetOTP
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect
from .models import DistributorProfile

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
    if request.user.is_authenticated:
        if is_distributor(request.user):
            return redirect('distributor_dashboard')

        if is_admin(request.user):
            return redirect('admin_dashboard')

        logout(request)

    if request.method == 'POST':
        
       login_value = request.POST.get("username", "").strip()
       password = request.POST.get("password", "")

# Allow login using either username or email.
       username = login_value

       if "@" in login_value:
        matching_user = User.objects.filter(
        email__iexact=login_value
    ).first()

    if matching_user:
        username = matching_user.username

    user = authenticate(
    request,
    username=username,
    password=password,
)

    if user is not None and is_distributor(user):
            login(request, user)
            return redirect('distributor_dashboard')

    messages.error(
            request,
            'Invalid credentials or distributor access not permitted.'
        )

    return render(request, 'distributor_login.html')


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


@user_passes_test(
    lambda user: user.is_authenticated and user.is_staff,
    login_url="/admin-login/"
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

            return redirect("add_product")
        else:
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
    lambda user: user.is_authenticated and user.is_staff,
    login_url="/admin-login/"
)
def product_list(request):
    search_query = request.GET.get("q", "").strip()

    products = Product.objects.select_related("category").all()

    # Search product name, code, barcode, and category.
    if search_query:
        products = products.filter(
            Q(name__icontains=search_query)
            | Q(product_code__icontains=search_query)
            | Q(barcode__icontains=search_query)
            | Q(category__name__icontains=search_query)
        )

    # Show 10 products per page.
    paginator = Paginator(products, 10)

    # get_page handles invalid page numbers safely.
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    context = {
        "page_obj": page_obj,
        "search_query": search_query,
        "total_products": paginator.count,
    }

    return render(
        request,
        "product_list.html",
        context
    )


# ---------------- LOGOUT ----------------

@require_POST
def logout_view(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('home')


