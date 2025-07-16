import sys
import json
import os
from dotenv import load_dotenv
from Logger import logger
from Models.LLM import ModelConfig, queryLLM
from Models.AppStatusCode import AppStatusCode
from MilvusManager import MilvusManager
from Helper import aggregate_results
from TextSplitter import sentence_Transformer
from constants import (
    USABLE_CONTEXT_FRACTION,
    MAX_REFERENCE_CHUNKS
)

import logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("milvus_whatsapp")
logger.setLevel(logging.DEBUG)
logging.basicConfig(level=logging.DEBUG)
# Load environment variables
load_dotenv()

# --- Milvus Setup for WhatsApp QA Collection ---
milvus_manager = MilvusManager(
    host=os.getenv("MILVUS_DB_HOST"),
    port=os.getenv("MILVUS_DB_PORT"),
    databaseName=os.getenv("MILVUS_DB_NAME"),
    collectionName=os.getenv("MILVUS_DB_COLLECTION_NAME", "whatsapp_data"),
    collectionDescription=os.getenv("MILVUS_DB_COLLECTION_DESCRIPTION", "QA over WhatsApp chats"),
    vectorSize=int(os.getenv("MILVUS_DB_VECTOR_FIELD_DIMENSION", "384"))
)

def estimated_reserved_token_count(text: str) -> int:
    avg_chars_per_token = int(os.getenv("APPROX_CHAR_PER_TOKEN", "4"))
    return len(text) // avg_chars_per_token

def get_safe_chunk_limit_by_model(modelConfig: ModelConfig, num_references: int, reserved_prompt_text: str = "") -> int:
    context_token_limit = int(modelConfig.contextWindow * USABLE_CONTEXT_FRACTION)
    reserved_tokens = estimated_reserved_token_count(reserved_prompt_text)
    usable_tokens = max(context_token_limit - reserved_tokens, 0)
    tokens_per_chunk = int(os.getenv("SENTENCE_SPLITTER_CHUNK_SIZE", "700"))
    estimated_available_chunk_limit = usable_tokens // tokens_per_chunk
    return min(estimated_available_chunk_limit, MAX_REFERENCE_CHUNKS), context_token_limit

def whatsapp_queryLLM(
    query: str,
    num_references: int,
    modelConfig: ModelConfig,
    api_key: str,
    chatHistoryContextSummary: str = "",
    recent_chat_history: str = ""
) -> dict:
    logger.info("Starting WhatsApp Q&A retrieval")
    max_chunks = 0

    try:
        max_chunks = get_safe_chunk_limit_by_model(
            modelConfig, num_references, reserved_prompt_text=query)
        if max_chunks == 0:
            return {
                "status": AppStatusCode.MAX_TOKEN_ERROR.value,
                "answer": "",
                "data": []
            }
    except Exception as e:
        logger.error(f"Token budget calculation failed: {e}")
        return {
            "status": AppStatusCode.MAX_TOKEN_ERROR.value,
            "answer": "",
            "data": []
        }

    if not milvus_manager.check_connection():
        logger.error("Milvus connection failed")
        return {
            "status": AppStatusCode.MILVUS_CONNECTION_FAILED.value,
            "answer": "",
            "data": []
        }
    combined_query = chatHistoryContextSummary + "\n" + query if chatHistoryContextSummary else query
    query_vector = sentence_Transformer.encode(sentences=combined_query, show_progress_bar=False)

    # ✅ Use MilvusManager's internal search method (no filter expression)
    results = milvus_manager.search(query_vector=query_vector, top_k=num_references)
    if not results:
        logger.warning("No results returned from Milvus search.")
        return {
            "status": AppStatusCode.NOT_FOUND.value,
            "answer": "Sorry, I couldn't find anything relevant.",
            "data": []
        }

    aggregated_content, references = aggregate_results(
        search_results=results,
        max_chunks=max_chunks,
        isChunkContentAllowed=True,
        num_references=num_references
    )

    try:
        (status, llm_response) = queryLLM(
            modelConfig=modelConfig,
            api_key=api_key,
            myQuestion=query,
            retrievedKnowledge=aggregated_content,
            recent_chat_history=recent_chat_history,
            chatHistoryContextSummary = chatHistoryContextSummary
        )
    except Exception as e:
        logger.error(f"queryLLM failed: {e}", exc_info=True)
        return {
            "status": AppStatusCode.LLM_ERROR.value,
            "answer": "An error occurred while generating the answer.",
            "data": []
        }

    return {
        "status": status.value if isinstance(status, AppStatusCode) else status,
        "answer": llm_response,
        "data": [
            {
                "file_id": r[0] if r[0] else "",
                "chunkNumber": r[1],
                "pageNo": r[2],
                "chunk": r[3]
            }
            for r in references
        ]
    }

# === STDIN Integration ===
if __name__ == "__main__":
    try:
        input_data = sys.stdin.readline().strip()
        # OR test manually:
        #input_data = """{"user_id":"demo-user","data":{"query":"What is required to join LMS?", "num_of_reference":20,"model":{"modelId":"gemini-2.5-flash","contextWindow":32768,"maxCompletionTokens":8192},"api_key":"AIzaSyChPOCT84gw17qIgKOeZAlAxIlaFV4JQCA"}}"""

        if input_data:
            data = json.loads(input_data)
            data_payload = data.get("data", {})

            user_query = data_payload.get("query")
            num_references = data_payload.get("num_of_reference", 5)
            api_key = data_payload.get("api_key")
            chatHistoryContextSummary = data_payload.get("chatHistoryContextSummary", "")
            recent_chat_history = data_payload.get("recent_chat_history", "")

            model_dict = data_payload.get("model")
            if model_dict and isinstance(model_dict, dict):
                model = ModelConfig(
                    modelId=model_dict.get("modelId"),
                    contextWindow=model_dict.get("contextWindow"),
                    maxCompletionTokens=model_dict.get("maxCompletionTokens")
                )

                result = whatsapp_queryLLM(
                    query=user_query,
                    num_references=num_references,
                    modelConfig=model,
                    api_key=api_key,
                    chatHistoryContextSummary=chatHistoryContextSummary,
                    recent_chat_history=recent_chat_history
                )

                print(json.dumps(result) + "\n", flush=True)
                # print("===END===", flush=True)
            else:
                logger.error("Model information is missing or not in the correct format.")
    except Exception as e:
        logger.error(f"WhatsApp query pipeline error: {e}", exc_info=True)
