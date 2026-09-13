from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from django.db import IntegrityError, transaction
from django.db.models import Max
from django.utils import timezone

from .models import (
    CourseProgress,
    Enrollment,
    Exercise,
    ExerciseAttempt,
    Lesson,
    LessonProgress,
    MAX_SUBMITTED_ANSWER_LENGTH,
)


EVALUATION_VERSION = "v1"
MAX_ATTEMPT_PERSISTENCE_TRIES = 3
IDEMPOTENCY_CONSTRAINT = "unique_user_attempt_idempotency_key"
ATTEMPT_NUMBER_CONSTRAINT = "unique_user_exercise_attempt_number"


class AttemptConflictError(Exception):
    """An idempotency key was reused for a materially different request."""


class AttemptPersistenceError(Exception):
    """A concurrent attempt could not be persisted safely."""


class AcademicAccessError(Exception):
    """The authenticated user has no active enrollment for the lesson."""


class LessonTransitionError(Exception):
    """The requested lesson transition is not valid from its current state."""


class CourseCompletionError(Exception):
    """The enrollment does not currently satisfy the modeled course requirements."""


@dataclass(frozen=True)
class EvaluationResult:
    passed: bool
    feedback: dict
    version: str = EVALUATION_VERSION


def evaluate_submission(exercise, submitted_answer):
    if not isinstance(submitted_answer, str):
        raise TypeError("submitted_answer must be a string")
    if not submitted_answer.strip():
        raise ValueError("submitted_answer must not be empty")
    if len(submitted_answer) > MAX_SUBMITTED_ANSWER_LENGTH:
        raise ValueError("submitted_answer is too long")

    try:
        passed = exercise.evaluate_answer(submitted_answer)
    except (AttributeError, TypeError, ValueError):
        return EvaluationResult(
            passed=False,
            feedback={
                "code": "evaluation_unavailable",
                "message": "Não foi possível avaliar esta resposta agora.",
            },
        )

    if passed:
        return EvaluationResult(
            passed=True,
            feedback={"code": "accepted", "message": "Resposta aprovada."},
        )
    return EvaluationResult(
        passed=False,
        feedback={
            "code": "not_accepted",
            "message": "A resposta ainda não atende aos critérios do exercício.",
        },
    )


def _known_constraint(error):
    """Return only the constraint violations this workflow can safely recover from."""

    cause = getattr(error, "__cause__", None)
    diagnostic = getattr(cause, "diag", None)
    constraint_name = getattr(diagnostic, "constraint_name", None)
    if constraint_name in {IDEMPOTENCY_CONSTRAINT, ATTEMPT_NUMBER_CONSTRAINT}:
        return constraint_name

    # SQLite does not expose constraint names, only the columns in the message.
    message = str(error).casefold()
    if (
        "unique constraint failed" in message
        and "core_exerciseattempt.user_id" in message
        and "core_exerciseattempt.idempotency_key" in message
    ):
        return IDEMPOTENCY_CONSTRAINT
    if (
        "unique constraint failed" in message
        and "core_exerciseattempt.user_id" in message
        and "core_exerciseattempt.exercise_id" in message
        and "core_exerciseattempt.attempt_number" in message
    ):
        return ATTEMPT_NUMBER_CONSTRAINT
    return None


def create_exercise_attempt(*, user, exercise_id, idempotency_key, submitted_answer):
    """Create once, or return the matching attempt for an idempotent replay."""

    exercise = Exercise.objects.select_related("lesson__module__course").get(pk=exercise_id)
    enrollment = Enrollment.objects.filter(
        user=user,
        course=exercise.lesson.module.course,
        status=Enrollment.STATUS_ACTIVE,
    ).first()
    if enrollment is None:
        raise AcademicAccessError
    course_progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
    result = evaluate_submission(exercise, submitted_answer)

    for attempt_index in range(MAX_ATTEMPT_PERSISTENCE_TRIES):
        try:
            with transaction.atomic():
                existing = ExerciseAttempt.objects.filter(
                    user=user,
                    idempotency_key=idempotency_key,
                ).first()
                if existing:
                    if (
                        existing.exercise_id != exercise.id
                        or existing.submitted_answer != submitted_answer
                    ):
                        raise AttemptConflictError
                    return existing, False

                next_number = (
                    ExerciseAttempt.objects.filter(user=user, exercise=exercise).aggregate(
                        maximum=Max("attempt_number")
                    )["maximum"]
                    or 0
                ) + 1
                created = ExerciseAttempt.objects.create(
                    user=user,
                    exercise=exercise,
                    idempotency_key=idempotency_key,
                    submitted_answer=submitted_answer,
                    attempt_number=next_number,
                    passed=result.passed,
                    feedback=result.feedback,
                    evaluation_version=result.version,
                )
                locked_course_progress = CourseProgress.objects.select_for_update().get(
                    pk=course_progress.pk
                )
                _record_exercise_activity(
                    course_progress=locked_course_progress,
                    lesson=exercise.lesson,
                    activity_at=created.created_at,
                )
                return created, True
        except IntegrityError as error:
            constraint = _known_constraint(error)
            if constraint is None:
                raise

            existing = ExerciseAttempt.objects.filter(
                user=user,
                idempotency_key=idempotency_key,
            ).first()
            if existing:
                if (
                    existing.exercise_id != exercise_id
                    or existing.submitted_answer != submitted_answer
                ):
                    raise AttemptConflictError from error
                return existing, False

            if constraint == IDEMPOTENCY_CONSTRAINT:
                if attempt_index == MAX_ATTEMPT_PERSISTENCE_TRIES - 1:
                    raise AttemptPersistenceError from error
                continue

            if attempt_index == MAX_ATTEMPT_PERSISTENCE_TRIES - 1:
                raise AttemptPersistenceError from error

    raise AttemptPersistenceError


