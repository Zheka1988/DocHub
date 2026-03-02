from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models, transaction
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver

from users.models import Department
from django_countries.fields import CountryField


from DocHub import settings


class Source(models.Model):
    """Источник"""
    title = models.CharField(
        verbose_name="Название источника",
        max_length=256
    )
    description = models.TextField(
        verbose_name="Описание источника",
        null=True,
        blank=True
    )
    created_at = models.DateField(
        verbose_name="Дата фиксации источника",
        auto_now_add=True,
    )
    updated_at = models.DateField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )
    year = models.SmallIntegerField(
        verbose_name="Год",
        default=2026
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Источник"
        verbose_name_plural = "Источники"
        unique_together = (("title", "year"),)


class ExternalDepartment(models.Model):
    """Ведомство"""
    title = models.CharField(
        verbose_name="Название",
        max_length=256
    )
    description = models.TextField(
        verbose_name="Описание ведомства",
        null=True,
        blank=True
    )
    year = models.SmallIntegerField(
        verbose_name="Год",
        default=2026
    )
    created_at = models.DateField(
        verbose_name="Дата внесения ведомства в базу",
        auto_now_add=True,
    )
    updated_at = models.DateField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Ведомство"
        verbose_name_plural = "Ведомства"
        unique_together = (("title", "year"),)


class Task(models.Model):
    """Задача"""
    title = models.CharField(
        verbose_name="Задача",
        max_length=256
    )
    description = models.TextField(
        verbose_name="Описание",
        blank=True,
        null=True
    )
    is_closed = models.BooleanField(
        verbose_name="Задача закрыта",
        default=False,
    )
    created_at = models.DateTimeField(
        verbose_name="Дата создания задачи",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )
    year = models.SmallIntegerField(
        verbose_name="Год",
        default=2026
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"
        constraints = [
            models.UniqueConstraint(
                fields=["title", "created_at"],
                name="uniq_task_title_per_day"
            )
        ]


class Country(models.Model):
    """Страна"""
    encoding = models.CharField(
        verbose_name="Кодировка",
        max_length=50,
    )
    title = CountryField(
        verbose_name="Название страны",
        max_length=2
    )
    created_at = models.DateField(
        verbose_name="Дата создания страны",
        auto_now_add=True,
    )
    updated_at = models.DateField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )
    year = models.PositiveSmallIntegerField(
        verbose_name="Год создания",
        default=2026
    )

    def __str__(self):
        return f"{self.title.code} - {self.encoding}"

    class Meta:
        verbose_name = "Страна"
        verbose_name_plural = "Страны"
        constraints = [
            models.UniqueConstraint(
                fields=['title', 'encoding', 'year'],
                name='unique_country_encoding_year'
            )
        ]


class SubTask(models.Model):
    """Подзадача"""
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="subtasks",
        verbose_name="Задача",
    )
    title = models.TextField(
        verbose_name="Подзадача",
    )
    is_closed = models.BooleanField(
        verbose_name="Подзадача закрыта",
        default=False,
    )
    created_at = models.DateTimeField(
        verbose_name="Дата создания подзадачи",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )

    def __str__(self):
        return f"{self.task}: {self.title}"

    class Meta:
        verbose_name = "Подзадача"
        verbose_name_plural = "Подзадачи"
        unique_together = ("task", "title")


