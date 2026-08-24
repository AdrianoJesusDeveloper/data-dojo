from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Course, Module, Lesson, Exercise, User, StudentProject


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(Module)
class ModuleAdmin(admin.ModelAdmin):
    list_display = ('title', 'course')
    list_filter = ('course',)


@admin.register(Lesson)
class LessonAdmin(admin.ModelAdmin):
    list_display = ('title', 'module', 'content_type')
    list_filter = ('content_type', 'module__course')


@admin.register(Exercise)
class ExerciseAdmin(admin.ModelAdmin):
    list_display = ('title', 'lesson', 'answer_type', 'evaluation_mode', 'points')
    list_filter = ('answer_type', 'evaluation_mode', 'lesson__module__course')


@admin.register(StudentProject)
class StudentProjectAdmin(admin.ModelAdmin):
    list_display = ('title', 'user', 'course', 'status', 'featured', 'updated_at')
    list_filter = ('status', 'featured', 'course')
    search_fields = ('title', 'summary', 'user__username', 'course__title')
    readonly_fields = ('user', 'created_at', 'updated_at')
