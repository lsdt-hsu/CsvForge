from enum import Enum, auto, unique

@unique
class TaskStatus(Enum):
    FINISHED = auto()
    ERROR = auto()
    CANCELLED = auto()
