from django import forms
from .models import Document


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True

class DocumentAdminForm(forms.ModelForm):
    # file = forms.FileField(required=False, label="Файл (загрузить в MinIO)")
    file = forms.FileField(
        label="Файлы/папка (загрузить в MinIO)",
        required=False,
        widget=MultipleFileInput(attrs={"multiple": True, "webkitdirectory": True}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # обязателен только при создании
        if self.instance.pk is None:
            self.fields["file"].required = True

    class Meta:
        model = Document
        fields = "__all__"
