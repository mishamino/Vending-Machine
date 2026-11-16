from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path


urlpatterns = [
    path("django-admin/", admin.site.urls),
    path(
        "admin/login/",
        auth_views.LoginView.as_view(template_name="registration/login.html"),
        name="admin_login",
    ),
    path("admin/logout/", auth_views.LogoutView.as_view(), name="admin_logout"),
    path("", include("vending.urls")),
]
