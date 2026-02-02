from django import forms
from .models import Document
from .widgets import FolderUploadWidget
from smart_selects.form_fields import ChainedModelChoiceField
from .models import Document, DocumentSubTask, SubTask, Task



class MultipleFileField(forms.FileField):
    def to_python(self, data):
        if not data:
            return None
        # Allow validation to pass even if it's a list
        if isinstance(data, list):
            return data
        return data

    def validate(self, value):
        if self.required and not value:
            raise forms.ValidationError(self.error_messages['required'], code='required')
        # Skip other validation for list of files for now, as standard val might fail
        pass


class DocumentAdminForm(forms.ModelForm):
    file = MultipleFileField(
        required=False, 
        label="Файл (загрузить в MinIO)",
        widget=FolderUploadWidget()
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Отключаем стандартную проверку, делаем её вручную в clean()
        self.fields["file"].required = False

    def clean(self):
        print(f"DEBUG: Form.files type: {type(self.files)}")
        files_list = self.files.getlist('file')
        print(f"DEBUG: Files count: {len(files_list)}")
        
        cleaned_data = super().clean()
        
        # Ручная проверка обязательности файла при создании
        if self.instance.pk is None and not files_list:
             self.add_error('file', "Файл (или папка) обязателен для загрузки.")
             
        # Т.к. мы используем request.FILES напрямую в save_model, 
        # нам не важно, что вернет cleaned_data['file'] (там будет только последний файл)
        
        return cleaned_data

    class Meta:
        model = Document
        fields = "__all__"

class DocumentSubTaskForm(forms.ModelForm):
    # Hidden field to store the task ID from the parent inline
    task_filter = forms.ModelChoiceField(
        queryset=Task.objects.all(),
        # Видимое поле с названием ФИЛЬТР, read-only
        label="ФИЛЬТР",
        widget=forms.TextInput(attrs={'readonly': 'readonly'}),
        required=False
    )
    
    subtask = ChainedModelChoiceField(
        to_app_name='documents',
        to_model_name='SubTask',
        chained_field='task_filter',
        chained_model_field='task',
        foreign_key_app_name='documents',
        foreign_key_model_name='Task',
        foreign_key_field_name='id',
        view_name='document_chained_filter',
        show_all=False,
        auto_choose=True,
        required=True,
        label="Подзадача"
    )

    class Meta:
        model = DocumentSubTask
        fields = "__all__"
