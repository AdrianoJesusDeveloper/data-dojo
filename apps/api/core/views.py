from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.utils import timezone
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from rest_framework.views import APIView

from rest_framework import viewsets, permissions, generics, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from rest_framework.pagination import PageNumberPagination

from .models import Course, Module, Lesson, Exercise, ForumTopic, ForumComment, Certificate, StudentProject, ExerciseAttempt, Enrollment, CourseProgress, LessonProgress
from .permissions import IsAdministrativeUserOrReadOnly
from .serializers import (
    CourseSerializer, 
    LessonSerializer, 
    ModuleSerializer,
    ForumTopicSerializer,
    ForumTopicDetailSerializer,
    ForumCommentSerializer,
    CertificateSerializer,
    UserSerializer,
    StudentProjectSerializer,
    ExerciseAttemptInputSerializer,
    ExerciseAttemptSerializer,
    EnrollmentSerializer,
    CourseProgressSerializer,
    LessonProgressSerializer,
)
from .services import (
    AcademicAccessError,
    AttemptConflictError,
    AttemptPersistenceError,
    CourseCompletionError,
    LessonTransitionError,
    complete_course,
    complete_lesson,
    create_exercise_attempt,
    resolve_learning_continuity,
    start_lesson,
)


class OwnerWritePermission(permissions.BasePermission):
    """Restringe edição/exclusão de publicações e comentários ao próprio autor."""

    def has_object_permission(self, request, view, obj):
        if request.method in permissions.SAFE_METHODS:
            return True
        return getattr(obj, "user_id", None) == request.user.id


# =====================================================================
# NOVAS VIEWS: COMUNIDADE (FÓRUM)
# =====================================================================
class ForumTopicViewSet(viewsets.ModelViewSet):
    """
    Lista, cria, edita e apaga tópicos no fórum da comunidade.
    Suporta JSON, upload de mídias e sistema de curtidas.
    """
    queryset = ForumTopic.objects.select_related('user').prefetch_related('likes', 'comments__user', 'comments__likes').order_by('-created_at')
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, OwnerWritePermission]

    def get_serializer_class(self):
        if self.action == 'retrieve':
            return ForumTopicDetailSerializer
        return ForumTopicSerializer

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

    def list(self, request, *args, **kwargs):
        queryset = self.filter_queryset(self.get_queryset())
        page = self.paginate_queryset(queryset)
        
        if page is not None:
            serializer = self.get_serializer(page, many=True)
            return self.get_paginated_response(self._inject_custom_fields(serializer.data, request.user))

        serializer = self.get_serializer(queryset, many=True)
        return Response(self._inject_custom_fields(serializer.data, request.user))

    def _inject_custom_fields(self, data, user):
        for post in data:
            user_data = post.get('user', {})
            
            if isinstance(user_data, dict):
                user_id = user_data.get('id')
                user_username = user_data.get('username')
            else:
                user_id = post.get('user_id')
                user_username = post.get('user')

            post['is_owner'] = user_id == user.id or user_username == user.username
            
            if 'comments' not in post:
                post['comments'] = post.get('forumcomment_set', [])
        return data

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        topic = self.get_object()
        user = request.user

        if user in topic.likes.all():
            topic.likes.remove(user)
        else:
            topic.likes.add(user)

        serializer = self.get_serializer(topic)
        return Response(serializer.data, status=status.HTTP_200_OK)

    def destroy(self, request, *args, **kwargs):
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
    queryset = ForumComment.objects.select_related('user', 'topic').prefetch_related('likes').order_by('created_at')
    serializer_class = ForumCommentSerializer
    parser_classes = [JSONParser, MultiPartParser, FormParser]
    permission_classes = [permissions.IsAuthenticated, OwnerWritePermission]

    def perform_create(self, serializer):
        comment = serializer.save(user=self.request.user)
        topic = comment.topic
        
        if hasattr(topic, 'comments_count'):
            comments_set = getattr(topic, 'comments', getattr(topic, 'forumcomment_set', None))
            if comments_set is not None:
                topic.comments_count = comments_set.count()
                topic.save()

    @action(detail=True, methods=['post'])
    def like(self, request, pk=None):
        comment = self.get_object()
        user = request.user

        if user in comment.likes.all():
            comment.likes.remove(user)
        else:
            comment.likes.add(user)

        serializer = self.get_serializer(comment)
        return Response(serializer.data, status=status.HTTP_200_OK)


