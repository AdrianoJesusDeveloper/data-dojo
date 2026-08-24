from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.views import APIView

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
    UserSerializer,
)


class OwnerWritePermission(permissions.BasePermission):
    """Permite leitura autenticada e restringe edição/exclusão ao autor."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, "user_id", None) == request.user.id


class ForumTopicViewSet(viewsets.ModelViewSet):
    """Lista, cria, edita, apaga e curte publicações da comunidade."""

    queryset = ForumTopic.objects.select_related("user").prefetch_related(
        "likes", "comments__user", "comments__likes"
    ).order_by("-created_at")
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, OwnerWritePermission]

    def get_serializer_class(self):
        if self.action == "retrieve":
            return ForumTopicDetailSerializer
        return ForumTopicSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        topic = self.get_object()
        if topic.likes.filter(pk=request.user.pk).exists():
            topic.likes.remove(request.user)
        else:
            topic.likes.add(request.user)
        return Response(self.get_serializer(topic).data, status=status.HTTP_200_OK)


class ForumCommentViewSet(viewsets.ModelViewSet):
    """Gerencia comentários, edição pelo autor e curtidas."""

    queryset = ForumComment.objects.select_related("user", "topic").prefetch_related("likes").order_by("created_at")
    serializer_class = ForumCommentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, OwnerWritePermission]

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        comment = self.get_object()
        if comment.likes.filter(pk=request.user.pk).exists():
            comment.likes.remove(request.user)
        else:
            comment.likes.add(request.user)
        return Response(self.get_serializer(comment).data, status=status.HTTP_200_OK)


class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).order_by("-issued_at")


class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.prefetch_related("modules__lessons").order_by("-created_at")
    serializer_class = CourseSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.prefetch_related("lessons").order_by("order")
    serializer_class = ModuleSerializer


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.order_by("order")
    serializer_class = LessonSerializer


class PasswordResetRequestView(APIView):
    """Requests a password reset without revealing whether an account exists."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        user = None

        if email:
            user = get_user_model().objects.filter(email__iexact=email, is_active=True).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"
            send_mail(
                subject="Redefina sua senha — Data Driven Dojo",
                message=(
                    "Recebemos uma solicitação para redefinir sua senha.\n\n"
                    f"Acesse o link para criar uma nova senha:\n{reset_url}\n\n"
                    "Se você não solicitou esta alteração, ignore este e-mail."
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                fail_silently=False,
            )

        return Response(
            {"detail": "Se houver uma conta associada a este e-mail, você receberá as instruções de recuperação."},
            status=status.HTTP_200_OK,
        )


class PasswordResetConfirmView(APIView):
    """Validates a reset token and saves the user's new password."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        uid = request.data.get("uid")
        token = request.data.get("token")
        password = request.data.get("password")
        password_confirmation = request.data.get("password_confirmation")

        if not all([uid, token, password, password_confirmation]):
            return Response({"detail": "Preencha todos os campos."}, status=status.HTTP_400_BAD_REQUEST)

        if password != password_confirmation:
            return Response(
                {"password_confirmation": ["As senhas não coincidem."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = get_user_model().objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            user = None

        if not user or not default_token_generator.check_token(user, token):
            return Response(
                {"detail": "Este link de recuperação é inválido ou expirou."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            validate_password(password, user)
        except Exception as error:
            return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(password)
        user.save(update_fields=["password"])
        return Response(
            {"detail": "Senha redefinida com sucesso. Você já pode entrar."},
            status=status.HTTP_200_OK,
        )
