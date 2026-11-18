
from django.urls import path
from . import views
from core import views
from core.views import invoice_list
from .views import distributor_customer_register_page
from .views import DistributorCustomerRegistrationAPI

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

    # Product Management URLs

    path('products/', views.product_list, name='product_list'),

    path('products/add/', views.add_product, name='product_add'),

    path('products/edit/<int:product_id>/', views.update_product, name='product_edit'),

    path('products/delete/<int:product_id>/', views.delete_product, name='product_delete'),

    path("invoice/create/", views.invoice_create, name="invoice_create"),

    path("invoices/add/", views.invoice_add, name="invoice_add"),

    path("invoices/", views.invoice_list, name="invoice_list"),

    path('invoice/<int:invoice_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),

    path('invoices/', invoice_list, name='invoice_list'),

    path("admin-forgot-password/", views.admin_forgot_password, name="admin_forgot_password"),

    path("admin-verify-otp/", views.admin_verify_otp, name="admin_verify_otp"),

    path("admin-reset-password/", views.admin_reset_password, name="admin_reset_password"),

    path('api/distributor/customers/', DistributorCustomerRegistrationAPI.as_view(), name='distributor_customer_api'),

    path('distributor/customer-register/', distributor_customer_register_page, name='distributor_customer_register_page'),

    path("logout/", views.logout_view, name="logout"),

]
