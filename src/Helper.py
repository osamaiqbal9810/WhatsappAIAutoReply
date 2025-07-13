import os
from Models.FileType import FileType
from typing import List, Tuple
import re
from langchain_community.document_loaders import PyMuPDFLoader, UnstructuredWordDocumentLoader, TextLoader, UnstructuredEPubLoader, UnstructuredHTMLLoader, UnstructuredMarkdownLoader, UnstructuredODTLoader, UnstructuredPowerPointLoader, UnstructuredRTFLoader, UnstructuredExcelLoader
from TextSplitter import NO_OF_CHAR_IN_CHUNKS

# nltk.download('all') # first time to run for downloading all packages
PARTITION_KEY_SEPARATOR = "___" # 3 underscrolls.

def get_page_number(text):
    try:
        pattern = r"['\"]?<{13,14} (\d+) >{13,14}"
        match = re.search(pattern, text)
        return int(match.group(1)) if match else None
    except:
        return None
def get_partition_key(userId: str, file_id: str):
    return userId + PARTITION_KEY_SEPARATOR + file_id

def get_file_id_from(partitionKey: str) -> str:
    # Split the partitionKey using PARTITION_KEY_SEPARATOR
    parts = partitionKey.split(PARTITION_KEY_SEPARATOR)
    
    # Return the file_id, which should be the second part (index 1)
    if len(parts) > 1:
        return parts[1]
    else:
        raise ValueError("Invalid partitionKey format")

def load_file_with_path(file_path: str, file_type: FileType):
    """
    Loads a file using the appropriate loader based on the file type.

    :param file_path: The path to the file to load.
    :param file_type: The type of the file (from FileType Enum).
    :return: Loaded document content and metadata.
    """
    if file_type == FileType.PDF:
        loader = PyMuPDFLoader(file_path)
    elif file_type in [FileType.DOC, FileType.DOCX]:
        loader = UnstructuredWordDocumentLoader(
        file_path=file_path, mode="elements", strategy="fast",
    )
    elif file_type == FileType.TXT:
        loader = TextLoader(file_path, "utf-8")
    elif file_type == FileType.MD:
        loader = UnstructuredMarkdownLoader(file_path)
    elif file_type in [FileType.PPT, FileType.PPTX]:
        loader = UnstructuredPowerPointLoader(
        file_path = file_path, mode="single", strategy="fast",
    )
    elif file_type == FileType.EPUB:
        loader = UnstructuredEPubLoader(file_path)
    elif file_type == FileType.HTML:
        loader = UnstructuredHTMLLoader(file_path, mode="single", strategy="fast")
    elif file_type == FileType.RTF:
        loader = UnstructuredRTFLoader(file_path)
    elif file_type == FileType.ODT:
        loader = UnstructuredODTLoader(file_path)
    elif file_type == FileType.ODP:
        raise NotImplementedError("ODP file loader is not implemented yet.")
    elif file_type == FileType.ODS:
        raise NotImplementedError("ODS file loader is not implemented yet.")
    elif file_type == FileType.MOBI:
        # Placeholder for MOBI file processing; custom implementation needed
        raise NotImplementedError("MOBI file loader is not implemented yet.")
    elif file_type == FileType.XLSX:
        loader = UnstructuredExcelLoader(file_path=file_path, mode="single")
    else:
        raise ValueError(f"Unsupported file type: {file_type}")

    # Load the document and return the content and metadata
    documents = loader.load()
    return documents



from typing import List, Tuple

def aggregate_results(
    search_results,
    max_chunks: int,
    isChunkContentAllowed: bool,
    num_references: int
) -> Tuple[str, List[Tuple[str, int, int, str]]]:
    """
    Aggregates search results for WhatsApp Q&A flat structure (question, answer only).

    Returns:
        - aggregated_content: concatenated answers
        - references: list of dummy metadata (id, 0, 0, answer)
    """
    SIMILARITY_SCORE_THRESHOLD = float(os.getenv("SIMILARITY_SCORE_THRESHOLD", "0.9"))

    aggregated_content = ""
    total_chunks = 0
    references = []

    # Flatten search results
    flat_hits = [hit for hits in search_results for hit in hits]

    # Always include first N
    for hit in flat_hits[:num_references]:
        answer = getattr(hit.entity, "chunk", "")
        qid = hit.id  # or use hit.entity.get("id", "unknown")
        aggregated_content += answer + "\n"
        total_chunks += 1

        references.append((
            str(qid), 0, 0,
            answer if isChunkContentAllowed else None
        ))

    # Conditionally include more based on score
    for hit in flat_hits[num_references:]:
        if total_chunks >= max_chunks:
            break
        score = getattr(hit, "score", 0.0)
        if score < SIMILARITY_SCORE_THRESHOLD:
            continue

        answer = getattr(hit.entity, "chunk", "")

        qid = hit.id
        aggregated_content += answer + "\n"
        total_chunks += 1

        references.append((
            str(qid), 0, 0,
            answer if isChunkContentAllowed else None
        ))

    return aggregated_content.strip(), references



