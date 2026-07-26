from django.urls import path, include
from rest_framework.routers import DefaultRouter
# CORREÇÃO: Importando as views de dentro do app 'core'
from core import views

router = DefaultRouter()
router.register(r'community/posts', views.ForumTopicViewSet, basename='forumtopic')
router.register(r'community/comments', views.ForumCommentViewSet, basename='forumcomment')
router.register(r'certificates', views.CertificateViewSet, basename='certificate')
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'modules', views.ModuleViewSet, basename='module')

urlpatterns = [
    path('', include(router.urls)),
    path('user/profile/', views.UserProfileUpdateView.as_view(), name='user-profile'),
]