from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static

urlpatterns = [
    #redireciona para o frontend 
    path('', RedirectView.as_view(url='https://data-dojo-nar3-lda8e7x88-adrianojesusdevelopers-projects.vercel.app/LOGINgit', permanent=False)),
    # Painel Administrativo    
    path('admin/', admin.site.urls),
    
    # Endpoints de Autenticação (dj-rest-auth) colocados no topo para evitar conflitos
    path('api/auth/', include('dj_rest_auth.urls')),
    path('api/auth/registration/', include('dj_rest_auth.registration.urls')),
    
    # RESOLUÇÃO DEFINITIVA: Importando pelo caminho absoluto do projeto
    path('api/', include('api.urls')), 
]

# Libera arquivos de mídia e uploads no ambiente de desenvolvimento
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)