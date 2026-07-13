from rest_framework import serializers

from .models import Course, Module, Lesson, Exercise


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
