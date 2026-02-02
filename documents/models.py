from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from users.models import Department


from DocHub import settings


class Source(models.Model):
    """Источник"""
    title = models.CharField(
        verbose_name="Название источника",
        max_length=256
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Источник"
        verbose_name_plural = "Источники"


class Direction(models.Model):
    """Направление"""
    title = models.CharField(
        verbose_name="Направление",
        max_length=256
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Направление"
        verbose_name_plural = "Направления"


class Task(models.Model):
    """Задача"""
    title = models.CharField(
        verbose_name="Задача",
        max_length=256
    )
    description = models.TextField(
        verbose_name="Описание",
        blank=True,
        max_length=256
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
        max_length=512
    )
    is_closed = models.BooleanField(
        verbose_name="Подзадача закрыта",
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

    def __str__(self):
        return f"{self.task}: {self.title}"

    class Meta:
        verbose_name = "Подзадача"
        verbose_name_plural = "Подзадачи"
        unique_together = ("task", "title")


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
    realization = models.CharField(
        verbose_name="Реализация",
        max_length=256
    )
    grade = models.IntegerField(
        verbose_name="Оценка",
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    executor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        verbose_name="Исполнитель",
        on_delete=models.PROTECT,
        related_name="executed_documents",
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

        if self.closes_task_fully:
            Task.objects.filter(pk=self.task_id, is_closed=False).update(is_closed=True)
            SubTask.objects.filter(task_id=self.task_id, is_closed=False).update(is_closed=True)
            DocumentSubTask.objects.filter(document_task=self).delete()
            DocumentSubTask.objects.bulk_create(
                [DocumentSubTask(document_task=self, subtask=st) for st in self.task.subtasks.all()],
                ignore_conflicts=True,
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


class DirectionRef(Direction):
    class Meta:
        proxy = True
        app_label = "references"
        verbose_name = "Направление"
        verbose_name_plural = "Направления"


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
