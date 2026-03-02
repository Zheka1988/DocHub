import re
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html
from .mixins import MinioUploadMixin
from .models import Document, Task, SubTask, Source, ExternalDepartment, DocumentTask, DocumentSubTask, \
    ExternalDepartmentRef, TaskRef, \
    SubtaskRef, SourceRef, CountryRef, DirectionRef, Direction, Country
from .forms import DocumentAdminForm
from rangefilter.filters import DateRangeFilter
from .admin_inline import DocumentTaskInline, DocumentSubTaskInline
import nested_admin
from django.contrib.admin import RelatedOnlyFieldListFilter


# ---------Справочники----------------------------------------
@admin.register(ExternalDepartment)
class ExternalDepartmentAdmin(admin.ModelAdmin):
    """Ведомство"""
    search_fields = ["title", "description"]
    search_help_text = 'Поиск по названию и описанию'
    list_display = ("title", "description", "year")
    list_filter = ("year",)

    def get_model_perms(self, request):
        return {}


@admin.register(ExternalDepartmentRef)
class ExternalDepartmentRefAdmin(admin.ModelAdmin):
    search_fields = ["title", "description"]
    search_help_text = 'Поиск по названию и описанию'
    list_display = ("title", "description", "year")
    list_filter = ("year",)


@admin.register(Source)
class SourceAdmin(admin.ModelAdmin):
    """Источник"""
    search_fields = ["title", "description"]
    search_help_text = 'Поиск по названию и описанию'
    list_display = ("title", "description", "year")
    list_filter = ("year",)

    def get_model_perms(self, request):
        return {}


@admin.register(SourceRef)
class SourceRefAdmin(admin.ModelAdmin):
    search_fields = ("title", "description")
    search_help_text = 'Поиск по названию и описанию'
    list_display = ("title", "description", "year")
    list_filter = ("year",)


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    """Задача"""
    search_fields = ["title", "description"]
    search_help_text = 'Поиск по названию задачи и описанию'
    list_display = ("title", "description", "is_closed", "year")
    list_filter = ("is_closed", "year")

    def get_model_perms(self, request):
        return {}


@admin.register(TaskRef)
class TaskRefAdmin(admin.ModelAdmin):
    search_fields = ("title", "description")
    search_help_text = 'Поиск по названию задачи и описанию'
    list_display = ("title", "description", "is_closed", "year")
    list_filter = ("is_closed", "year")


@admin.register(SubTask)
class SubTaskAdmin(admin.ModelAdmin):
    """Подзадача"""
    list_display = ("title", "task", "is_closed",)
    list_filter = ("task__title", "is_closed",)
    search_fields = ["title", "task__title"]
    search_help_text = 'Поиск по названию подзадачи и задачи'
    autocomplete_fields = ["task",]

    def get_model_perms(self, request):
        return {}


@admin.register(SubtaskRef)
class SubtaskRefAdmin(admin.ModelAdmin):
    list_display = ("title", "task", "is_closed")
    list_filter = ("task__title", "is_closed")
    search_fields = ("title", "task__title")
    search_help_text = 'Поиск по названию подзадачи и задачи'
    autocomplete_fields = ["task",]


@admin.register(Direction)
class DirectionAdmin(admin.ModelAdmin):
    search_fields = ["title",]
    search_help_text = 'Поиск по названию'
    list_display = ("title", "year",)
    list_filter = ("year",)

    def get_model_perms(self, request):
        return {}


@admin.register(DirectionRef)
class DirectionRefAdmin(admin.ModelAdmin):
    search_fields = ("title",)
    list_display = ("title", "year",)
    search_help_text = 'Поиск по названию'
    list_filter = ("year",)


@admin.register(Country)
class CountryAdmin(admin.ModelAdmin):
    search_fields = ["title", "encoding"]
    list_display = ("title", "encoding", "year")
    list_filter = ("year",)
    search_help_text = 'Поиск по названию и кодировке'

    def get_model_perms(self, request):
        return {}


