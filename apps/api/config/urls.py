from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    path('admin/', admin.site.get_admin_urls() if hasattr(admin.site, 'get_admin_urls') else admin.site.urls),
    path('api/', include([
        path('', include('core.urls')), # Suas rotas atuais (courses, lessons)
        path('auth/', include('dj_rest_auth.urls')), # Novas rotas de login/logout!
        path('auth/registration/', include('dj_rest_auth.registration.urls')),
    ]))
]

# ESTA LINHA ABAIXO É O SEGREDO: Libera os vídeos em ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)