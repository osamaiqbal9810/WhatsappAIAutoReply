import sys
import os
# Add the parent directory (or the directory where Logger.py is located) to the system path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from enum import Enum
from langchain_community.llms import Ollama
from openai import OpenAI
from groq import Groq
import google.generativeai as genai
from Models.AppStatusCode import AppStatusCode
from typing import Tuple
Ollama.model_rebuild()
local_llama_model = Ollama(model="gemma3:1b", temperature=0)
# gemini_model = genai.GenerativeModel('gemini-1.5-flash')
from Logger import logger
from Models.ModelConfig import ModelConfig
class LLM(Enum):
    gpt4o = "gpt-4o"
    gpt4o_mini = "gpt-4o-mini"  
    # llama3_70b = "llama3-70b-8192" 
    # llama3_8b = "llama3-8b-8192"
    o3_mini="o3-mini"
    o3="o3"
    gemma3_12B="gemma3:12b"
    gemma3_27B="gemma3:27b"
    default = "default"
    gemini = "gemini-1.5-flash"
    gemini_2_5= "gemini-2.5-flash"

def getSystemPrompt(retrievedKnowledge: str, recentChatSummary: str, myQuestion: str):
    if recentChatSummary == "":
        return f"""
            You are my personal assistant. Your job is to help me by answering my question using ONLY the provided information below.

            🎯 **Guidelines:**
            - Answer directly and clearly — do NOT include phrases like "based on the provided information."
            - If the answer includes instructions, lists, or required fields, format them clearly as bullet points or steps.
            - If the context is unclear or not related to the question, reply professionally: "I wasn't able to find the answer in the provided information. Could you please rephrase or clarify your question?"

            📚 **Information Provided:**
            {retrievedKnowledge}

            ❓ **My Question:**
            """    
    else:
        return f"""You are EyraTech AI Assistant, a polite and helpful assistant. Your goal is to provide clear, accurate answers based EXCLUSIVELY on the provided context.
**Core Instructions:**
1. **Answer Source:** Use ONLY the "Relevant Information from Knowledge Base"
2. **No External Knowledge:** Do NOT use any real-world knowledge, internal knowledge, or facts not found in the provided context
3. **Context Usage:**
   - Prioritize "Relevant Information from Knowledge Base" for factual content
4. **Reasoning:** Form conclusions ONLY from the provided recentChatSummary and retrievedKnowledge
5. **Response Style:** Be polite and professional. Do not include phrases like "based on the provided information" in your response
8. **Information Gaps:** If the provided context doesn't contain enough details to answer, politely ask for more information by saying something like "I'd be happy to help, but I need more information about [specific topic]. Could you please provide additional details?"
**Recent Conversation Summary:**
{recentChatSummary}
**Relevant Information from Knowledge Base:**
{retrievedKnowledge}
**User's Question:**
{myQuestion}"""


def queryLLM(
    modelConfig: ModelConfig,
    api_key: str,
    myQuestion: str,
    retrievedKnowledge: str,
    recentChatSummary: str
) -> Tuple[AppStatusCode, str]:

    systemPrompt = getSystemPrompt(retrievedKnowledge, recentChatSummary, myQuestion)
    userPrompt = "Please answer the following question: " + myQuestion
    response = ""

    llmClient = None
    gemini_model = genai.GenerativeModel('gemini-1.5-flash') 
    try:
        model_id = modelConfig.modelId

        # Initialize correct client
        if model_id in [LLM.gpt4o.value, LLM.gpt4o_mini.value, LLM.o3.value, LLM.o3_mini.value]:
            llmClient = OpenAI(api_key=api_key)

        elif model_id in [LLM.gemma3_12B.value, LLM.gemma3_27B.value]:
            llmClient = Groq(api_key=api_key)

        elif model_id in [LLM.gemini.value, LLM.gemini_2_5.value]:
            logger.info("Configure Gemini Model")
            genai.configure(api_key=api_key)
            gemini_model = genai.GenerativeModel(model_id)
           

        elif model_id == LLM.default.value:
            logger.info("Configure default Model")
            # local_llama_model = Ollama(model="gemma3:1b", temperature=0)
            response = local_llama_model.invoke(systemPrompt + userPrompt)
            logger.info(f"response: {response}")
            return (AppStatusCode.SUCCESS, response)

        if llmClient:
            llmClient.max_retries = 0

            # Temperature and token config
            token_param = (
                {"max_completion_tokens": modelConfig.maxCompletionTokens}
                if model_id in [LLM.o3.value, LLM.o3_mini.value]
                else {"max_tokens": modelConfig.maxCompletionTokens}
            )
            temperature = 1 if model_id in [LLM.o3.value, LLM.o3_mini.value] else 0

            # Compose chat message payload
            message_payload = {
                "model": model_id,
                "messages": [
                    {"role": "system", "content": systemPrompt},
                    {"role": "user", "content": userPrompt}
                ],
                "temperature": temperature,
                "stream": True,
                **token_param
            }

            # Add extras for OpenAI-like models only
            if model_id not in [LLM.o3.value, LLM.o3_mini.value]:
                message_payload.update({
                    "top_p": 0,
                    "seed": 0,
                    "stop": None
                })

            # Stream response
            model_response = llmClient.chat.completions.create(**message_payload)
            for chunk in model_response:
                response += chunk.choices[0].delta.content or ""

        elif model_id in [LLM.gemini.value, LLM.gemini_2_5.value]:
            # logger.info(f"{systemPrompt}+{userPrompt}")
            model_response = gemini_model.generate_content(systemPrompt + userPrompt, stream=True)
            for chunk in model_response:
                response += chunk.text

    except Exception as e:
        logger.error(f"queryLLM {modelConfig.modelId} error: {e}")
        error_code = getattr(e, "status_code", AppStatusCode.LLM_ERROR)
        return (AppStatusCode(error_code), "")

    return (AppStatusCode.SUCCESS, response)
