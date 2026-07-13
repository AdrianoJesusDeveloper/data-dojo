from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser

from .models import Course, Module, Lesson, ForumTopic, ForumComment, Certificate
from .serializers import (
    CourseSerializer, 
    LessonSerializer, 
    ModuleSerializer,
    ForumTopicSerializer,
    ForumTopicDetailSerializer,
    ForumCommentSerializer,
    CertificateSerializer,
    UserSerializer
)

# =====================================================================
# NOVAS VIEWS: COMUNIDADE (FÓRUM)
# =====================================================================
class ForumTopicViewSet(viewsets.ModelViewSet):
    """
    Lista, cria, edita e apaga tópicos no fórum da comunidade.
    Suporta JSON, upload de mídias e sistema de curtidas.
    """
    queryset = ForumTopic.objects.prefetch_related('user', 'comments__user').order_by('-created_at')
    parser_classes = [JSONParser, MultiPartParser, FormParser] # Adicionado JSONParser para suportar o React
    permission_classes = [permissions.IsAuthenticated]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ForumTopicDetailSerializer
        return ForumTopicSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        """Sobrescreve a listagem para injetar as propriedades que o frontend precisa"""
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(self._inject_custom_fields(serializer.data, request.user))

        serializer = self.get_serializer(queryset, many=True)
        return Response(self._inject_custom_fields(serializer.data, request.user))

    def _inject_custom_fields(self, data, user):
        """Injeta dinamicamente se o usuário logado é dono e garante o array de comentários"""
        for post in data:
            # Captura com segurança os dados do usuário se for um dicionário aninhado
            user_data = post.get('user', {})
            
            if isinstance(user_data, dict):
                user_id = user_data.get('id')
                user_username = user_data.get('username')
            else:
                user_id = post.get('user_id')
                user_username = post.get('user')

            # Validação real se o samurai logado é o autor da postagem
            post['is_owner'] = user_id == user.id or user_username == user.username
            
            if 'comments' not in post:
                # Garante que a chave exista para evitar erros de undefined no frontend
                post['comments'] = post.get('forumcomment_set', [])
        return data

    # ❤️ ROTA CUSTOMIZADA: /api/community/posts/{id}/like/
    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        topic = self.get_object()
        
        if hasattr(topic, 'likes'):
            if request.user in topic.likes.all():
                topic.likes.remove(request.user)
                message = "Curtida removida"
            else:
                topic.likes.add(request.user)
                message = "Post curtido"
            
            if hasattr(topic, 'likes_count'):
                topic.likes_count = topic.likes.count()
                topic.save()
        else:
            if hasattr(topic, 'likes_count'):
                topic.likes_count += 1
                topic.save()
            message = "Post curtido"

        return Response({
            'status': message, 
            'likes_count': getattr(topic, 'likes_count', 0)
        }, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
        """Garante que samurais só possam apagar suas próprias publicações"""
        instance = self.get_object()
        if instance.user != request.user:
            return Response(
                {"detail": "Você não tem permissão para apagar a publicação de outro samurai."}, 
                status=status.HTTP_403_FORBIDDEN
            )
        self.perform_destroy(instance)
        return Response(status=status.HTTP_204_NO_CONTENT)


class ForumCommentViewSet(viewsets.ModelViewSet):
    """
    Gerencia as respostas e comentários de um tópico específico.
    """
    queryset = ForumComment.objects.select_related('user').order_by('created_at')
    serializer_class = ForumCommentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated]

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        
        # Sincroniza o contador de comentários do post pai se o campo existir
        topic = comment.forum_topic
        if hasattr(topic, 'comments_count'):
            topic.comments_count = topic.comments.count()
            topic.save()


# =====================================================================
# NOVA VIEW: CERTIFICADOS
# =====================================================================
class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).order_by('-issued_at')


# =====================================================================
# NOVA VIEW: PERFIL DE USUÁRIO (ATUALIZAÇÃO DE FOTO DE PERFIL)
# =====================================================================
class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def get_object(self):
        return self.request.user


# =====================================================================
# VIEWS JÁ EXISTENTES DA PLATAFORMA DE CURSOS
# =====================================================================
class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.prefetch_related('modules__lessons').order_by('-created_at')
    serializer_class = CourseSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.prefetch_related('lessons').order_by('order')
    serializer_class = ModuleSerializer


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.order_by('order')
    serializer_class = LessonSerializer