from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404, FileResponse
from django.shortcuts import get_object_or_404, redirect
import zipfile
import tempfile

from .models import Document
from .minio_client import get_minio_client


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
            
            filename = doc.original_filename or "archive"
            if not filename.endswith('.zip'):
                filename += '.zip'
                
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
