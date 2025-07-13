import os
from enum import Enum
from typing import Optional
from typing import List, Tuple
from Models.FileType import FileType

class File:
    def __init__(self, file_id: str, type: FileType, path: str):
        self.file_id = file_id
        self.type = type
        self.path = path

    def __repr__(self):
        return f"File(file_id='{self.file_id}', file_Type={self.type}, path='{self.path}')"
    



class PageRange:
    def __init__(self, start: int, end: int):
        """
        Initialize a PageRange object.

        Parameters:
        - start (int): The starting page number.
        - end (int): The ending page number.
        """
        self.start = start
        self.end = end

    def __repr__(self):
        return f"PageRange(start={self.start}, end={self.end})"

# Example usage:



class FileRange:
    def __init__(self, file_id: str, pageRanges: List[PageRange]):
        """
        Initialize a FileRange object.

        Parameters:
        - file_id (str): The ID of the file.
        - pageRanges (List[PageRange]): A list of PageRange objects.
        """
        self.file_id = file_id
        self.pageRanges = pageRanges

    def __repr__(self):
        return f"FileRange(file_id='{self.file_id}', pageRanges={self.pageRanges})"