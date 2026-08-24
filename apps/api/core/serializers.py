from rest_framework import serializers
from django.contrib.auth import get_user_model

from .models import Course, Module, Lesson, Exercise, ForumTopic, ForumComment, Certificate

User = get_user_model()

# =====================================================================
# NOVO: SERIALIZER DE USUÁRIO (PERFIL, FOTO E XP) - CORRIGIDO
# =====================================================================
class UserSerializer(serializers.ModelSerializer):
    # Cria uma chave extra "studentName" apontando para o username para garantir compatibilidade com o frontend
    studentName = serializers.CharField(source="username", read_only=True)

    class Meta:
        model = User
        fields = ["id", "username", "studentName", "email", "profile_picture", "xp_points"]
        read_only_fields = ["id", "xp_points"]

    def to_representation(self, instance):
        """ Garante o envio do link absoluto completo mesmo sendo um campo editável """
        ret = super().to_representation(instance)
        request = self.context.get('request')
        
        if instance.profile_picture and request is not None:
            ret['profile_picture'] = request.build_absolute_uri(instance.profile_picture.url)
        return ret


# =====================================================================
# NOVOS: SERIALIZERS DA COMUNIDADE (FÓRUM E FOTOS DE CÓDIGO)
# =====================================================================
class ForumCommentSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    likes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    liked_by_me = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ForumComment
        fields = ["id", "topic", "user", "content", "code_screenshot", "likes", "likes_count", "liked_by_me", "is_owner", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "likes", "created_at", "updated_at"]

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(pk=request.user.pk).exists())

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class ForumTopicSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    comments = ForumCommentSerializer(many=True, read_only=True)
    comments_count = serializers.IntegerField(source="comments.count", read_only=True)
    
    # Fornece a lista de IDs de quem curtiu (essencial para o frontend verificar o estado do botão)
    likes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    # Mantém o contador dinâmico estruturado
    likes_count = serializers.SerializerMethodField()
    liked_by_me = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ForumTopic
        fields = [
            "id", 
            "user", 
            "title", 
            "content", 
            "code_screenshot", 
            "likes",          
            "likes_count", 
            "liked_by_me",
            "comments_count", 
            "comments",
            "is_owner",
            "created_at",
            "updated_at"
        ]
        read_only_fields = ["id", "user", "likes", "created_at", "updated_at"]

    def get_likes_count(self, obj):
        return obj.likes.count()

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(pk=request.user.pk).exists())

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


class ForumTopicDetailSerializer(serializers.ModelSerializer):
    user = UserSerializer(read_only=True)
    comments = ForumCommentSerializer(many=True, read_only=True)
    likes = serializers.PrimaryKeyRelatedField(many=True, read_only=True)
    likes_count = serializers.IntegerField(source="likes.count", read_only=True)
    liked_by_me = serializers.SerializerMethodField()
    is_owner = serializers.SerializerMethodField()

    class Meta:
        model = ForumTopic
        fields = ["id", "user", "title", "content", "code_screenshot", "comments", "likes", "likes_count", "liked_by_me", "is_owner", "created_at", "updated_at"]
        read_only_fields = ["id", "user", "likes", "created_at", "updated_at"]

    def get_liked_by_me(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.likes.filter(pk=request.user.pk).exists())

    def get_is_owner(self, obj):
        request = self.context.get("request")
        return bool(request and request.user.is_authenticated and obj.user_id == request.user.id)


# =====================================================================
# NOVO: SERIALIZER DE CERTIFICADOS
# =====================================================================
class CertificateSerializer(serializers.ModelSerializer):
    course_title = serializers.CharField(source="course.title", read_only=True)

    class Meta:
        model = Certificate
        fields = ["id", "course", "course_title", "issued_at", "verification_code"]
        read_only_fields = ["id", "issued_at", "verification_code"]


# =====================================================================
# SERIALIZERS JÁ EXISTENTES DA PLATAFORMA
# =====================================================================
class ExerciseSerializer(serializers.ModelSerializer):
    class Meta:
        model = Exercise
        fields = [
            "id",
            "lesson",
            "title",
            "statement",
            "answer_type",
            "expected_answer",
            "expected_keywords",
            "evaluation_mode",
            "points",
        ]


class LessonSerializer(serializers.ModelSerializer):
    exercise = ExerciseSerializer(read_only=True)

    class Meta:
        model = Lesson
        fields = [
            "id",
            "module",
            "title",
            "content_type",
            "file_upload",
            "video_url",
            "body",
            "order",
            "exercise",
        ]

    def to_representation(self, instance):
        ret = super().to_representation(instance)

        request = self.context.get("request")

        if instance.file_upload:
            if request:
                ret["file_upload"] = request.build_absolute_uri(
                    instance.file_upload.url
                )

        return ret
    exercise = ExerciseSerializer(read_only=True)
    
    

    class Meta:
        model = Lesson
        fields = [
            "id",
            "module",
            "title",
            "content_type",
            "file_upload",
            "video_url",
            "body",
            "order",
            "exercise",
        ]
    

class ModuleSerializer(serializers.ModelSerializer):
    lessons = LessonSerializer(many=True, read_only=True)

    class Meta:
        model = Module
        fields = [
            "id",
            "course",
            "title",
            "order",
            "lessons",
        ]


class CourseSerializer(serializers.ModelSerializer):
    modules = ModuleSerializer(many=True, read_only=True)

    class Meta:
        model = Course
        fields = [
            "id",
            "title",
            "description",
            "created_at",
            "modules",
        ]