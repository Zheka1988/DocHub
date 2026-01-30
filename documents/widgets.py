
import json
from django import forms
from django.contrib.admin.widgets import AdminFileWidget
from django.utils.safestring import mark_safe

class FolderUploadWidget(AdminFileWidget):
    allow_multiple_selected = True

    def __init__(self, attrs=None):
        default_attrs = {
            "multiple": "multiple",
            "webkitdirectory": "",
            "directory": "",
        }
        if attrs:
            default_attrs.update(attrs)
        if attrs:
            default_attrs.update(attrs)
        super().__init__(default_attrs)

    def value_from_datadict(self, data, files, name):
        val = super().value_from_datadict(data, files, name)
        return val

    def render(self, name, value, attrs=None, renderer=None):
        # AdminFileWidget expects attrs id to be present usually
        if attrs is None:
            attrs = {}
            
        # Ensure regex attributes are there
        attrs['multiple'] = 'multiple'
        attrs['webkitdirectory'] = ''
        attrs['directory'] = ''
        
        output = super().render(name, value, attrs, renderer)
        
        # Depending on AdminFileWidget implementation, id might be in attrs or not
        # We need a robust way to find the input. 
        # But usually attrs['id'] is available here.
        input_id = attrs.get('id', f'id_{name}')
        paths_input_id = f"{input_id}_paths"
        
        script = f"""
        <input type="hidden" name="file_paths" id="{paths_input_id}">
        <script>
            document.addEventListener('DOMContentLoaded', function() {{
                const fileInput = document.getElementById('{input_id}');
                const pathsInput = document.getElementById('{paths_input_id}');
                
                if (fileInput) {{
                    fileInput.setAttribute('webkitdirectory', '');
                    fileInput.setAttribute('directory', '');
                    fileInput.setAttribute('multiple', 'multiple');
                    
                    fileInput.addEventListener('change', function(e) {{
                        const files = e.target.files;
                        const fileList = [];
                        for (let i = 0; i < files.length; i++) {{
                            fileList.push({{
                                'name': files[i].name,
                                'path': files[i].webkitRelativePath
                            }});
                        }}
                        pathsInput.value = JSON.stringify(fileList);
                    }});
                }} else {{
            }});
        </script>
        """
        return mark_safe(output + script)
