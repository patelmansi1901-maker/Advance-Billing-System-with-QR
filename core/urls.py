
from django.urls import path
from . import views
from core import views

urlpatterns = [
    path("admin-login/", views.admin_login, name="admin_login"),
    
    path("distributor-login/", views.distributor_login, name="distributor_login",),
    
    path('forgot-password/', views.forgot_password, name='forgot_password'),

    path("admin-dashboard/", views.admin_dashboard, name="admin_dashboard",),

    path("distributor-dashboard/", views.distributor_dashboard, name="distributor_dashboard",),

    path("distributor-register/", views.distributor_register, name="distributor_register",),

    path("distributor-profile/edit/", views.update_distributor_profile, name="update_distributor_profile",),

    path("distributor-profile/", views.distributor_profile, name="distributor_profile",),

    path("customers/add/", views.customer_add, name="customer_add",),

    path("customers/", views.customer_list, name="customer_list",),

    path("customers/<int:customer_id>/edit/", views.customer_edit, name="customer_edit",),

    path("customers/<int:customer_id>/delete/", views.customer_delete, name="customer_delete",),

    path("products/", views.product_list, name="product_list"),
    
    path("products/add/", views.add_product, name="add_product"),

    path("products/<int:product_id>/update/", views.update_product, name="update_product"),
    
    path("products/<int:product_id>/delete/", views.delete_product, name="delete_product",),

    path("invoice/create/", views.invoice_create, name="invoice_create"),

    path("logout/", views.logout_view, name="logout"),

]
