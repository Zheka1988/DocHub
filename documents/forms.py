from django import forms
from .models import Document
from .widgets import FolderUploadWidget



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
