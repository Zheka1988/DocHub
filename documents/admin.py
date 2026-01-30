import uuid
from pathlib import Path
from django.contrib import admin
from django.utils import timezone
from django.urls import reverse
from django.utils.html import format_html
from django.conf import settings
from .models import Document, Task, SubTask, Source, Direction, DocumentTask,DocumentSubTask
from .forms import DocumentAdminForm
from rangefilter.filters import DateRangeFilter
from .minio_client import get_minio_client
from .admin_inline import DocumentTaskInline, DocumentSubTaskInline
import nested_admin


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    """Направление"""
    search_fields = ("title",)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    """Источник"""
    search_fields = ("title",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Задача"""
    search_fields = ("title",)
    list_display = ("title", "description", "is_closed", "created_at")
    list_filter = ("is_closed",)


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    """Подзадача"""
    list_display = ("title", "task", "is_closed", "created_at")
    list_filter = ("task", "is_closed")
    search_fields = ("title", "task__title")


@admin.register(DocumentTask)
class DocumentTaskAdmin(admin.ModelAdmin):
    """Задачи (документы)"""
    list_display = ("document", "task", "closes_task_fully")
    list_filter = ("closes_task_fully", "task")
    search_fields = ("document__number", "document__title", "task__title")
    autocomplete_fields = ("document", "task")
    inlines = (DocumentSubTaskInline,)

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.closes_task_fully:
            obj.covered_subtasks.all().delete()
            subtasks = obj.task.subtasks.all()
            DocumentSubTask.objects.bulk_create(
                [DocumentSubTask(document_task=obj, subtask=st) for st in subtasks],
                ignore_conflicts=True,
            )


@admin.register(DocumentSubTask)
class DocumentSubTaskAdmin(admin.ModelAdmin):
    """Подзадачи (документы)"""
    list_display = ("document_task", "subtask",)
    list_filter = ("document_task__task",)
    search_fields = (
        "document_task__document__number",
        "document_task__document__title",
        "document_task__task__title",
        "subtask__title",
    )
    autocomplete_fields = ("document_task", "subtask")


@admin.register(Document)
class DocumentAdmin(nested_admin.NestedModelAdmin):
    """Документ"""
    form = DocumentAdminForm
    readonly_fields = ("storage_key", "original_filename", "content_type", "size_bytes")
    # exclude = ("storage_key", "original_filename", "content_type", "size_bytes")
    search_fields = ["title", "number", "realization"]
    list_display = ["title", "number", "date",
                    "realization", "grade", "executor",
                    "source", "direction", "open_file",]  # "task", "subtask",

    list_filter = [("date", DateRangeFilter), "grade", "executor", "source", "direction","realization"]  # "task", "subtask"
    inlines = (DocumentTaskInline,)

    def open_file(self, obj):
        if not obj.storage_key:
            return "—"
        url = reverse("document_open", args=[obj.pk])
        return format_html('<a href="{}" target="_blank">Открыть</a>', url)

    open_file.short_description = "Файл"

    # def save_model(self, request, obj, form, change):
    #     uploaded = form.cleaned_data.get("file")
    #
    #     if uploaded:
    #         client = get_minio_client()
    #
    #         # bucket создаём один раз, если вдруг не существует
    #         if not client.bucket_exists(settings.MINIO_BUCKET):
    #             client.make_bucket(settings.MINIO_BUCKET)
    #
    #         # ключ в MinIO: documents/2026/01/<uuid>.<ext>
    #         ext = Path(uploaded.name).suffix
    #         now = timezone.now()
    #         department = (
    #             obj.executor.department
    #             if obj.executor and obj.executor.department
    #             else None
    #         )
    #
    #         key = f"{department.title}/{now:%Y/%m}/{uuid.uuid4().hex}{ext}"
    #
    #         # размер
    #         size = uploaded.size
    #
    #         # content-type (если не пришёл — поставим application/octet-stream)
    #         content_type = getattr(uploaded, "content_type", None) or "application/octet-stream"
    #
    #         # ВАЖНО: перед put_object файл читается как поток
    #         client.put_object(
    #             bucket_name=settings.MINIO_BUCKET,
    #             object_name=key,
    #             data=uploaded.file,
    #             length=size,
    #             content_type=content_type,
    #         )
    #
    #         # сохраняем в БД то, что нужно
    #         obj.storage_key = key
    #         obj.original_filename = uploaded.name
    #         obj.content_type = content_type
    #         obj.size_bytes = size
    #
    #     super().save_model(request, obj, form, change)
def save_model(self, request, obj, form, change):
    files = request.FILES.getlist("file")  # <-- важно

    if files:
        client = get_minio_client()
        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)

        now = timezone.now()
        department = obj.executor.department if obj.executor and obj.executor.department else None
        dept = department.title if department else "no_department"

        base = f"{dept}/{now:%Y/%m}/{uuid.uuid4().hex}/"  # папка документа

        # грузим ВСЕ файлы из выбранной папки (с сохранением структуры)
        for f in files:
            # f.name может быть "folder/sub/file.pdf" (если выбрали папку)
            key = base + f.name.replace("\\", "/")

            content_type = getattr(f, "content_type", None) or "application/octet-stream"
            client.put_object(
                bucket_name=settings.MINIO_BUCKET,
                object_name=key,
                data=f.file,
                length=f.size,
                content_type=content_type,
            )

        # В БД: храним корневой ключ папки (а не одного файла)
        obj.storage_key = base
        obj.original_filename = ""  # можно не хранить
        obj.content_type = "folder"
        obj.size_bytes = sum(f.size for f in files)

    super().save_model(request, obj, form, change)
