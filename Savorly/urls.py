"""
URL configuration for Savorly project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/6.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path

from home import views as home_views
from vege import views as recipe_views

# for image
from django.conf.urls.static import static
from django.conf import settings
from django.contrib.staticfiles.urls import staticfiles_urlpatterns

urlpatterns = [
    path("admin/", admin.site.urls),
    path("", home_views.home, name="home"),
    path("register/<str:role>/", home_views.register, name="register"),
    path("login/", home_views.login_view, name="login"),
    path("logout/", home_views.logout_view, name="logout"),
    path("health", home_views.health, name="health"),
    path("recipes/", recipe_views.recipes, name="recipes"),
    path("chefs-table/", recipe_views.chefs_table, name="chefs_table"),
    # Both names point to the canonical URL so either naming convention works.
    path("chefs-table/", recipe_views.chefs_table, name="chef_table"),
    path("chef-table/", recipe_views.chefs_table, name="chef_table_hyphen"),
    path("chef_table/", recipe_views.chefs_table, name="chef_table_underscore"),
    path("chefs_table/", recipe_views.chefs_table, name="chefs_table_underscore"),
    path("delete_recipe/<id>/", recipe_views.delete_recipe, name="delete_recipe"),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

urlpatterns += staticfiles_urlpatterns()
