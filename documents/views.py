from datetime import timedelta

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect

from .models import Document
from .minio_client import get_minio_client


@login_required
def document_open(request, pk: int):
    doc = get_object_or_404(Document, pk=pk)

    if not doc.storage_key:
        raise Http404("Файл не найден")

    client = get_minio_client()

    url = client.presigned_get_object(
        settings.MINIO_BUCKET,
        doc.storage_key,
        expires=timedelta(hours=1),  # ссылка жива 1 час
    )

    return redirect(url)
