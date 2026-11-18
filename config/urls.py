from django.contrib import admin
from django.urls import path, include
from core.api_views import AdminRegistrationAPIView
from core import views
from core.views import admin_register_page

urlpatterns = [
    path("django-admin/", admin.site.urls),
    path("", views.home, name="home"),
    path("", include("core.urls")),
    path('invoice/<int:invoice_id>/pdf/', views.invoice_pdf, name='invoice_pdf'),
    path('api/admin/register/', AdminRegistrationAPIView.as_view(), name='admin_register_api'),
    path('api-auth/', include('rest_framework.urls')),
    path('admin-register/', admin_register_page, name='admin_register_page'),
    path("admin-reports/", views.admin_reports, name="admin_reports"),
    path("products/add/", views.add_product, name="add_product"),
    path("admin-reports/", views.admin_reports, name="admin_reports"),
    path("admin-reports/pdf/", views.admin_reports_pdf, name="admin_reports_pdf",),
]
