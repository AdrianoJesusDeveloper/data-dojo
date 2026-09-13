from django.contrib import admin

from .models import (
    Book, BookChunk, GeneratedScript, LibrarySource, SenseiCompetency,
    SenseiCompetencyEvidence, SenseiCompetencyProgress, SenseiFormation,
    SenseiFormationModule, SenseiProgress, SenseiStudyJourney, SenseiStudyNote, SenseiStudyUnit,
    SenseiUnitSource, SenseiUnitSourceGap, SenseiUnitStudyPlan, SenseiUnitStudyProgress, Trilha,
)


@admin.register(LibrarySource)
class LibrarySourceAdmin(admin.ModelAdmin):
    list_display = ("filename", "extension", "status", "size_bytes", "last_seen_at")
    list_filter = ("status", "extension")
    search_fields = ("relative_path", "filename", "sha256")
    readonly_fields = ("relative_path", "sha256", "discovered_at", "last_seen_at")


@admin.register(Trilha)
class TrilhaAdmin(admin.ModelAdmin):
    list_display = ("nome", "ordem")
    ordering = ("ordem", "nome")


@admin.register(Book)
class BookAdmin(admin.ModelAdmin):
    list_display = ("title", "author", "trilha", "status", "total_chunks", "created_at")
    list_filter = ("status", "trilha")
    search_fields = ("title", "author")


@admin.register(BookChunk)
class BookChunkAdmin(admin.ModelAdmin):
    list_display = ("book", "chunk_index", "page_number")
    search_fields = ("book__title", "content")


@admin.register(GeneratedScript)
class GeneratedScriptAdmin(admin.ModelAdmin):
    list_display = ("titulo_video", "trilha", "created_by", "created_at")
    filter_horizontal = ("books",)


@admin.register(SenseiFormation)
class SenseiFormationAdmin(admin.ModelAdmin):
    list_display = ("title", "status", "level", "created_by", "updated_at")
    list_filter = ("status", "level")
    search_fields = ("title", "slug", "description", "objective")


admin.site.register(SenseiFormationModule)
admin.site.register(SenseiStudyUnit)
admin.site.register(SenseiCompetency)
admin.site.register(SenseiCompetencyEvidence)
admin.site.register(SenseiProgress)
admin.site.register(SenseiCompetencyProgress)
admin.site.register(SenseiStudyJourney)
admin.site.register(SenseiUnitSource)
admin.site.register(SenseiUnitSourceGap)
admin.site.register(SenseiUnitStudyPlan)
admin.site.register(SenseiStudyNote)
admin.site.register(SenseiUnitStudyProgress)
