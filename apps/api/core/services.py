from dataclasses import dataclass

from django.db import IntegrityError, transaction
from django.db.models import Max

from .models import Exercise, ExerciseAttempt, MAX_SUBMITTED_ANSWER_LENGTH


EVALUATION_VERSION = "v1"
MAX_ATTEMPT_PERSISTENCE_TRIES = 3
IDEMPOTENCY_CONSTRAINT = "unique_user_attempt_idempotency_key"
ATTEMPT_NUMBER_CONSTRAINT = "unique_user_exercise_attempt_number"


class AttemptConflictError(Exception):
    """An idempotency key was reused for a materially different request."""


class AttemptPersistenceError(Exception):
    """A concurrent attempt could not be persisted safely."""


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

    exercise = Exercise.objects.get(pk=exercise_id)
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
