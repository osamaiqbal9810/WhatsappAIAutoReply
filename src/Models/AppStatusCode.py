from enum import Enum
from typing import Tuple
class AppStatusCode(Enum):
    SUCCESS = 0 # (0, "Success")
    FILE_NOT_FOUND = 10 # (10, "File not found")
    FILE_TYPE_NOT_SUPPORTED = 11 # (11, "File type not supported")
    FILE_READ_FAILED = 12 # (12, "File read failed") 
    FILE_CONVERSION_TO_MD_FAILED = 13 # (13, "File conversion to md failed")

    VECTOR_CREATION_FAILED = 20 # (20, "Vector creation failed")

    MILVUS_CONNECTION_FAILED = 30 # (30, "Milvus connection failed")
    MILVUS_CHUNKS_CREATION_FAILED = 31 # (31, "Milvus chunks creation failed")
    MILVUS_CHUNKS_DELETION_FAILED = 32 # (32, "Milvus chunks deletion failed")
    MILVUS_CHUNKS_STORAGE_FAILED = 33 # (33, "Milvus chunks storage failed")
    
    MILVUS_PARTITION_KEY_EXISTS = 34 # (34, "Milvus partition key exists")
    MILVUS_PARTITION_KEY_DOES_NOT_EXIST = 35 # (35, "Milvus partition key does not exist") 

    MAX_TOKEN_ERROR = 50 # (50, "Maximum token error")
    TOP_NO_OF_REFERENCES_ERROR = 51 # (51, "Top no of references error")
    LLM_ERROR = 100 # (100, "LLM error")

    BAD_REQUEST = 400 # (400, "The server could not understand the request due to invalid syntax. Review the request format and ensure it is correct.")
    UNAUTHORIZED = 401 # (401, "The request was not successful because it lacks valid authentication credentials for the requested resource. Ensure the request includes the necessary authentication credentials and the api key is valid.")
    FORBIDDEN = 403 # (403, "Forbidden")
    NOT_FOUND = 404 # (404, "The requested resource could not be found. Check the request URL and the existence of the resource.")
    UNPROCESSABLE_ENTITY = 422 # (422, "The request was well-formed but could not be followed due to semantic errors. Verify the data provided for correctness and completeness.")
    TOO_MANY_REQUESTS = 429 # (429, " Too many requests were sent in a given timeframe. Implement request throttling and respect rate limits.") 

    INTERNAL_SERVER_ERROR = 500 # (500, "The server could not understand the request due to invalid syntax. Review the request format and ensure it is correct.")
    BAD_GATEWAY = 502 # (502, "The server received an invalid response from an upstream server. This may be a temporary issue; retrying the request might resolve it.")
    SERVICE_UNAVAILABLE = 503 # (503, "The server is not ready to handle the request, often due to maintenance or overload. Wait before retrying the request.")
    PARTIAL_CONTENT = 206 # (206, "Only part of the resource is being delivered, usually in response to range headers sent by the client. Ensure this is expected for the request being made.")