# =====================================================================
# NOVA VIEW: CERTIFICADOS
# =====================================================================
class CertificateViewSet(viewsets.ReadOnlyModelViewSet):
    serializer_class = CertificateSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Certificate.objects.filter(user=self.request.user).order_by('-issued_at')


class StudentProjectViewSet(viewsets.ModelViewSet):
    serializer_class = StudentProjectSerializer

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [permissions.AllowAny()]
        return [permissions.IsAuthenticated(), OwnerWritePermission()]

    def get_queryset(self):
        queryset = StudentProject.objects.select_related("user", "course")
        user = self.request.user
        if user.is_authenticated:
            queryset = queryset.filter(Q(status="published") | Q(user=user))
        else:
            queryset = queryset.filter(status="published")
        course = self.request.query_params.get("course")
        if course:
            queryset = queryset.filter(course_id=course)
        return queryset.distinct().order_by("-featured", "-updated_at")

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


# =====================================================================
# NOVA VIEW: PERFIL DE USUÁRIO (ATUALIZAÇÃO DE FOTO DE PERFIL) - CORRIGIDO
# =====================================================================
class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    def get_object(self):
        return self.request.user

    def get_serializer_context(self):
        """ Passa a requisição para o Serializer gerar URLs de mídia absolutas """
        context = super().get_serializer_context()
        context.update({"request": self.request})
        return context


# =====================================================================
# VIEWS JÁ EXISTENTES DA PLATAFORMA DE CURSOS
# =====================================================================
class CourseViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrativeUserOrReadOnly]
    queryset = Course.objects.prefetch_related('modules__lessons').order_by('-created_at')
    serializer_class = CourseSerializer


