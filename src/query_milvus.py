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

from openai import OpenAI
from groq import Groq
import google.generativeai as genai

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

import time

# In-memory cache for user history
_history_cache = {}
_HISTORY_EXPIRY_SECONDS = 3600  # 1 hour expiry for demonstration

def clear_history_cache(user_id=None):
    """Clear the cache for a specific user or all users."""
    if user_id:
        _history_cache.pop(user_id, None)
    else:
        _history_cache.clear()

def _get_history(user_id):
    now = time.time()
    # Remove expired entries
    expired = [uid for uid, (h, ts) in _history_cache.items() if now - ts > _HISTORY_EXPIRY_SECONDS]
    for uid in expired:
        del _history_cache[uid]
    # Get or create
    if user_id in _history_cache:
        _history_cache[user_id] = (_history_cache[user_id][0], now)  # update timestamp
        return _history_cache[user_id][0]
    else:
        class HistoryState:
            def __init__(self):
                self.low_conf_count = 0
                self.unclear_count = 0
        h = HistoryState()
        _history_cache[user_id] = (h, now)
        return h

def whatsapp_queryLLM(
    query: str,
    num_references: int,
    modelConfig: ModelConfig,
    api_key: str,
    user_id: str,
    chatHistoryContextSummary: str = "",
    recent_chat_history: str = ""
) -> dict:
    logger.info("Starting WhatsApp Q&A retrieval")
    max_chunks = 0

    # --- Step 0: Translate query to English if needed ---
    from Models.LLM import get_llm_client, LLM
    llmClient = get_llm_client(modelConfig, api_key)
    model_id = modelConfig.modelId
    token_param = (
        {"max_completion_tokens": modelConfig.maxCompletionTokens}
        if model_id in [LLM.o3.value, LLM.o3_mini.value]
        else {"max_tokens": modelConfig.maxCompletionTokens}
    )
    translation_prompt = f"""
You are a translation assistant. Your job is to translate the following WhatsApp message to English if it is not already in English. If the message is already in English, return it as is. Do not add any explanation or extra text. Return only the translated or original message as plain text.

Message:
{query}
"""
    logger.info(f"[PROMPT][TRANSLATE] Sent to LLM:\n{translation_prompt}")
    if isinstance(llmClient, (OpenAI, Groq)):
        translation_response = llmClient.chat.completions.create(
            model=modelConfig.modelId,
            messages=[{"role": "system", "content": translation_prompt}],
            temperature=0,
            response_format="text",
            **token_param
        )
        translated_query = translation_response.choices[0].message.content.strip()
        logger.info(f"[RAW][TRANSLATE] LLM output:\n{translated_query}")
    else:
        translation_response = llmClient.generate_content(translation_prompt,  generation_config=genai.types.GenerationConfig(
            temperature=0,
            response_mime_type="text/plain"
        ))
        translated_query = translation_response.text.strip()
        logger.info(f"[RAW][TRANSLATE] LLM output:\n{translated_query}")

    # Use translated_query for combined_query
    combined_query = chatHistoryContextSummary + "\n" + translated_query if chatHistoryContextSummary else translated_query

    try:
        max_chunks = get_safe_chunk_limit_by_model(
            modelConfig, num_references, reserved_prompt_text=translated_query)
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

    history = _get_history(user_id)
    try:
        (status, llm_response) = queryLLM(
            modelConfig=modelConfig,
            api_key=api_key,
            myQuestion=translated_query,
            retrievedKnowledge=aggregated_content,
            recent_chat_history=recent_chat_history,
            chatHistoryContextSummary=chatHistoryContextSummary,
            history=history
        )
        # If escalation is triggered, clear the user's history
        if isinstance(llm_response, str) and "forwarded to a human" in llm_response:
            clear_history_cache(user_id)
    except Exception as e:
        logger.error(f"queryLLM failed: {e}", exc_info=True)
        print(e)
        return {
            "status": AppStatusCode.LLM_ERROR.value,
            "answer": "An error occurred while generating the answer. {e}",
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
        # input_data = sys.stdin.readline().strip()
        # OR test manually:
        input_data = """{"user_id":"demo-user","data":{"query":"AslamoAlaikum.kya biryani mil sakti h?", "num_of_reference":20,"model":{"modelId":"gemini-2.5-flash","contextWindow":32768,"maxCompletionTokens":8192},"api_key":"AIzaSyChPOCT84gw17qIgKOeZAlAxIlaFV4JQCA"}}"""

        if input_data:
            data = json.loads(input_data)
            data_payload = data.get("data", {})

            user_query = data_payload.get("query")
            num_references = data_payload.get("num_of_reference", 5)
            api_key = data_payload.get("api_key")
            chatHistoryContextSummary = data_payload.get("chatHistoryContextSummary", "")
            recent_chat_history = data_payload.get("recent_chat_history", "")

            model_dict = data_payload.get("model")
            user_id = data.get("user_id", "default-user")
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
                    user_id=user_id,
                    chatHistoryContextSummary=chatHistoryContextSummary,
                    recent_chat_history=recent_chat_history
                )

                print(json.dumps(result) + "\n", flush=True)
                # print("===END===", flush=True)
            else:
                logger.error("Model information is missing or not in the correct format.")
    except Exception as e:
        logger.error(f"WhatsApp query pipeline error: {e}", exc_info=True)
