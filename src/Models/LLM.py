import sys
import os
import json
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from enum import Enum
from langchain_community.llms import Ollama
from openai import OpenAI
from groq import Groq
import google.generativeai as genai
from Models.AppStatusCode import AppStatusCode
from typing import Tuple
from Logger import logger
import logging
import os

# Ensure log directory exists
log_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'microservices', 'logs')
os.makedirs(log_dir, exist_ok=True)
log_file = os.path.join(log_dir, 'llm.log')

# Add file handler if not already present
if not any(isinstance(h, logging.FileHandler) and h.baseFilename == log_file for h in logger.handlers):
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.INFO)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(name)s:%(lineno)d %(message)s')
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)
from Models.ModelConfig import ModelConfig

Ollama.model_rebuild()
local_llama_model = Ollama(model="gemma3:1b", temperature=0)

class LLM(Enum):
    gpt4o = "gpt-4o"
    gpt4o_mini = "gpt-4o-mini"
    o3_mini = "o3-mini"
    o3 = "o3"
    gemma3_12B = "gemma3:12b"
    gemma3_27B = "gemma3:27b"
    default = "default"
    gemini = "gemini-1.5-flash"
    gemini_2_5 = "gemini-2.5-flash"

def sanitize_text(text: str) -> str:
    return text.encode("utf-8", "ignore").decode("utf-8")

def get_llm_client(modelConfig, api_key):
    model_id = modelConfig.modelId
    if model_id in [LLM.gpt4o.value, LLM.gpt4o_mini.value, LLM.o3.value, LLM.o3_mini.value]:
        return OpenAI(api_key=api_key)
    elif model_id in [LLM.gemma3_12B.value, LLM.gemma3_27B.value]:
        return Groq(api_key=api_key)
    elif model_id in [LLM.gemini.value, LLM.gemini_2_5.value]:
        genai.configure(api_key=api_key)
        return genai.GenerativeModel(model_id)
    else:
        return None

