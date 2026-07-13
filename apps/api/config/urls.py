from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    # Painel Administrativo
    path('admin/', admin.site.urls),
    
    # Endpoints de Autenticação (dj-rest-auth) colocados no topo para evitar conflitos
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # Endpoints do Core/Comunidade (Apontando diretamente para o app)
    path('api/', include('core.urls')), 
]

# Libera arquivos de mídia e uploads no ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)