def _record_exercise_activity(*, course_progress, lesson, activity_at):
    """Record a real attempt as activity without completing the lesson."""

    lesson_progress, _ = LessonProgress.objects.get_or_create(
        course_progress=course_progress,
        lesson=lesson,
    )
    if lesson_progress.status == LessonProgress.STATUS_NOT_STARTED:
        lesson_progress.status = LessonProgress.STATUS_IN_PROGRESS
        lesson_progress.started_at = activity_at
    lesson_progress.last_activity_at = activity_at
    lesson_progress.save(
        update_fields=["status", "started_at", "last_activity_at", "updated_at"]
    )

    update_fields = ["last_activity_at", "academic_state", "updated_at"]
    if course_progress.first_activity_at is None:
        course_progress.first_activity_at = activity_at
        update_fields.append("first_activity_at")
    course_progress.last_activity_at = activity_at
    if course_progress.academic_state != CourseProgress.STATE_COMPLETED:
        course_progress.academic_state = CourseProgress.STATE_IN_PROGRESS
    course_progress.save(update_fields=update_fields)


def _resolve_academic_context(*, user, lesson_id):
    lesson = Lesson.objects.select_related("module__course").get(pk=lesson_id)
    enrollment = Enrollment.objects.filter(
        user=user,
        course=lesson.module.course,
        status=Enrollment.STATUS_ACTIVE,
    ).first()
    if enrollment is None:
        raise AcademicAccessError
    course_progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
    return lesson, course_progress


def recalculate_course_progress(course_progress, *, activity_at=None):
    """Derive course percentage exclusively from completed lesson records."""

    course_id = course_progress.enrollment.course_id
    total_lessons = Lesson.objects.filter(module__course_id=course_id).count()
    completed_lessons = course_progress.lesson_progress.filter(
        lesson__module__course_id=course_id,
        status=LessonProgress.STATUS_COMPLETED,
    ).count()
    percentage = Decimal("0.00")
    if total_lessons:
        percentage = (
            Decimal(completed_lessons) * Decimal(100) / Decimal(total_lessons)
        ).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

    course_progress.percentage = percentage
    if course_progress.academic_state == CourseProgress.STATE_COMPLETED:
        pass
    elif course_progress.lesson_progress.exists():
        course_progress.academic_state = CourseProgress.STATE_IN_PROGRESS
    else:
        course_progress.academic_state = CourseProgress.STATE_NOT_STARTED

    update_fields = ["percentage", "academic_state", "updated_at"]
    if activity_at is not None:
        if course_progress.first_activity_at is None:
            course_progress.first_activity_at = activity_at
            update_fields.append("first_activity_at")
        course_progress.last_activity_at = activity_at
        update_fields.append("last_activity_at")
    course_progress.save(update_fields=update_fields)
    return course_progress


def evaluate_course_completion(*, course_progress):
    """Evaluate only requirements explicitly represented by the current domain."""

    enrollment = course_progress.enrollment
    total_lessons = Lesson.objects.filter(module__course_id=enrollment.course_id).count()
    completed_lessons = course_progress.lesson_progress.filter(
        lesson__module__course_id=enrollment.course_id,
        status=LessonProgress.STATUS_COMPLETED,
    ).count()
    return {
        "eligible": (
            enrollment.status == Enrollment.STATUS_ACTIVE
            and total_lessons > 0
            and completed_lessons == total_lessons
            and course_progress.percentage == Decimal("100.00")
        ),
        "total_lessons": total_lessons,
        "completed_lessons": completed_lessons,
    }


def complete_course(*, user, course_id):
    """Persist an explicit, idempotent academic completion transition."""

    with transaction.atomic():
        enrollment = Enrollment.objects.select_related("course").filter(
            user=user,
            course_id=course_id,
            status=Enrollment.STATUS_ACTIVE,
        ).first()
        if enrollment is None:
            raise AcademicAccessError
        course_progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
        course_progress = CourseProgress.objects.select_for_update().select_related(
            "enrollment"
        ).get(pk=course_progress.pk)
        if course_progress.academic_state == CourseProgress.STATE_COMPLETED:
            return course_progress, False
        recalculate_course_progress(course_progress)
        eligibility = evaluate_course_completion(course_progress=course_progress)
        if not eligibility["eligible"]:
            raise CourseCompletionError(eligibility)
        now = timezone.now()
        course_progress.academic_state = CourseProgress.STATE_COMPLETED
        course_progress.completed_at = now
        course_progress.last_activity_at = now
        if course_progress.first_activity_at is None:
            course_progress.first_activity_at = now
        course_progress.save(
            update_fields=[
                "academic_state",
                "completed_at",
                "first_activity_at",
                "last_activity_at",
                "updated_at",
            ]
        )
        return course_progress, True


