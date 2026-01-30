import uuid
import re
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
    list_display = ("task", "document")  # "closes_task_fully"
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
    list_display = ("subtask", "get_task", "get_document")

    list_filter = ("document_task__task", "document_task__document")
    search_fields = (
        "document_task__document__number",
        "document_task__document__title",
        "document_task__task__title",
        "subtask__title",
    )
    autocomplete_fields = ("document_task", "subtask")

    @admin.display(description="Задача", ordering="document_task__task__title")
    def get_task(self, obj):
        return obj.document_task.task

    @admin.display(description="Документ", ordering="document_task__document__number")
    def get_document(self, obj):
        d = obj.document_task.document
        # чтобы было понятнее, можно вернуть "№ - заголовок"
        return f"№{d.number} — {d.date}" if getattr(d, "title", None) else f"№{d.number}"


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

    list_filter = [("date", DateRangeFilter), "grade", "executor", "source", "direction","realization", "department", "document_tasks__task"]  # "task", "subtask"
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

            # New MinIO path logic
            # Structure: <year>/<dept>/<month>/<source>/<doc_folder>/
            # doc_folder: <number>-<date>
            
            # 1. Extract params
            year_str = obj.date.strftime("%Y")
            month_str = obj.date.strftime("%m")
            date_str = obj.date.strftime("%Y.%m.%d")
            
            dept_title = obj.department.title
            source_title = obj.source.title
            number_str = str(obj.number)
            
            # 2. Sanitize params (replace invalid chars with _ or -)
            def sanitize(s, replace_with='_'):
                return re.sub(r'[\\/*?:"<>|]', replace_with, str(s))

            safe_dept = sanitize(dept_title)
            safe_source = sanitize(source_title)
            # Use - for number as requested
            safe_number = sanitize(number_str, '-') 
            
            # 3. Construct doc_folder
            doc_folder = f"{safe_number}-{date_str}"
            
            # 4. Construct prefix
            prefix = f"{year_str}/{safe_dept}/{month_str}/{safe_source}/{doc_folder}/"
            
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
                 # Single file upload
                 # Even for single file, we store it inside the doc_folder structure.
                 
                 # If we want to treat even single files as "folder" content type because of structure:
                 # obj.content_type = "folder"
                 # obj.original_filename = files[0].name 
                 
                 # But standard logic for single file usually keeps original content type.
                 # Let's keep existing logic but ensure storage_key logic is consistent.
                 
                 if path_data and '/' in path_data[0].get('path', ''):
                      obj.content_type = "folder"
                      obj.original_filename = path_data[0].get('path').split('/')[0]
                 else:
                      obj.content_type = getattr(files[0], "content_type", "application/octet-stream")
                      obj.original_filename = files[0].name
                      
                 # IMPORTANT: For single files, we must set storage_key to the full object key,
                 # NOT just the prefix, otherwise document_open (presigned url) fails.
                 if obj.content_type != "folder":
                      # Re-construct key for the single file (loop ran once)
                      # Relies on 'key' variable from loop being available?
                      # Yes, python loop variables leak scope. But robust way matches loop logic.
                      
                      # Simplest way: use the last 'key' calculated 
                      # (since len(files)==1 for this branch effectively)
                      # Or re-calculate:
                      rel_path = files[0].name
                      if path_data: # Should check use_index logic but here implies single
                           # Fallback simple logic
                           rel_path = path_data[0].get('path', rel_path)
                      
                      rel_path = rel_path.lstrip('/')
                      obj.storage_key = prefix + rel_path
            
            obj.size_bytes = total_size
            
            obj.size_bytes = total_size

        super().save_model(request, obj, form, change)

