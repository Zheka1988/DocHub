from django.contrib import admin
from django.contrib.admin import RelatedOnlyFieldListFilter
from rangefilter.filters import DateRangeFilter
from django.urls import reverse
from django.utils.html import format_html
from correspondence.models import IncomingDocument, OutgoingDocument
import re
from documents.forms import DocumentAdminForm
from documents.mixins import MinioUploadMixin


# Register your models here.
@admin.register(IncomingDocument)
class IncomingDocumentAdmin(MinioUploadMixin, admin.ModelAdmin):
    """Входящие доокументы"""
    form = DocumentAdminForm
    list_display = ("title", "source", "reg_number",
                    "reg_date", "due_date", "is_completed",
                    "executor", "open_file"
    )
    readonly_fields = ("storage_key", "original_filename", "content_type", "size_bytes")
    autocomplete_fields = ["source", "executor"]
    search_fields = ("title", "reg_number")
    search_help_text = 'Поиск по названию и номеру'
    list_filter = ["source", ("reg_date", DateRangeFilter), ("due_date", DateRangeFilter),
                   "is_completed", ("executor", RelatedOnlyFieldListFilter)]

    def open_file(self, obj):
        if not obj.storage_key:
            return "—"
        url = reverse("incoming_document_open", args=[obj.pk])
        label = "Скачать ZIP" if obj.content_type == "folder" else "Открыть"
        return format_html('<a href="{}" target="_blank">{}</a>', url, label)

    open_file.short_description = "Файл"

    def get_minio_prefix(self, obj):
        year_str = obj.reg_date.strftime("%Y")
        executor_name = obj.executor.get_full_name() or obj.executor.username
        safe_executor = re.sub(r'[\\/*?:"<>|]', '_', executor_name.strip())

        source_name = obj.source.title if obj.source else "unknown"
        safe_source = re.sub(r'[\\/*?:"<>|]', '_', source_name.strip())

        doc_name = f"{obj.title} - {obj.reg_number}"
        safe_doc_name = re.sub(r'[\\/*?:"<>|]', '_', doc_name.strip())

        return f"Корреспонденция/Входящие/{year_str}/{safe_executor}/{safe_source}/{safe_doc_name}"


@admin.register(OutgoingDocument)
class OutgoingDocumentAdmin(MinioUploadMixin, admin.ModelAdmin):
    """Исходящие доокументы"""
    form = DocumentAdminForm
    readonly_fields = ("storage_key", "original_filename", "content_type", "size_bytes")
    list_display = ("title", "reg_number", "reg_date", "note", "incoming", "realization", "open_file")
    search_fields = ("reg_number", "note")
    search_help_text = 'Поиск по номеру и примечанию'
    list_filter = [("reg_date", DateRangeFilter), ("realization", RelatedOnlyFieldListFilter)]
    autocomplete_fields = ["incoming", "realization"]

    def open_file(self, obj):
        if not obj.storage_key:
            return "—"
        url = reverse("outgoing_document_open", args=[obj.pk])
        label = "Скачать ZIP" if obj.content_type == "folder" else "Открыть"
        return format_html('<a href="{}" target="_blank">{}</a>', url, label)

    open_file.short_description = "Файл"

    def get_minio_prefix(self, obj):
        year_str = obj.reg_date.strftime("%Y")

        doc_name = f"{obj.reg_number} - {obj.reg_date}"
        safe_doc_name = re.sub(r'[\\/*?:"<>|]', '_', doc_name.strip())
        return f"Корреспонденция/Исходящие/{year_str}/{safe_doc_name}"
