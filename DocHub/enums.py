from enum import Enum


class BaseEnum(Enum):
    @classmethod
    def choices(cls):
        return [(constant.name, constant.value) for constant in cls]