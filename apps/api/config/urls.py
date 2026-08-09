from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView
from django.conf import settings
from django.conf.urls.static import static


urlpatterns = [

    # =====================================================
    # HOME
    # Redireciona para Django Admin
    # =====================================================
    path(
        "",
        RedirectView.as_view(
            url="/admin/",
            permanent=False,
        ),
    ),


    # =====================================================
    # ADMIN
    # =====================================================
    path(
        "admin/",
        admin.site.urls,
    ),


    # =====================================================
    # AUTENTICAÇÃO API
    # Login
    # Logout
    # User details
    # Token
    # =====================================================
    path(
        "api/auth/",
        include("dj_rest_auth.urls"),
    ),


    # =====================================================
    # API PRINCIPAL DDJ
    # =====================================================
    path(
        "api/",
        include("api.urls"),
    ),


    # =====================================================
    # INTELIGÊNCIA ARTIFICIAL DDJ AI
    # =====================================================
    path(
        "api/ai/",
        include("ai.urls"),
    ),

]


# =====================================================
# MEDIA FILES (somente desenvolvimento)
# =====================================================
if settings.DEBUG:
    urlpatterns += static(
        settings.MEDIA_URL,
        document_root=settings.MEDIA_ROOT,
    )


# =====================================================
# STATIC FILES
# =====================================================
urlpatterns += static(
    settings.STATIC_URL,
    document_root=settings.STATIC_ROOT,
)