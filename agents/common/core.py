from enum import Enum

class Suitability(str, Enum):
    ADEQUATE = 'adequate'
    INADEQUATE = 'inadequate'
    PROBABLY_INADEQUATE = 'probably_inadequate'
    UNKNOWN = 'unknown'

