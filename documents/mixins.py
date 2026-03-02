import re
import logging
from django.conf import settings

from documents.minio_client import get_minio_client


class MinioUploadMixin:
    """Mixin для загрузки файлов в MinIO с общей логикой"""

    def get_minio_prefix(self, obj):
        """
        Переопределяется в каждой админке.
        Возвращает префикс пути (без финального слеша).
        """
        raise NotImplementedError("Переопределите get_minio_prefix в дочернем классе")

    def upload_to_minio(self, request, obj, files):
        """Общая логика загрузки файлов и обновления метаданных"""
        client = get_minio_client()

        if not client.bucket_exists(settings.MINIO_BUCKET):
            client.make_bucket(settings.MINIO_BUCKET)

        prefix = self.get_minio_prefix(obj).rstrip('/') + '/'
        total_size = 0
        logger = logging.getLogger(__name__)

        for uploaded_file in files:
            rel_path = uploaded_file.name.lstrip('/')
            key = prefix + rel_path

            content_type = getattr(uploaded_file, "content_type", None) or "application/octet-stream"

            try:
                client.put_object(
                    bucket_name=settings.MINIO_BUCKET,
                    object_name=key,
                    data=uploaded_file.file,
                    length=uploaded_file.size,
                    content_type=content_type,
                )
                total_size += uploaded_file.size
                logger.info(f"Uploaded: {key} ({uploaded_file.size} bytes)")
            except Exception as e:
                logger.error(f"MinIO upload failed for {key}: {e}")

        # Общие метаданные
        obj.size_bytes = total_size
        obj.storage_key = prefix  # по умолчанию — путь к папке

        # Для одного файла — точный путь к файлу
        if len(files) == 1:
            obj.storage_key = prefix + files[0].name.lstrip('/')
            obj.content_type = getattr(files[0], "content_type", "application/octet-stream")
            obj.original_filename = files[0].name
        else:
            obj.content_type = "folder"
            obj.original_filename = prefix.split('/')[-2]  # имя последней папки (doc_name)

    def save_model(self, request, obj, form, change):
        files = request.FILES.getlist('file')
        if files:
            self.upload_to_minio(request, obj, files)

        super().save_model(request, obj, form, change)