def queryLLM(modelConfig: ModelConfig, api_key: str, myQuestion: str, retrievedKnowledge: str, recent_chat_history: str, chatHistoryContextSummary: str, history) -> Tuple[AppStatusCode, str]:

    myQuestion = sanitize_text(myQuestion)
    retrievedKnowledge = sanitize_text(retrievedKnowledge)
    recent_chat_history = sanitize_text(recent_chat_history)

    sys.stdout.reconfigure(encoding='utf-8')
    logger.info("Starting WhatsApp Chatbot pipeline.")

    try:
        llmClient = get_llm_client(modelConfig, api_key)
        model_id = modelConfig.modelId
        token_param = (
            {"max_completion_tokens": modelConfig.maxCompletionTokens}
            if model_id in [LLM.o3.value, LLM.o3_mini.value]
            else {"max_tokens": modelConfig.maxCompletionTokens}
        )
        if llmClient is None:
            response = local_llama_model.invoke(myQuestion)
            return (AppStatusCode.SUCCESS, response)

        # Step 1: Intent Recognition using exact prompt from document
        intent_prompt = f"""
You are part of a smart assistant system that quietly understands user messages in a WhatsApp conversation related to ACCA courses. The user can send messages in English, Urdu, or Roman Urdu, sometimes mixing languages in a single sentence.

Your job is to:
1. Recognize the **user’s intent** based on the message content
2. Detect whether the **topic has changed** from the last message
3. Summarize the user’s message in natural, conversational English (even if the message was in Urdu or Roman Urdu)

This assistant supports queries related to ACCA subjects, enrollment, LMS, fees, study material, preparation strategy, or tutor support.

Choose the intent from this list:
- greeting (e.g., "Hi", "Salam", "Assalamualaikum", "Good morning")
- smalltalk (e.g., "How are you?", "Thanks", "Shukriya")
- course_info (e.g., asking about subjects, modules, UK vs. international versions)
- fees_payment (fees, discounts, installment, payment proof, payment portals)
- enrollment_lms (LMS login, course access, device policy, freezing, forms)
- study_material (notes, books, tests, attachments, LMS content)
- exam_prep (mock tests, study tips, exam timelines)
- doubt_support (asking for tutor help, WhatsApp group, query contacts)
- counseling (paper planning, exemptions, career questions)
- out_of_scope (unrelated, e.g., weather, politics, jokes)
- unclear (too vague to classify or incomplete)

Return this JSON structure only:
{{
  "intent": "selected label",
  "topic_changed": "true/false",
  "summary": "English summary of the user’s message"
}}

Be precise, and always return the JSON — no explanation.

User message: "{myQuestion}"
Previous topic summary: "{chatHistoryContextSummary}"

IMPORTANT: Your response must always be in English, regardless of the input language. Do not use any other language.
"""
        logger.info(f"[PROMPT][INTENT] Sent to LLM:\n{intent_prompt}")
        if isinstance(llmClient, OpenAI) or isinstance(llmClient, Groq):
            intent_response = llmClient.chat.completions.create(
                model=modelConfig.modelId,
                messages=[{"role": "system", "content": intent_prompt}],
                temperature=0,
                response_format="json",
                **token_param
            )
            logger.info(f"[RAW][INTENT] LLM output:\n{intent_response.choices[0].message.content}")
            intent_data = json.loads(intent_response.choices[0].message.content)
        else:
            intent_response = llmClient.generate_content(intent_prompt,  generation_config=genai.types.GenerationConfig(
                temperature=0,
                response_mime_type="application/json"   # For newer Gemini APIs
            ))
            logger.info(f"[RAW][INTENT] LLM output:\n{intent_response.text}")
            intent_data = json.loads(intent_response.text)

        intent = intent_data["intent"]
        summary = intent_data["summary"]
        logger.info(f"Detected intent: {intent}, Summary: {summary}")

        # Step 2: Handle intent
        if intent in ["greeting", "smalltalk"]:
            chitchat_prompt = f"""
You are a warm, friendly assistant chatting with a student on WhatsApp. The user may send a greeting, thank you message, or casual small talk — often in English, Urdu, or Roman Urdu.

Your goal is to reply in a **natural, human-like way**, keeping it:
- Friendly and polite
- Brief and conversational
- Never robotic or overly formal

The user must never feel like they are speaking to a bot.

Don't ask follow-up questions unless the user asked something directly. Just acknowledge and keep the tone professional yet friendly.

DO NOT mention that you're an assistant or a bot.

Return this JSON only:
{{
  "response": "your reply message",
  "language": "detected language: 'english', 'urdu', 'roman_urdu', or 'mixed'"
}}

User message: "{myQuestion}"

IMPORTANT: Your response must always be in English, regardless of the input language. Do not use any other language.
"""
            logger.info(f"[PROMPT][CHITCHAT] Sent to LLM:\n{chitchat_prompt}")
            if isinstance(llmClient, OpenAI) or isinstance(llmClient, Groq):
                response = llmClient.chat.completions.create(
                    model=modelConfig.modelId,
                    messages=[{"role": "system", "content": chitchat_prompt}],
                    temperature=0,
                    response_format="json",
                    **token_param
                )
                logger.info(f"[RAW][CHITCHAT] LLM output:\n{response.choices[0].message.content}")
                chitchat_output = json.loads(response.choices[0].message.content)
                return (AppStatusCode.SUCCESS, chitchat_output)
            else:
                response = llmClient.generate_content(chitchat_prompt,  generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json"   # For newer Gemini APIs
                ))
                logger.info(f"[RAW][CHITCHAT] LLM output:\n{response.text}")
                chitchat_output = json.loads(response.text)
                return (AppStatusCode.SUCCESS, chitchat_output)

        elif intent in ["course_info", "fees_payment", "enrollment_lms", "study_material", "exam_prep", "doubt_support", "counseling"]:
            rag_prompt = f"""
You are a knowledgeable, polite, and helpful WhatsApp assistant who supports students with ACCA-related questions. You answer only using the context provided below.

You must:
- Sound like a human, not a bot
- Reply briefly and naturally, as if on WhatsApp
- NEVER invent information not present in the context
- If the context is not relevant or doesn’t answer the question, politely admit that and offer to help with something else

Context (trusted knowledge base):
{retrievedKnowledge}

Conversation Summary:
{summary}

Rules:
1. If the user's question is clearly answered in the context, respond naturally and conversationally.
2. If the answer is not found or the context is unclear, respond with:
   - "I'm not sure I have the right info for that. Would you like to ask something else?"
3. NEVER mention that you used a knowledge base or database.
4. Always respond in the same language the user used (English, Urdu, or Roman Urdu).

User question: "{myQuestion}"

IMPORTANT: Your response must always be in English, regardless of the input language. Do not use any other language.

Output Schema
{{
  "answer": "string",      
  "is_confident": "true | false",  
  "language": "string"      
}}

"""
            logger.info(f"[PROMPT][RAG] Sent to LLM:\n{rag_prompt}")
            if isinstance(llmClient, OpenAI) or isinstance(llmClient, Groq):
                rag_response = llmClient.chat.completions.create(
                    model=modelConfig.modelId,
                    messages=[{"role": "system", "content": rag_prompt}],
                    temperature=0,
                    response_format="json",
                    **token_param
                )
                logger.info(f"[RAW][RAG] LLM output:\n{rag_response.choices[0].message.content}")
                rag_output = json.loads(rag_response.choices[0].message.content)
                rag_result = rag_output["answer"]
                rag_confidence = rag_output["is_confident"]
                rag_confidence = "I'm not sure I have the right info" not in rag_result
            else:
                rag_response = llmClient.generate_content(rag_prompt,  generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json"   # For newer Gemini APIs
                ))
                logger.info(f"[RAW][RAG] LLM output:\n{rag_response.text}")
                rag_output = json.loads(rag_response.text)
                rag_result = rag_output["answer"]
                rag_confidence = rag_output["is_confident"]
                rag_confidence = "I'm not sure I have the right info" not in rag_result

        elif intent in ["out_of_scope", "unclear"]:
            fallback_prompt = f"""
You are a friendly, professional assistant on WhatsApp helping students with ACCA-related questions. Sometimes, users may send messages that are:

1. **Out of Scope** – unrelated to ACCA (e.g., questions about weather, AI, politics, football, jokes, etc.)
2. **Unclear or Incomplete** – vague or confusing (e.g., "help plz", "next?", "I’m confused")

Your job is to respond naturally, without sounding robotic or defensive. Use friendly, brief replies that sound like a real human.

Rules:
- Never say you are an AI or chatbot.
- Stay polite and helpful.

Instructions:
- If the message is **out of scope**, reply politely and suggest asking something related to ACCA.
- If the message is **unclear**, ask the user (politely) to rephrase or give more details.

User message: "{myQuestion}"

IMPORTANT: Your response must always be in English, regardless of the input language. Do not use any other language.

Output Schema:
{{
  "response": "string",    
  "handled_as": "out_of_scope" | "unclear",
  "language": "english" | "urdu" | "roman_urdu" | "mixed"
}}

"""
            logger.info(f"[PROMPT][FALLBACK] Sent to LLM:\n{fallback_prompt}")
            if isinstance(llmClient, OpenAI) or isinstance(llmClient, Groq):
                fallback_response = llmClient.chat.completions.create(
                    model=modelConfig.modelId,
                    messages=[{"role": "system", "content": fallback_prompt}],
                    temperature=0,
                    response_format="json",
                    **token_param
                )
                logger.info(f"[RAW][FALLBACK] LLM output:\n{fallback_response.choices[0].message.content}")
                fallback_output = json.loads(fallback_response.choices[0].message.content)
                rag_result = fallback_output["response"]
                rag_confidence = False
                rag_confidence = False
            else:
                fallback_response = llmClient.generate_content(fallback_prompt,  generation_config=genai.types.GenerationConfig(
                    temperature=0,
                    response_mime_type="application/json"   # For newer Gemini APIs
                ))
                logger.info(f"[RAW][FALLBACK] LLM output:\n{fallback_response.text}")
                fallback_output = json.loads(fallback_response.text)
                rag_result = fallback_output["response"]
                rag_confidence = False
                rag_confidence = False

        # Step 3: Escalation Check (omit Rule 4 embeddings for now)
        def should_escalate(intent, rag_confidence, history):
            if intent == "counseling":
                return True
            if intent in ["fees_payment", "enrollment_lms", "doubt_support"] and not rag_confidence:
                history.low_conf_count += 1
                if history.low_conf_count >= 2:
                    return True
            if intent in ["unclear", "out_of_scope"]:
                history.unclear_count += 1
                if history.unclear_count >= 2:
                    return True
            return False

        if should_escalate(intent, rag_confidence, history):
            logger.info("Escalation triggered.")
            return (AppStatusCode.SUCCESS, "Your message has been forwarded to a human support representative.")

        return (AppStatusCode.SUCCESS, rag_result)

    except Exception as e:
        logger.error(f"queryLLM pipeline error: {e}")
        return (AppStatusCode.LLM_ERROR, str(e))