def resolve_learning_continuity(*, user):
    """Resolve one deterministic next academic action for the authenticated user."""

    if user.is_staff or user.is_superuser:
        return {"type": "administrative"}

    enrollments = list(
        Enrollment.objects.filter(user=user, status=Enrollment.STATUS_ACTIVE)
        .select_related("course", "progress")
        .prefetch_related("course__modules__lessons", "progress__lesson_progress")
    )
    if not enrollments:
        return {"type": "no_enrollment"}

    def activity_key(enrollment):
        progress = getattr(enrollment, "progress", None)
        return (
            progress.last_activity_at if progress and progress.last_activity_at else enrollment.enrolled_at,
            enrollment.pk,
        )

    enrollment = max(enrollments, key=activity_key)
    course_progress, _ = CourseProgress.objects.get_or_create(enrollment=enrollment)
    lessons = sorted(
        [lesson for module in enrollment.course.modules.all() for lesson in module.lessons.all()],
        key=lambda lesson: (lesson.module.order, lesson.order, lesson.pk),
    )
    base = {
        "enrollment": enrollment,
        "course_progress": course_progress,
        "course": enrollment.course,
        "lesson": None,
    }
    if course_progress.academic_state == CourseProgress.STATE_COMPLETED:
        return {**base, "type": "course_completed"}

    progress_by_lesson = {
        item.lesson_id: item for item in course_progress.lesson_progress.all()
    }
    in_progress = [
        item for item in progress_by_lesson.values()
        if item.status == LessonProgress.STATUS_IN_PROGRESS
    ]
    if in_progress:
        latest = max(in_progress, key=lambda item: (item.last_activity_at, item.pk))
        return {**base, "type": "continue_lesson", "lesson": latest.lesson}

    incomplete = [
        lesson for lesson in lessons
        if progress_by_lesson.get(lesson.pk) is None
        or progress_by_lesson[lesson.pk].status != LessonProgress.STATUS_COMPLETED
    ]
    if incomplete:
        completed_positions = [
            index for index, lesson in enumerate(lessons)
            if progress_by_lesson.get(lesson.pk)
            and progress_by_lesson[lesson.pk].status == LessonProgress.STATUS_COMPLETED
        ]
        if completed_positions:
            last_completed = max(completed_positions)
            lesson = next(
                (candidate for candidate in lessons[last_completed + 1:] if candidate in incomplete),
                incomplete[0],
            )
            step_type = "next_lesson"
        else:
            lesson = incomplete[0]
            step_type = "start_course"
        return {**base, "type": step_type, "lesson": lesson}

    return {**base, "type": "complete_course"}


def start_lesson(*, user, lesson_id):
    with transaction.atomic():
        lesson, course_progress = _resolve_academic_context(user=user, lesson_id=lesson_id)
        course_progress = CourseProgress.objects.select_for_update().get(pk=course_progress.pk)
        lesson_progress, _ = LessonProgress.objects.get_or_create(
            course_progress=course_progress,
            lesson=lesson,
        )
        now = timezone.now()
        if lesson_progress.status == LessonProgress.STATUS_NOT_STARTED:
            lesson_progress.status = LessonProgress.STATUS_IN_PROGRESS
            lesson_progress.started_at = now
        if lesson_progress.status != LessonProgress.STATUS_COMPLETED:
            lesson_progress.last_activity_at = now
            lesson_progress.save(
                update_fields=["status", "started_at", "last_activity_at", "updated_at"]
            )
            recalculate_course_progress(course_progress, activity_at=now)
        return lesson_progress, course_progress


def complete_lesson(*, user, lesson_id):
    with transaction.atomic():
        lesson, course_progress = _resolve_academic_context(user=user, lesson_id=lesson_id)
        course_progress = CourseProgress.objects.select_for_update().get(pk=course_progress.pk)
        lesson_progress = LessonProgress.objects.filter(
            course_progress=course_progress,
            lesson=lesson,
        ).first()
        if lesson_progress is None or lesson_progress.status == LessonProgress.STATUS_NOT_STARTED:
            raise LessonTransitionError
        if lesson_progress.status == LessonProgress.STATUS_COMPLETED:
            return lesson_progress, course_progress

        now = timezone.now()
        lesson_progress.status = LessonProgress.STATUS_COMPLETED
        lesson_progress.completed_at = now
        lesson_progress.last_activity_at = now
        lesson_progress.save(
            update_fields=["status", "completed_at", "last_activity_at", "updated_at"]
        )
        recalculate_course_progress(course_progress, activity_at=now)
        return lesson_progress, course_progress
