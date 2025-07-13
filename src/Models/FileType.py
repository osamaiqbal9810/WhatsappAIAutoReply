from enum import Enum
from typing import Optional
from typing import List, Tuple
class FileType(Enum):
    PDF = ".pdf"          
    DOC = ".doc"          
    DOCX = ".docx"        
    TXT = ".txt"          
    EPUB = ".epub"        
    HTML = ".html"        
    MD = ".md"           
    ODP = ".odp"          
    ODT = ".odt"          
    ODS = ".ods"      
    PPT = ".ppt"          
    PPTX = ".pptx"        
    RTF = ".rtf"          
    MOBI = ".mobi"    
    XLSX = ".xlsx"  
    XLS = ".xls" 
    @staticmethod
    def is_valid_file_type(file_type_str: str) -> bool:
        """
        Check if a given file type string exists in the FileType enum.
        
        Args:
        file_type_str (str): The file type to check.

        Returns:
        bool: True if the file type exists in the FileType enum, False otherwise.
        """
        try:
            FileType(file_type_str)
            return True
        except ValueError:
            return False
