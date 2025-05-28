from .lib import get, put
from .collection import DataCollection
from .piper import DictPiper
from .seeds import DROP, KEEP, ELIF, COALESCE, SPLIT, MERGE, FLATTEN, DEFAULT

# Alias for backward compatibility if needed
Piper = DictPiper

# Aliases for README compatibility
COAL = COALESCE
FLAT = FLATTEN

__all__ = [
    "get",
    "put", 
    "DataCollection",
    "DictPiper",
    "Piper",
    "DROP",
    "KEEP",
    "ELIF",
    "COALESCE",
    "COAL",
    "SPLIT",
    "MERGE",
    "FLATTEN",
    "FLAT",
    "DEFAULT",
]