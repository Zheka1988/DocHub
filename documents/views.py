from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect
import zipfile
import tempfile
import re

from .models import Document
from .minio_client import get_minio_client
from django.apps import apps
from django.db.models import Q
from django.http import JsonResponse
from smart_selects.utils import (
    get_keywords,
    sort_results,
    serialize_results,
    get_queryset,
    get_limit_choices_to,
)

def do_filter(qs, keywords, exclude=False):
    """
    Filter queryset based on keywords.
    Support for multiple-selected parent values.
    """
    and_q = Q()
    for keyword, value in keywords.items():
        try:
            values = value.split(",")
            if len(values) > 0:
                or_q = Q()
                for value in values:
                    or_q |= Q(**{keyword: value})
                and_q &= or_q
        except AttributeError:
            # value can be a bool
            and_q &= Q(**{keyword: value})
    if exclude:
        qs = qs.exclude(and_q)
    else:
        qs = qs.filter(and_q)
    return qs

def chained_filter(request, app, model, field, foreign_key_app_name, foreign_key_model_name, foreign_key_field_name, value, manager=None):
    """
    Custom filterchain view to bypass smart_selects security check
    which requires the foreign model to have a ChainedForeignKey field.
    """
    model_class = apps.get_model(app, model)
    keywords = get_keywords(field, value, m2m=False)

    # SKIP SECURITY CHECK
    
    # filter queryset using limit_choices_to
    limit_choices_to = get_limit_choices_to(
        foreign_key_app_name, foreign_key_model_name, foreign_key_field_name
    )
    queryset = get_queryset(model_class, manager, limit_choices_to)

    results = do_filter(queryset, keywords)

    # Sort results if model doesn't include a default ordering.
    if not getattr(model_class._meta, "ordering", False):
        results = list(results)
        sort_results(results)

    serialized_results = serialize_results(results)
    return JsonResponse(serialized_results, safe=False)


@login_required
def document_open(request, pk: int):
    doc = get_object_or_404(Document, pk=pk)

    if not doc.storage_key:
        raise Http404("Файл не найден")

    client = get_minio_client()

    if doc.content_type == "folder":
        try:
            # Generate prefix
            prefix = doc.storage_key
            
            # List all objects
            objects = client.list_objects(settings.MINIO_BUCKET, prefix=prefix, recursive=True)
            
            # Create temp file
            tmp = tempfile.TemporaryFile()
            
            has_files = False
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for obj in objects:
                    has_files = True
                    # Calculate relative path in archive
                    # obj.object_name: dept/2026/01/uuid/Folder/file.txt
                    # prefix: dept/2026/01/uuid/
                    rel_name = obj.object_name[len(prefix):]
                    
                    # Fetch from MinIO
                    data = client.get_object(settings.MINIO_BUCKET, obj.object_name)
                    try:
                        file_content = data.read()
                    finally:
                        data.close()
                        data.release_conn()
                    
                    archive.writestr(rel_name, file_content)
            
            if not has_files:
                tmp.close()
                raise Http404("Папка пуста или удалена")
                
            tmp.seek(0)
            
            tmp.seek(0)
            
            # New filename logic: <number>-<YYYY.MM.DD>.zip
            date_str = doc.date.strftime("%Y.%m.%d")
            number_str = str(doc.number)
            
            # Simple sanitization (replace invalid with -)
            # Reusing the pattern from admin.py for consistency
            safe_number = re.sub(r'[\\/*?:"<>|]', '-', number_str)
            
            filename = f"{safe_number}-{date_str}.zip"
                
            return FileResponse(tmp, as_attachment=True, filename=filename)
            
        except Exception as e:
            # In a real app, log this
            print(f"Zip generation error: {e}")
            raise Http404("Ошибка при формировании архива")

    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        doc.storage_key,
        expires=timedelta(hours=1),  # ссылка жива 1 час
    )

    return redirect(url)
