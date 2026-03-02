from django.db import models
from django.contrib.auth.models import AbstractUser
from .enums import Rank, Role, Departments
from .validators import phone_validator


class Department(models.Model):
    """Модель управлений"""

    title = models.CharField(
        verbose_name='Управление',
        max_length=25,
    )

    def __str__(self):
        return self.title

    class Meta:
        verbose_name = "Управление"
        verbose_name_plural = "Управления"
        constraints = [
            models.UniqueConstraint(
                fields=["title"],
                name="uniq_department_title",
                violation_error_message="Такое управление уже есть в системе."
            )
        ]

class User(AbstractUser):
    """Модель расширяющая, пользователя по умолчанию"""

    role = models.CharField(
        verbose_name="Роль",
        max_length=32,
        choices=Role.choices(),
        default=Role.USER.name,
    )
    rank = models.CharField(
        verbose_name='Воинское звание',
        max_length=64,
        choices=Rank.choices(),
        default=Rank.ENLISTED.name,
    )
    middle_name = models.CharField(
        max_length=128,
        verbose_name="Отчество",
        blank=True
    )
    department = models.ForeignKey(
        Department,
        on_delete=models.PROTECT,
        verbose_name="Управление",
        related_name="users",
        null=True,
        blank=True,
    )
    birth_date = models.DateField(
        verbose_name="Дата рождения",
        null=True,
        blank=True
    )
    work_phone = models.CharField(
        max_length=15,
        verbose_name="Рабочий телефон",
        validators=[phone_validator],
        null=True,
        blank=True
    )

    def __str__(self):
        full = self.get_full_name().strip()
        return full or self.username

    class Meta:
        verbose_name = 'Пользователь'
        verbose_name_plural = 'Пользователи'
