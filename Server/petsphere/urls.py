from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('allauth.urls')), 
    path('api/accounts/', include('accounts.urls')),
    path('api/user/', include('user_profile.urls')),
    path('api/posts/', include('posts.urls')),
    path('api/pet/', include('pets.urls')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
