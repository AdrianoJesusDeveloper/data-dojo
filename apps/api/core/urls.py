from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# O Router cria automaticamente as rotas de GET (listagem) e POST (criação) para o ViewSet
router = DefaultRouter()
router.register(r'community/posts', views.ForumTopicViewSet, basename='forumtopic')
router.register(r'community/comments', views.ForumCommentViewSet, basename='forumcomment')
router.register(r'certificates', views.CertificateViewSet, basename='certificate')

urlpatterns = [
    # Inclui todas as rotas registradas acima
    path('', include(router.urls)),
    
    # Rota separada para a atualização de perfil do samurai
    path('user/profile/', views.UserProfileUpdateView.as_view(), name='user-profile'),
]