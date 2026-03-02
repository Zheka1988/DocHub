from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from .models import IncomingDocument, OutgoingDocument
from django.http import Http404, FileResponse
from documents.minio_client import get_minio_client
from django.conf import settings
import zipfile
import tempfile
import re
from datetime import timedelta


@login_required
def incoming_document_open(request, pk: int):
    doc = get_object_or_404(IncomingDocument, pk=pk)

    if not doc.storage_key:
        raise Http404("Файл не найден")

    client = get_minio_client()

    if doc.content_type == "folder":
        try:
            # Префикс из storage_key (заканчивается слешем)
            prefix = doc.storage_key.rstrip('/') + '/'

            # Получаем все объекты в папке
            objects = client.list_objects(
                settings.MINIO_BUCKET,
                prefix=prefix,
                recursive=True
            )

            # Временный файл для ZIP
            tmp = tempfile.TemporaryFile()

            has_files = False
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for obj in objects:
                    has_files = True
                    # Относительный путь внутри архива (убираем префикс)
                    rel_name = obj.object_name[len(prefix):]

                    # Скачиваем файл из MinIO
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

            # Имя архива: reg_number - reg_date.zip
            date_str = doc.reg_date.strftime("%Y.%m.%d")
            number_str = str(doc.reg_number)
            safe_number = re.sub(r'[\\/*?:"<>|]', '-', number_str)

            filename = f"{safe_number}-{date_str}.zip"

            return FileResponse(tmp, as_attachment=True, filename=filename)

        except Exception as e:
            print(f"Zip generation error for IncomingDocument {pk}: {e}")
            raise Http404("Ошибка при формировании архива")

    # Для одиночного файла — presigned URL
    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        doc.storage_key,
        expires=timedelta(hours=1)
    )

    return redirect(url)


@login_required
def outgoing_document_open(request, pk: int):
    doc = get_object_or_404(OutgoingDocument, pk=pk)

    if not doc.storage_key:
        raise Http404("Файл не найден")

    client = get_minio_client()

    if doc.content_type == "folder":
        try:
            # Префикс из storage_key (заканчивается слешем)
            prefix = doc.storage_key.rstrip('/') + '/'

            # Получаем все объекты в папке
            objects = client.list_objects(
                settings.MINIO_BUCKET,
                prefix=prefix,
                recursive=True
            )

            # Временный файл для ZIP
            tmp = tempfile.TemporaryFile()

            has_files = False
            with zipfile.ZipFile(tmp, 'w', zipfile.ZIP_DEFLATED) as archive:
                for obj in objects:
                    has_files = True
                    # Относительный путь внутри архива
                    rel_name = obj.object_name[len(prefix):]

                    # Скачиваем файл из MinIO
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

            # Имя архива: reg_number - reg_date.zip
            date_str = doc.reg_date.strftime("%Y.%m.%d")
            number_str = str(doc.reg_number)
            safe_number = re.sub(r'[\\/*?:"<>|]', '-', number_str)

            filename = f"{safe_number}-{date_str}.zip"

            return FileResponse(tmp, as_attachment=True, filename=filename)

        except Exception as e:
            print(f"Zip generation error for OutgoingDocument {pk}: {e}")
            raise Http404("Ошибка при формировании архива")

    # Для одиночного файла — presigned URL
    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        doc.storage_key,
        expires=timedelta(hours=1)
    )

    return redirect(url)
