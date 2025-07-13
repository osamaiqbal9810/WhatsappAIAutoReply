import os
from sentence_transformers import SentenceTransformer
from llama_index.core.node_parser import SentenceSplitter
from langchain_text_splitters import MarkdownHeaderTextSplitter
from langchain.schema import Document

from typing import List, Tuple
from dotenv import load_dotenv
# loading env variable
load_dotenv()

splitter = SentenceSplitter(chunk_size=int(os.getenv("SENTENCE_SPLITTER_CHUNK_SIZE")), chunk_overlap = int(os.getenv("SENTENCE_SPLITTER_CHUNK_OVERLAP")))

sentence_Transformer = SentenceTransformer('all-MiniLM-L12-v2')


NO_OF_CHAR_IN_CHUNKS = 4

headers_to_split_on = [("#", "Header 1"), ("##", "Header 2"), ("###", "Header 3"),  ("####", "Header 4"), ("#####", "Header 5"), ("######", "Header 6"), ("<<<<<<<<<<<<<<<", "Page")]
markdownSplitter = MarkdownHeaderTextSplitter(headers_to_split_on=headers_to_split_on, strip_headers=False)

def create_chunks_from_md(documents: List[Document]) -> List[str]:
    """
    Creates chunks from a given list of documents. This function will split the documents based on headers and then split
    each section into smaller chunks based on a given character threshold.
    """
    all_chunks = []
    
    # Loop through each document in the list
    for document in documents:
        # Use the markdown splitter to split the document based on headers
        list_of_documents = markdownSplitter.split_text(text = document.page_content)
        
        # Loop through each document section obtained from the header split
        for doc_section in list_of_documents:
            # Use the sentence splitter to further split each section into smaller chunks
            page_content = doc_section.page_content
            # Check if the page content is longer than the defined chunk size
            if len(page_content) > int(os.getenv("SENTENCE_SPLITTER_CHUNK_SIZE")) * NO_OF_CHAR_IN_CHUNKS:
                # Split the page content into chunks
                chunks = splitter.split_text(doc_section.page_content)
                # Add the resulting chunks to the overall list of chunks
                all_chunks.extend(chunks)
            else:
                # If the page content is shorter than the defined chunk size, add it to the list of chunks
                all_chunks.append(page_content)
    
    return all_chunks


def create_chunks(documents: List[Document]) -> List[str]:
    all_chunks = []
    for document in documents:
        page_content = document.page_content
        chunks = splitter.split_text(page_content)
        all_chunks.extend(chunks)
    return all_chunks