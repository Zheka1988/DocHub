from django.db import models
from DocHub import settings
from documents.models import ExternalDepartment


class MinioSave(models.Model):
    """Класс спец. полей для хранения документов в Minio"""
    storage_key = models.CharField(
        "MinIO object key",
        max_length=1024,
        blank=True)
    original_filename = models.CharField(
        "Имя файла",
        max_length=255,
        blank=True
    )
    content_type = models.CharField(
        "MIME тип",
        max_length=100,
        blank=True
    )
    size_bytes = models.BigIntegerField(
        "Размер (байт)",
        null=True,
        blank=True
    )

    class Meta:
        abstract = True


class IncomingDocument(MinioSave):
    """Входящие документы"""
    source = models.ForeignKey(
        ExternalDepartment,
        on_delete=models.PROTECT,
        verbose_name="Откуда поступил",
        related_name='incoming_documents'
    )
    title = models.CharField(
        verbose_name="Наименование документа",
        max_length=255
    )
    reg_number = models.CharField(
        verbose_name="Регистрационный номер",
        max_length=50,
        unique=True
    )
    reg_date = models.DateField(
        verbose_name="Дата регистрации"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    due_date = models.DateField(
        verbose_name="Срок исполнения",
        null=True,
        blank=True
    )
    is_completed = models.BooleanField(
        verbose_name="Отметка об исполнении",
        default=False
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        verbose_name="Ответственный исполнитель"
    )

    class Meta:
        verbose_name = "Входящий документ"
        verbose_name_plural = "Входящие документы"
        ordering = ['-reg_date']

    def __str__(self):
        return f"{self.title} - {self.reg_number}"


class OutgoingDocument(MinioSave):
    """Исходящие документы"""
    title = models.CharField(
        verbose_name="Наименование документа",
        max_length=255
    )
    incoming = models.ForeignKey(
        IncomingDocument,
        on_delete=models.PROTECT,
        related_name='outgoing_documents',
        verbose_name="Основание (входящий документ)",
        null=True,
        blank=True
    )
    reg_number = models.CharField(
        verbose_name="Регистрационный номер исходящего",
        max_length=50,
        unique=True
    )
    reg_date = models.DateField(
        verbose_name="Дата исполнения"
    )
    realization = models.ForeignKey(
        ExternalDepartment,
        on_delete=models.PROTECT,
        verbose_name="Куда реализован",
        related_name='realized_outgoing_documents'
    )
    note = models.TextField(
        verbose_name="Примечание",
        blank=True
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Исходящий документ"
        verbose_name_plural = "Исходящие документы"
        ordering = ['-reg_date']

    def __str__(self):
        return f"{self.reg_number}"

    def save(self, *args, **kwargs):
        incoming = self.incoming
        super().save(*args, **kwargs)
        if incoming and not incoming.is_completed:
            if not incoming.outgoing_documents.exclude(pk=self.pk).exists():
                incoming.is_completed = True
                incoming.save(update_fields=['is_completed'])

    def delete(self, *args, **kwargs):
        incoming = self.incoming
        if incoming and incoming.is_completed:
            other_outgoings = incoming.outgoing_documents.exclude(pk=self.pk)
            if not other_outgoings.exists():
                incoming.is_completed = False
                incoming.save(update_fields=['is_completed'])
        super().delete(*args, **kwargs)