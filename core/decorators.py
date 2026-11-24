from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages


def admin_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("admin_login")

        if request.user.is_staff:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Admin access required.")

        if request.user.groups.filter(name="Distributor").exists():
            return redirect("distributor_dashboard")

        return redirect("home")

    return wrapper


def distributor_required(view_func):

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):

        if not request.user.is_authenticated:
            return redirect("distributor_login")

        is_distributor = (
            request.user.groups.filter(name="Distributor").exists()
            and not request.user.is_staff
        )

        if is_distributor:
            return view_func(request, *args, **kwargs)

        messages.error(request, "Distributor access required.")

        if request.user.is_staff:
            return redirect("admin_dashboard")

        return redirect("home")

    return wrapper