import uuid
import json
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
    list_display = ["title", "number", "date", "department",
                    "realization", "grade", "executor",
                    "source", "direction", "open_file",]  # "task", "subtask",

    list_filter = [("date", DateRangeFilter), "grade", "executor", "source", "direction","realization", "department"]  # "task", "subtask"
    inlines = (DocumentTaskInline,)

    def open_file(self, obj):
        if not obj.storage_key:
            return "—"
        url = reverse("document_open", args=[obj.pk])
        label = "Скачать ZIP" if obj.content_type == "folder" else "Открыть"
        return format_html('<a href="{}" target="_blank">{}</a>', url, label)

    open_file.short_description = "Файл"

    def save_model(self, request, obj, form, change):
        files = request.FILES.getlist('file')
        file_paths_json = request.POST.get('file_paths')

        if files:
            client = get_minio_client()

            # bucket создаём один раз, если вдруг не существует
            if not client.bucket_exists(settings.MINIO_BUCKET):
                client.make_bucket(settings.MINIO_BUCKET)

            now = timezone.now()
            department = (
                obj.executor.department
                if obj.executor and obj.executor.department
                else None
            )
            dept_title = department.title if department else "no_department"
            # Sanitize replacement to avoid path issues
            dept_title = dept_title.replace("/", "_") 

            uuid_hex = uuid.uuid4().hex
            prefix = f"{dept_title}/{now:%Y/%m}/{uuid_hex}/"
            
            path_data = []
            if file_paths_json:
                try:
                    path_data = json.loads(file_paths_json)
                except json.JSONDecodeError:
                    pass
            
            total_size = 0
            
            # Map for index-based or name-based matching
            use_index = len(files) == len(path_data)

            for i, uploaded_file in enumerate(files):
                # Default relative path is just the filename
                rel_path = uploaded_file.name 
                
                if use_index:
                    if path_data[i].get('name') == uploaded_file.name:
                        # Use captured relative path from JS
                        rel_path = path_data[i].get('path')
                else:
                    # Fallback: try to find by name
                    for p in path_data:
                        if p.get('name') == uploaded_file.name:
                            rel_path = p.get('path')
                            break
                            
                # Ensure no leading slashes to append correctly to prefix
                rel_path = rel_path.lstrip('/')
                
                key = prefix + rel_path
                
                # content-type
                content_type = getattr(uploaded_file, "content_type", None) or "application/octet-stream"
                
                # Upload
                client.put_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=key,
                    data=uploaded_file.file,
                    length=uploaded_file.size,
                    content_type=content_type,
                )
                
                total_size += uploaded_file.size

            # Save metadata
            obj.storage_key = prefix
            
            # Decide content type and original filename
            # If explicit folder structure found or multiple files
            if len(files) > 1 or (path_data and '/' in str(path_data[0].get('path', ''))):
                obj.content_type = "folder"
                # Try to get root folder name from the first path
                first_path = path_data[0].get('path') if path_data else files[0].name
                parts = first_path.split('/')
                obj.original_filename = parts[0] if len(parts) > 1 else "folder"
            else:
                # Single file uploaded as file (or single file in folder)
                # Note: if it was single file in folder, webkitRelativePath still has path
                # But if just file selection, no path.
                if path_data and '/' in path_data[0].get('path', ''):
                     obj.content_type = "folder"
                     obj.original_filename = path_data[0].get('path').split('/')[0]
                else:
                     obj.content_type = getattr(files[0], "content_type", "application/octet-stream")
                     obj.original_filename = files[0].name
            
            obj.size_bytes = total_size

        super().save_model(request, obj, form, change)

