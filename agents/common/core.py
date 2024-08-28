from enum import Enum

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    UNKNOWN = 'unknown'

