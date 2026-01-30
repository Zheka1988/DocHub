from DocHub.enums import BaseEnum


class Role(BaseEnum):
    """Названия ролей пользователя"""

    USER = "Пользователь"
    EDITOR = "Редактор"
    ADMIN = "Администратор"


class Rank(BaseEnum):
    """Звания"""

    ENLISTED = "Служащий"
    PRIVATE = "Рядовой"
    LANCE_CORPORAL = "Ефрейтор"
    JUNIOR_SERGEANT = "Младший сержант"
    SERGEANT = "Сержант"
    SEN_SERGEANT = "Старший сержант"
    SERGEANT_THIRD_CLASS = "Сержант 3 класса"
    SERGEANT_SECOND_CLASS = "Сержант 2 класса"
    SERGEANT_FIRST_CLASS = "Сержант 1 класса"
    STAFF_SERGEANT = "Штаб-сержант"
    MASTER_SERGEANT = "Мастер-сержант"

    LIEUTENANT = "Лейтенант"
    SENIOR_LIEUTENANT = "Старший лейтенант"
    CAPTAIN = "Капитан"
    MAJOR = "Майор"
    LIEUTENANT_COLONEL = "Подполковник"
    COLONEL = "Полковник"

    MAJOR_GENERAL = "Генерал-майор"
    LIEUTENANT_GENERAL = "Генерал-лейтенант"
    COLONEL_GENERAL = "Генерал-полковник"


class Departments(BaseEnum):
    """ Управления"""

    DEFAULT = "Выберите управление"
    ONE = "Первое управление"
    TWO = "Второе управление"
    THREE = "Третье управление"
    FOR = "Четвертое управление"
