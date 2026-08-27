from django.urls import path

from .views import (
    BookProcessView, BookStatusView, BookUploadView, LibraryScanView,
    LibrarySourceListView, ScriptDetailView, ScriptGenerateView,
    ScriptListView, TrilhaListView,
)

urlpatterns = [
    path("scan/", LibraryScanView.as_view(), name="library-scan"),
    path("sources/", LibrarySourceListView.as_view(), name="library-source-list"),
    path("books/", BookUploadView.as_view(), name="library-book-upload"),
    path("books/<int:pk>/process/", BookProcessView.as_view(), name="library-book-process"),
    path("books/<int:pk>/status/", BookStatusView.as_view(), name="library-book-status"),
    path("trilhas/", TrilhaListView.as_view(), name="library-trilha-list"),
    path("scripts/generate/", ScriptGenerateView.as_view(), name="library-script-generate"),
    path("scripts/", ScriptListView.as_view(), name="library-script-list"),
    path("scripts/<int:pk>/", ScriptDetailView.as_view(), name="library-script-detail"),
]
