from django.contrib import admin

from .models import Opportunity, OpportunityAnalysis, OpportunityBriefing, OpportunityExecutionPlan, OpportunityProposal, ProfessionalModality


@admin.register(ProfessionalModality)
class ProfessionalModalityAdmin(admin.ModelAdmin):
    list_display = ("name", "domain", "is_active", "sort_order")
    list_filter = ("domain", "is_active")
    search_fields = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}


@admin.register(Opportunity)
class OpportunityAdmin(admin.ModelAdmin):
    list_display = ("title", "created_by", "source", "status", "created_at")
    list_filter = ("source", "status")
    search_fields = ("title", "client_name", "created_by__email")
    filter_horizontal = ("modalities",)


@admin.register(OpportunityBriefing)
class OpportunityBriefingAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "created_by", "ai_provider", "ai_model", "updated_at")
    search_fields = ("opportunity__title", "created_by__email")
    readonly_fields = ("created_by", "ai_provider", "ai_model", "created_at", "updated_at")


@admin.register(OpportunityAnalysis)
class OpportunityAnalysisAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "decision", "score", "ai_provider", "generated_at")
    list_filter = ("decision", "ai_provider")
    readonly_fields = ("created_by", "ai_provider", "ai_model", "generated_at", "created_at", "updated_at")


@admin.register(OpportunityProposal)
class OpportunityProposalAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "version", "status", "suggested_price", "updated_at")
    list_filter = ("version", "status")
    readonly_fields = ("created_by", "ai_provider", "ai_model", "approved_at", "generated_at", "created_at", "updated_at")


@admin.register(OpportunityExecutionPlan)
class OpportunityExecutionPlanAdmin(admin.ModelAdmin):
    list_display = ("opportunity", "status", "ai_provider", "generated_at")
    readonly_fields = ("created_by", "ai_provider", "ai_model", "generated_at", "created_at", "updated_at")
