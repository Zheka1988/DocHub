from .models import DocumentTask, DocumentSubTask
import nested_admin
from django.forms.models import BaseInlineFormSet


class DocumentSubTaskInlineFormSet(BaseInlineFormSet):
    def clean(self):
        super().clean()

        for form in self.forms:
            if not hasattr(form, "cleaned_data"):
                continue
            if form.cleaned_data.get("DELETE"):
                continue

            subtask = form.cleaned_data.get("subtask")
            document_task = form.cleaned_data.get("document_task") or getattr(form.instance, "document_task", None)

            # document_task может быть ещё не полностью “связан” — поэтому аккуратно
            task = getattr(document_task, "task", None)

            if subtask and task and subtask.task_id != task.id:
                form.add_error("subtask", "Подзадача не относится к выбранной задаче.")


class DocumentSubTaskInline(nested_admin.NestedTabularInline):
    model = DocumentSubTask
    autocomplete_fields = ['subtask']
    extra = 0
    formset = DocumentSubTaskInlineFormSet


class DocumentTaskInline(nested_admin.NestedTabularInline):
    model = DocumentTask
    extra = 0
    autocomplete_fields = ("task",)
    fields = ("task", "closes_task_fully")
    show_change_link = True
    inlines = (DocumentSubTaskInline,)
