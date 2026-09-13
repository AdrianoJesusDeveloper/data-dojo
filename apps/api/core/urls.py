from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

# O Router cria automaticamente as rotas de GET (listagem) e POST (criação) para o ViewSet
router = DefaultRouter()
router.register(r'community/posts', views.ForumTopicViewSet, basename='forumtopic')
router.register(r'community/comments', views.ForumCommentViewSet, basename='forumcomment')
router.register(r'certificates', views.CertificateViewSet, basename='certificate')
router.register(r'portfolio/projects', views.StudentProjectViewSet, basename='student-project')

# ESSAS DUAS LINHAS REGISTRAM AS ROTAS QUE O SEU WORKSPACE PRECISA:
router.register(r'courses', views.CourseViewSet, basename='course')
router.register(r'enrollments', views.EnrollmentViewSet, basename='enrollment')
router.register(r'course-progress', views.CourseProgressViewSet, basename='course-progress')
router.register(r'lesson-progress', views.LessonProgressViewSet, basename='lesson-progress')
router.register(r'modules', views.ModuleViewSet, basename='module')

urlpatterns = [
    # Inclui todas as rotas registradas acima
    path('', include(router.urls)),
    
    # Rota separada para a atualização de perfil do samurai
    path('user/profile/', views.UserProfileUpdateView.as_view(), name='user-profile'),
    path('exercise-evidence/', views.ExerciseEvidenceListView.as_view(), name='exercise-evidence-list'),
    path('learning/continue/', views.LearningContinuityView.as_view(), name='learning-continuity'),
]
