from dataclasses import dataclass
from typing import List, Optional

@dataclass
class LoadedCSVData:
    all_rows: List[List[str]]
    delimiter: str
    encoding: str
    file_path: Optional[str] = None
