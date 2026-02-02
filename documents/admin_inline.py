from django.contrib import admin
from .models import DocumentTask, DocumentSubTask, SubTask
from .forms import DocumentSubTaskForm
import nested_admin


class DocumentSubTaskInline(nested_admin.NestedTabularInline):
    model = DocumentSubTask
    form = DocumentSubTaskForm
    extra = 1

    def formfield_for_foreignkey(self, db_field, request, **kwargs):
        """
        Ограничиваем выбор subtask только подзадачами нужной task.
        DocumentTask редактируется как /admin/documents/documenttask/<id>/change/
        """
        if db_field.name == "subtask":
            obj_id = request.resolver_match.kwargs.get("object_id")
            if obj_id:
                try:
                    dt = DocumentTask.objects.get(pk=obj_id)
                    kwargs["queryset"] = SubTask.objects.filter(task=dt.task).order_by("title")
                except DocumentTask.DoesNotExist:
                    pass
        return super().formfield_for_foreignkey(db_field, request, **kwargs)


class DocumentTaskInline(nested_admin.NestedTabularInline):
    model = DocumentTask
    extra = 1
    autocomplete_fields = ("task",)
    fields = ("task", "closes_task_fully")
    show_change_link = True
    inlines = (DocumentSubTaskInline,)
