from enum import Enum, unique

@unique
class TaskStatus(Enum):
    FINISHED = "finished"
    ERROR = "error"
    CANCELLED = "cancelled"
