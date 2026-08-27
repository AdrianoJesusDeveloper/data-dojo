from django.urls import path

from .views import (
    BookProcessView, BookStatusView, BookUploadView, LibraryScanView,
    LibrarySourceListView, ScriptDetailView, ScriptGenerateView,
    ScriptListView, StudioApprovalView, StudioGenerateContentView,
    StudioGeneratePlanView, StudioProjectDetailView, StudioProjectListCreateView,
    StudioStatusView, TrilhaListView,
)

urlpatterns = [
    path("studio/status/", StudioStatusView.as_view(), name="library-studio-status"),
    path("studio/scan/", LibraryScanView.as_view(), name="library-studio-scan"),
    path("sources/", LibrarySourceListView.as_view(), name="library-source-list"),
    path("studio/projects/", StudioProjectListCreateView.as_view(), name="library-studio-projects"),
    path("studio/projects/<int:pk>/", StudioProjectDetailView.as_view(), name="library-studio-project-detail"),
    path("studio/projects/<int:pk>/generate-plan/", StudioGeneratePlanView.as_view(), name="library-studio-generate-plan"),
    path("studio/projects/<int:pk>/approve/", StudioApprovalView.as_view(), name="library-studio-approve"),
    path("studio/projects/<int:pk>/generate-content/", StudioGenerateContentView.as_view(), name="library-studio-generate-content"),
    path("books/", BookUploadView.as_view(), name="library-book-upload"),
    path("books/<int:pk>/process/", BookProcessView.as_view(), name="library-book-process"),
    path("books/<int:pk>/status/", BookStatusView.as_view(), name="library-book-status"),
    path("trilhas/", TrilhaListView.as_view(), name="library-trilha-list"),
    path("scripts/generate/", ScriptGenerateView.as_view(), name="library-script-generate"),
    path("scripts/", ScriptListView.as_view(), name="library-script-list"),
    path("scripts/<int:pk>/", ScriptDetailView.as_view(), name="library-script-detail"),
]
