from enum import Enum


class AIStatus(int, Enum):
    PENDING = 1
    PROCESSING = 2
    FINISHED = 3
    ERROR = 4
    SUSPENDED = 5