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
from .serializers import CourseSerializer, LessonSerializer, ModuleSerializer, ForumTopicSerializer, ForumTopicDetailSerializer, ForumCommentSerializer, CertificateSerializer, UserSerializer


class OwnerWritePermission(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, "user_id", None) == request.user.id


class ForumTopicViewSet(viewsets.ModelViewSet):
    queryset = ForumTopic.objects.select_related("user").prefetch_related("likes", "comments__user", "comments__likes").order_by("-created_at")
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, OwnerWritePermission]

    def get_serializer_class(self):
        return ForumTopicDetailSerializer if self.action == "retrieve" else ForumTopicSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    @action(detail=True, methods=["post"])
    def like(self, request, pk=None):
        topic = self.get_object()
        if topic.likes.filter(pk=request.user.pk).exists():
            topic.likes.remove(request.user)
        else:
            topic.likes.add(request.user)
        return Response(self.get_serializer(topic).data)


class ForumCommentViewSet(viewsets.ModelViewSet):
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
        return Response(self.get_serializer(comment).data)


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
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        user = get_user_model().objects.filter(email__iexact=email, is_active=True).first() if email else None
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
            reset_url = f"{frontend_url}/reset-password?uid={uid}&token={token}"
            send_mail(subject="Redefina sua senha — Data Driven Dojo", message=f"Recebemos uma solicitação para redefinir sua senha.\n\nAcesse o link para criar uma nova senha:\n{reset_url}\n\nSe você não solicitou esta alteração, ignore este e-mail.", from_email=settings.DEFAULT_FROM_EMAIL, recipient_list=[user.email], fail_silently=False)
        return Response({"detail": "Se houver uma conta associada a este e-mail, você receberá as instruções de recuperação."})


class PasswordResetConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request):
        uid, token = request.data.get("uid"), request.data.get("token")
        password, confirmation = request.data.get("password"), request.data.get("password_confirmation")
        if not all([uid, token, password, confirmation]):
            return Response({"detail": "Preencha todos os campos."}, status=status.HTTP_400_BAD_REQUEST)
        if password != confirmation:
            return Response({"password_confirmation": ["As senhas não coincidem."]}, status=status.HTTP_400_BAD_REQUEST)
        try:
            user_id = force_str(urlsafe_base64_decode(uid))
            user = get_user_model().objects.get(pk=user_id, is_active=True)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            user = None
        if not user or not default_token_generator.check_token(user, token):
            return Response({"detail": "Este link de recuperação é inválido ou expirou."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            validate_password(password, user)
        except Exception as error:
            return Response({"password": list(error.messages)}, status=status.HTTP_400_BAD_REQUEST)
        user.set_password(password)
        user.save(update_fields=["password"])
        return Response({"detail": "Senha redefinida com sucesso. Você já pode entrar."})