@admin.register(CountryRef)
class CountryRefAdmin(admin.ModelAdmin):
    search_fields = ("title", "encoding")
    list_display = ("title", "encoding", "year")
    search_help_text = 'Поиск по названию и кодировке'
    list_filter = ("year",)


# ----------------------------------------------------------------------------
@admin.register(DocumentTask)
class DocumentTaskAdmin(admin.ModelAdmin):
    """Задачи (документы)"""
    list_display = ("task", "document", )
    list_filter = ("task",)
    search_fields = ["document__number", "document__title", "task__title"]
    search_help_text = 'Поиск по номеру и названию документа или названию задачи'
    autocomplete_fields = ("document", "task")
    inlines = (DocumentSubTaskInline,)


@admin.register(DocumentSubTask)
class DocumentSubTaskAdmin(admin.ModelAdmin):
    """Подзадачи (документы)"""
    list_display = ("subtask", "get_task", "get_document")

    list_filter = ("document_task__task", )  # "document_task__document"
    search_fields = [
        "document_task__document__number",
        "document_task__document__title",
        "document_task__task__title",
        "subtask__title",
    ]
    search_help_text = 'Поиск по номеру и названию документа, названию задачи и подзадачи'
    autocomplete_fields = ("document_task", "subtask")

    @admin.display(description="Задача", ordering="document_task__task__title")
    def get_task(self, obj):
        return obj.document_task.task

    @admin.display(description="Документ", ordering="document_task__document__number")
    def get_document(self, obj):
        d = obj.document_task.document
        if not d:
            return "—"

        date_str = d.date.strftime("%d.%m.%Y") if d.date else "—"
        return f"{d.number}: {date_str}"


@admin.register(Document)
class DocumentAdmin(MinioUploadMixin, nested_admin.NestedModelAdmin):
    """Документ"""
    form = DocumentAdminForm
    readonly_fields = ("storage_key", "original_filename", "content_type", "size_bytes")
    search_fields = ["title", "number"]
    list_display = ["title", "number", "date", "department",  "get_countries",
                    "get_realization", "grade", "executor",
                    "source", "direction", "open_file",]

    list_filter = [("date", DateRangeFilter), "grade", ("executor", RelatedOnlyFieldListFilter),
                   ("source", RelatedOnlyFieldListFilter), ("direction", RelatedOnlyFieldListFilter),
                   ("realization", RelatedOnlyFieldListFilter), ("department", RelatedOnlyFieldListFilter),
                   ("document_tasks__task", RelatedOnlyFieldListFilter), ('countries', RelatedOnlyFieldListFilter)]
    search_help_text = 'Поиск по номеру и названию документа'
    inlines = (DocumentTaskInline,)
    autocomplete_fields = ["realization", "executor", "department", "realization", "source", "direction"]

    @admin.display(description="Реализация")
    def get_realization(self, obj):
        return obj.realization.title if obj.realization else "—"

    @admin.display(description="Страны")
    def get_countries(self, obj):
        return ", ".join([str(country) for country in obj.countries.all()])

    def open_file(self, obj):
        if not obj.storage_key:
            return "—"
        url = reverse("document_open", args=[obj.pk])
        label = "Скачать ZIP" if obj.content_type == "folder" else "Открыть"
        return format_html('<a href="{}" target="_blank">{}</a>', url, label)

    open_file.short_description = "Файл"

    def get_minio_prefix(self, obj):
        year_str = obj.date.strftime("%Y")
        month_str = obj.date.strftime("%m")
        date_str = obj.date.strftime("%Y.%m.%d")

        dept_title = obj.department.title
        safe_dept = re.sub(r'[\\/*?:"<>|]', '_', dept_title.strip())

        source_title = obj.source.title
        safe_source = re.sub(r'[\\/*?:"<>|]', '_', source_title.strip())

        number_str = str(obj.number)
        safe_number = re.sub(r'[\\/*?:"<>|]', '-', number_str.strip())

        doc_folder = f"{safe_number}-{date_str}"

        return f"Материалы/{year_str}/{safe_dept}/{month_str}/{safe_source}/{doc_folder}"