from rest_framework import viewsets

from .models import Course, Module, Lesson
from .serializers import CourseSerializer, LessonSerializer, ModuleSerializer


class CourseViewSet(viewsets.ModelViewSet):
    queryset = Course.objects.prefetch_related('modules__lessons').order_by('-created_at')
    serializer_class = CourseSerializer


class ModuleViewSet(viewsets.ModelViewSet):
    queryset = Module.objects.prefetch_related('lessons').order_by('order')
    serializer_class = ModuleSerializer


class LessonViewSet(viewsets.ModelViewSet):
    queryset = Lesson.objects.order_by('order')
    serializer_class = LessonSerializer