class Direction(models.Model):
    """Направление С-Ю-З-В"""
    title = models.CharField(
        verbose_name="Название"
    )
    year = models.SmallIntegerField(
        verbose_name="Год",
        default=2026
    )
    description = models.TextField(
        verbose_name="Описание направления",
        blank=True,
        null=True
    )
    created_at = models.DateTimeField(
        verbose_name="Дата создания направления",
        auto_now_add=True,
    )
    updated_at = models.DateTimeField(
        verbose_name="Дата последнего изменения",
        auto_now=True,
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Направление"
        verbose_name_plural = "Направления"
        unique_together = (("title", "year"),)


class Document(models.Model):
    """Документ"""
    title = models.CharField(
        verbose_name="Наименование справки",
        max_length=256
    )
    number = models.CharField(
        verbose_name="Вх. № справки",
        max_length=24,
        unique=True
    )
    date = models.DateField(
        verbose_name="Дата",
    )
    realization = models.ForeignKey(
        ExternalDepartment,
        on_delete=models.PROTECT,
        related_name='documents',
        verbose_name="Реализация",
        max_length=256
    )
    countries = models.ManyToManyField(
        Country,
        related_name='documents',
        verbose_name="Страны"
    )
    grade = models.IntegerField(
        verbose_name="Оценка",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Исполнитель",
        on_delete=models.PROTECT,
        related_name="documents",
    )
    department = models.ForeignKey(
        "users.Department",
        verbose_name="Управление",
        on_delete=models.PROTECT,
        related_name="documents",
        help_text="Управление, добывшее (предоставившее) документ"
    )
    source = models.ForeignKey(
        Source,
        verbose_name="Источник",
        on_delete=models.PROTECT,
        related_name="documents",
    )
    direction = models.ForeignKey(
        Direction,
        verbose_name="Направление",
        on_delete=models.PROTECT,
        related_name="documents",
    )
    tasks = models.ManyToManyField(Task, through="DocumentTask", related_name="documents", blank=True)

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

    def __str__(self):
        d = self.date.strftime("%d.%m.%Y") if self.date else "—"
        return f"{self.number}: {d}"

    class Meta:
        verbose_name = "Документ"
        verbose_name_plural = "Документы"


class DocumentTask(models.Model):
    document = models.ForeignKey(
        "Document",
        verbose_name="Документ",
        on_delete=models.CASCADE,
        related_name="document_tasks")
    task = models.ForeignKey(
        "Task",
        verbose_name="Задача",
        on_delete=models.PROTECT,
        related_name="document_tasks")

    # если True — документ закрывает задачу полностью (все подзадачи)
    closes_task_fully = models.BooleanField(
        verbose_name="Задача закрыта",
        default=False
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self._update_closure_status()

    def _update_closure_status(self):
        all_count = self.task.subtasks.count()
        covered_count = self.covered_subtasks.count()

        should_be_fully = (covered_count == all_count and all_count > 0)

        # Обновляем closes_task_fully без рекурсии
        if self.closes_task_fully != should_be_fully:
            DocumentTask.objects.filter(pk=self.pk).update(closes_task_fully=should_be_fully)
            self.closes_task_fully = should_be_fully  # синхронизируем объект в памяти

        if self.closes_task_fully:
            # Закрываем задачу и подзадачи
            self.task.is_closed = True
            self.task.save(update_fields=['is_closed'])  # ← здесь save на другой модели — ок

            SubTask.objects.filter(task=self.task, is_closed=False).update(is_closed=True)

            # Создаём недостающие связи (без рекурсии)
            existing_ids = set(self.covered_subtasks.values_list('subtask_id', flat=True))
            missing = self.task.subtasks.exclude(id__in=existing_ids)
            if missing.exists():
                with transaction.atomic():
                    DocumentSubTask.objects.bulk_create(
                        [DocumentSubTask(document_task=self, subtask=st) for st in missing],
                        ignore_conflicts=True
                    )

    class Meta:
        verbose_name = "Задача (документы)"
        verbose_name_plural = "Задачи (документы)"
        unique_together = ("document", "task")
        indexes = [
            models.Index(fields=["task"]),
            models.Index(fields=["document"]),
        ]


class DocumentSubTask(models.Model):
    document_task = models.ForeignKey(
        DocumentTask,
        verbose_name="Задача",
        on_delete=models.CASCADE,
        related_name="covered_subtasks"
    )
    subtask = models.ForeignKey(
        SubTask,
        verbose_name="Подзадача",
        on_delete=models.PROTECT
    )

    def save(self, *args, **kwargs):
        self.full_clean()
        instance = super().save(*args, **kwargs)
        
        SubTask.objects.filter(pk=self.subtask_id, is_closed=False).update(is_closed=True)
        task_id = self.subtask.task_id
        if not SubTask.objects.filter(task_id=task_id, is_closed=False).exists():
            Task.objects.filter(pk=task_id, is_closed=False).update(is_closed=True)

        return instance

    def clean(self):
        if self.document_task_id and self.subtask_id:
            if self.subtask.task_id != self.document_task.task_id:
                raise ValidationError({"subtask": "Подзадача не относится к выбранной задаче."})

    class Meta:
        verbose_name = "Подзадача (документы)"
        verbose_name_plural = "Подзадачи (документы)"
        unique_together = ("document_task", "subtask")


@receiver(post_save, sender=DocumentSubTask)
@receiver(post_delete, sender=DocumentSubTask)
def sync_document_task(sender, instance, **kwargs):
    if instance.document_task_id:
        dt = instance.document_task
        dt._update_closure_status()


class ExternalDepartmentRef(ExternalDepartment):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Ведомство"
        verbose_name_plural = "Ведомства"


class TaskRef(Task):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Задача"
        verbose_name_plural = "Задачи"


class SubtaskRef(SubTask):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Подзадача"
        verbose_name_plural = "Подзадачи"


class SourceRef(Source):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Источник"
        verbose_name_plural = "Источники"


class CountryRef(Country):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Страна"
        verbose_name_plural = "Страны"


class DirectionRef(Direction):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Направление"
        verbose_name_plural = "Направления"