class EnrollmentViewSet(viewsets.ModelViewSet):
    """Authenticated, owner-scoped and idempotent course enrollments."""

    serializer_class = EnrollmentSerializer
    permission_classes = [permissions.IsAuthenticated]
    http_method_names = ["get", "post", "patch", "head", "options"]

    def get_queryset(self):
        queryset = Enrollment.objects.filter(user=self.request.user).select_related("course")
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_id=course_id)
        return queryset

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        course = serializer.validated_data["course"]

        try:
            with transaction.atomic():
                enrollment, created = Enrollment.objects.get_or_create(
                    user=request.user,
                    course=course,
                    defaults={"status": Enrollment.STATUS_ACTIVE},
                )
        except IntegrityError:
            enrollment = Enrollment.objects.get(user=request.user, course=course)
            created = False

        if enrollment.status == Enrollment.STATUS_CANCELLED:
            enrollment.status = Enrollment.STATUS_ACTIVE
            enrollment.enrolled_at = timezone.now()
            enrollment.save(update_fields=["status", "enrolled_at", "updated_at"])

        output = self.get_serializer(enrollment)
        return Response(
            output.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def partial_update(self, request, *args, **kwargs):
        unexpected = set(request.data) - {"status"}
        if unexpected:
            return Response(
                {"detail": "Somente o status da matrícula pode ser alterado."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return super().partial_update(request, *args, **kwargs)

    @action(detail=False, methods=["get"])
    def courses(self, request):
        courses = Course.objects.filter(
            enrollments__user=request.user,
            enrollments__status=Enrollment.STATUS_ACTIVE,
        ).prefetch_related("modules__lessons").order_by("-enrollments__enrolled_at")
        page = self.paginate_queryset(courses)
        serializer = CourseSerializer(page, many=True, context=self.get_serializer_context())
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path="access")
    def access(self, request):
        """Resolve course access without conflating staff access with enrollment."""

        if request.user.is_staff or request.user.is_superuser:
            access_type = "administrative"
            courses = Course.objects.all()
        else:
            access_type = "enrollment"
            courses = Course.objects.filter(
                enrollments__user=request.user,
                enrollments__status=Enrollment.STATUS_ACTIVE,
            )
            if not courses.exists():
                access_type = "none"

        courses = courses.prefetch_related("modules__lessons").order_by("-created_at")
        return Response(
            {
                "access_type": access_type,
                "courses": CourseSerializer(
                    courses,
                    many=True,
                    context=self.get_serializer_context(),
                ).data,
            }
        )


class CourseProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """Read-only progress derived from the authenticated user's active enrollments."""

    serializer_class = CourseProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return CourseProgress.objects.filter(
            enrollment__user=self.request.user,
            enrollment__status=Enrollment.STATUS_ACTIVE,
        ).select_related("enrollment__course")

    def _active_enrollments(self):
        enrollments = Enrollment.objects.filter(
            user=self.request.user,
            status=Enrollment.STATUS_ACTIVE,
        ).select_related("course")
        course_id = self.request.query_params.get("course")
        if course_id:
            enrollments = enrollments.filter(course_id=course_id)
        return enrollments

    def list(self, request, *args, **kwargs):
        progress_items = [
            CourseProgress.objects.get_or_create(enrollment=enrollment)[0]
            for enrollment in self._active_enrollments()
        ]
        page = self.paginate_queryset(progress_items)
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    @action(detail=False, methods=["get"], url_path=r"by-course/(?P<course_id>[^/.]+)")
    def by_course(self, request, course_id=None):
        enrollment = get_object_or_404(
            Enrollment,
            user=request.user,
            course_id=course_id,
            status=Enrollment.STATUS_ACTIVE,
        )
        progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
        return Response(self.get_serializer(progress).data)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"by-course/(?P<course_id>[^/.]+)/complete",
    )
    def complete(self, request, course_id=None):
        if request.data:
            return Response(
                {"detail": "Esta operação não aceita estado, percentual ou data do cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            progress, _ = complete_course(user=request.user, course_id=course_id)
        except AcademicAccessError:
            return Response(
                {"detail": "Curso não encontrado para uma matrícula ativa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except CourseCompletionError as error:
            return Response(
                {
                    "detail": "O curso ainda não atende aos requisitos acadêmicos de conclusão.",
                    "requirements": error.args[0],
                },
                status=status.HTTP_409_CONFLICT,
            )
        return Response(self.get_serializer(progress).data)


class LearningContinuityView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        step = resolve_learning_continuity(user=request.user)
        payload = {"type": step["type"]}
        course = step.get("course")
        progress = step.get("course_progress")
        enrollment = step.get("enrollment")
        lesson = step.get("lesson")
        if enrollment:
            payload["enrollment"] = {
                "id": enrollment.id,
                "status": enrollment.status,
            }
        if course:
            payload["course"] = {
                "id": course.id,
                "title": course.title,
                "description": course.description,
            }
        if progress:
            payload["course_progress"] = {
                "id": progress.id,
                "percentage": str(progress.percentage),
                "academic_state": progress.academic_state,
                "last_activity_at": progress.last_activity_at,
                "completed_at": progress.completed_at,
            }
        if lesson:
            payload["lesson"] = {
                "id": lesson.id,
                "title": lesson.title,
                "order": lesson.order,
                "module": {
                    "id": lesson.module.id,
                    "title": lesson.module.title,
                    "order": lesson.module.order,
                },
            }
        return Response(payload)


class LessonProgressViewSet(viewsets.ReadOnlyModelViewSet):
    """Owner-scoped lesson state with semantic transition endpoints only."""

    serializer_class = LessonProgressSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        queryset = LessonProgress.objects.filter(
            course_progress__enrollment__user=self.request.user,
            course_progress__enrollment__status=Enrollment.STATUS_ACTIVE,
        ).select_related(
            "course_progress__enrollment__course",
            "lesson__module__course",
        )
        course_id = self.request.query_params.get("course")
        if course_id:
            queryset = queryset.filter(course_progress__enrollment__course_id=course_id)
        return queryset

    @action(detail=False, methods=["get"], url_path=r"by-lesson/(?P<lesson_id>[^/.]+)")
    def by_lesson(self, request, lesson_id=None):
        progress = get_object_or_404(self.get_queryset(), lesson_id=lesson_id)
        return Response(self.get_serializer(progress).data)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"by-lesson/(?P<lesson_id>[^/.]+)/start",
    )
    def start(self, request, lesson_id=None):
        return self._transition(request, lesson_id, start_lesson)

    @action(
        detail=False,
        methods=["post"],
        url_path=r"by-lesson/(?P<lesson_id>[^/.]+)/complete",
    )
    def complete(self, request, lesson_id=None):
        return self._transition(request, lesson_id, complete_lesson)

    def _transition(self, request, lesson_id, transition):
        if request.data:
            return Response(
                {"detail": "Esta operação não aceita estado ou percentual do cliente."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            lesson_progress, _ = transition(user=request.user, lesson_id=lesson_id)
        except (Lesson.DoesNotExist, AcademicAccessError):
            return Response(
                {"detail": "Aula não encontrada para uma matrícula ativa."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except LessonTransitionError:
            return Response(
                {"detail": "A aula precisa ser iniciada antes de ser concluída."},
                status=status.HTTP_409_CONFLICT,
            )
        lesson_progress.refresh_from_db()
        return Response(self.get_serializer(lesson_progress).data)

class ModuleViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAdministrativeUserOrReadOnly]
    queryset = Module.objects.prefetch_related('lessons').order_by('order')
    serializer_class = ModuleSerializer


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.order_by('order')
    serializer_class = LessonSerializer


class ExerciseAttemptListCreateView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, exercise_id):
        get_object_or_404(Exercise, pk=exercise_id)
        attempts = ExerciseAttempt.objects.filter(
            user=request.user,
            exercise_id=exercise_id,
        ).order_by("-attempt_number")
        paginator = PageNumberPagination()
        page = paginator.paginate_queryset(attempts, request, view=self)
        serializer = ExerciseAttemptSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def post(self, request, exercise_id):
        input_serializer = ExerciseAttemptInputSerializer(data=request.data)
        input_serializer.is_valid(raise_exception=True)

        try:
            attempt, created = create_exercise_attempt(
                user=request.user,
                exercise_id=exercise_id,
                **input_serializer.validated_data,
            )
        except Exercise.DoesNotExist:
            return Response(
                {"detail": "Exercício não encontrado."},
                status=status.HTTP_404_NOT_FOUND,
            )
        except AcademicAccessError:
            return Response(
                {"detail": "É necessária uma matrícula ativa no curso do exercício."},
                status=status.HTTP_403_FORBIDDEN,
            )
        except AttemptConflictError:
            return Response(
                {"detail": "A chave de idempotência já foi usada em outra submissão."},
                status=status.HTTP_409_CONFLICT,
            )
        except AttemptPersistenceError:
            return Response(
                {"detail": "Não foi possível registrar a tentativa agora."},
                status=status.HTTP_409_CONFLICT,
            )

        return Response(
            ExerciseAttemptSerializer(attempt).data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )


class ExerciseEvidenceListView(APIView):
    """Read-only aggregate of the authenticated student's attempt evidence."""

    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        attempts = ExerciseAttempt.objects.filter(
            user=request.user,
            exercise__lesson__module__course__enrollments__user=request.user,
        ).select_related("exercise__lesson__module__course").distinct()

        filter_map = {
            "exercise": "exercise_id",
            "lesson": "exercise__lesson_id",
            "course": "exercise__lesson__module__course_id",
        }
        for parameter, field in filter_map.items():
            value = request.query_params.get(parameter)
            if value:
                if not value.isdigit():
                    return Response(
                        {parameter: ["Informe um identificador válido."]},
                        status=status.HTTP_400_BAD_REQUEST,
                    )
                attempts = attempts.filter(**{field: value})

        enrollment_id = request.query_params.get("enrollment")
        if enrollment_id:
            if not enrollment_id.isdigit():
                return Response(
                    {"enrollment": ["Informe um identificador válido."]},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            enrollment = Enrollment.objects.filter(
                pk=enrollment_id,
                user=request.user,
            ).first()
            if enrollment is None:
                attempts = attempts.none()
            else:
                attempts = attempts.filter(
                    exercise__lesson__module__course_id=enrollment.course_id
                )

        evidence = []
        for exercise_id in attempts.order_by().values_list("exercise_id", flat=True).distinct():
            exercise_attempts = attempts.filter(exercise_id=exercise_id).order_by(
                "-attempt_number"
            )
            latest = exercise_attempts.first()
            course = latest.exercise.lesson.module.course
            enrollment = Enrollment.objects.get(user=request.user, course=course)
            evidence.append(
                {
                    "exercise": exercise_id,
                    "lesson": latest.exercise.lesson_id,
                    "course": course.id,
                    "enrollment": enrollment.id,
                    "attempt_count": exercise_attempts.count(),
                    "best_passed": exercise_attempts.filter(passed=True).exists(),
                    "latest_attempt_at": latest.created_at,
                    "latest_attempt": ExerciseAttemptSerializer(latest).data,
                }
            )
        return Response(evidence)


class PasswordResetRequestView(APIView):
    """Requests a password reset without revealing whether an account exists."""

    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = str(request.data.get("email", "")).strip()
        user = None

        if email:
            user = get_user_model().objects.filter(
                email__iexact=email,
                is_active=True,
            ).first()

        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            frontend_url = getattr(
                settings,
                "FRONTEND_URL",
                "http://localhost:5173",
            ).rstrip("/")
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
