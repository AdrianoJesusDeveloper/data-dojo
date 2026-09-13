from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Course, Module, Lesson, Exercise, User, StudentProject, Enrollment, CourseProgress, LessonProgress


@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('email', 'first_name', 'last_name', 'is_staff')
    ordering = ('email',)


@admin.register(Course)
class CourseAdmin(admin.ModelAdmin):
    list_display = ('title',)


@admin.register(Enrollment)
class EnrollmentAdmin(admin.ModelAdmin):
    list_display = ('user', 'course', 'status', 'enrolled_at', 'updated_at')
    list_filter = ('status', 'course')
    search_fields = ('user__email', 'user__username', 'course__title')
    readonly_fields = ('user', 'course', 'enrolled_at', 'created_at', 'updated_at')


@admin.register(CourseProgress)
class CourseProgressAdmin(admin.ModelAdmin):
    list_display = ('enrollment', 'percentage', 'academic_state', 'last_activity_at', 'updated_at')
    list_filter = ('academic_state',)
    search_fields = ('enrollment__user__email', 'enrollment__course__title')
    readonly_fields = (
        'enrollment', 'percentage', 'academic_state', 'first_activity_at',
        'last_activity_at', 'created_at', 'updated_at',
    )


@admin.register(LessonProgress)
class LessonProgressAdmin(admin.ModelAdmin):
    list_display = ('course_progress', 'lesson', 'status', 'last_activity_at', 'updated_at')
    list_filter = ('status', 'lesson__module__course')
    search_fields = ('course_progress__enrollment__user__email', 'lesson__title')
    readonly_fields = (
        'course_progress', 'lesson', 'status', 'started_at', 'last_activity_at',
        'completed_at', 'created_at', 'updated_at',
    )


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
