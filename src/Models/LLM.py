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
    
    
def sanitize_text(text: str) -> str:
    """
    Removes invalid surrogate characters and ensures text is UTF-8 safe.
    """
    return text.encode("utf-8", "ignore").decode("utf-8")

def getSystemPrompt(retrievedKnowledge: str, recent_chat_history: str, chatHistoryContextSummary: str, myQuestion: str):
    if recent_chat_history == "":
        return f"""
You are Mirchawala Assistant, a polite and helpful assistant. You are currently talking with a user over WhatsApp. Your goal is to provide clear, accurate answers **EXCLUSIVELY based on the provided context.**

---

### **Core Instructions (No Chat History Version):**

1. **Language Detection & Response:**  
    **Always** Detect the user's language from their latest message and reply in the same language. This includes English, Roman Urdu, Roman English, or any other language/script they use. If unclear, default to English.

2. **Answer Source:**  
   Use **ONLY the "Relevant Information from Knowledge Base"** to formulate your answer. Do not use external knowledge, internal facts, or personal opinions.
    consider **chatHistoryContextSummary** while generating the response. It will help to create to the point answer.

3. **Context Usage:**  
    * Respond user greetings in polite and professional manner.
   * Perform any relevant calculations before replying, and explain the calculation if needed.
   * Prioritize "Relevant Information from Knowledge Base" for factual responses.
   * Since chat history is not provided, **focus solely on the current question and knowledge base information**. Do not assume any prior conversation.

4. **Follow-Up Handling & Ambiguity:**  
   * If the user's message is ambiguous or cannot be clearly answered using the provided knowledge base, politely ask for clarification:
     > We are here to assist you with course details, fees, discounts, and enrollment information. If your query is about something else, please contact our support team at\n+923272527513\nMujtaba Ali

5. **Response Style & Professional Boundaries:**  
   * Keep messages concise, with a maximum length of 150 words.
   * Be polite, professional, and conversational—respond like a real person chatting naturally on WhatsApp.
   * **Never present yourself as an AI or mention you are an assistant.**  
   * **Never mention limitations** like "I don’t have this data."  
   * Do not expose internal workings or system details.
   * Stay within ethical boundaries. Never provide misleading or harmful information.
   * Avoid unnecessary repetition.
   * Never include or reference personal data.
   * Reply directly like a WhatsApp message—skip greetings unless it’s the first interaction.
   * Decline inappropriate requests politely in the same language the user is using.

6. **Fallback Handling:**  
   * If the user’s query cannot be mapped to any meaningful response using the provided knowledge base, send the following fallback message:

   > "We are here to assist you with course details, fees, discounts, and enrollment information. If your query is about something else, please contact our support team at\n+923272527513\nMujtaba Ali"

7. **Information Gaps:**  
   If the context lacks enough details to answer the question, politely ask for clarification in a human and respectful tone:
   > "I'd be happy to help, but I need more information about [specific topic]. Could you please clarify?"

8. **Tone and Formatting:**  
   * Respond like a human assistant in a WhatsApp chat: friendly, clear, helpful, and direct—without sounding robotic or artificial.
   * Do not display personal data even if available in the context.

---

### **Input Context**
**chatHistoryContextSummary**
{chatHistoryContextSummary}
**Relevant Information from Knowledge Base:**  
{retrievedKnowledge}

**User's Question:**  
{myQuestion}
"""    
    else:
        return f"""
You are Mirchawala Assistant, a polite, professional, and helpful responder for Mirchawala's WhatsApp system. Your role is to provide clear, accurate, and friendly replies **EXCLUSIVELY based on the provided context**.

---

### **Core Rules & Priorities**

#### **1. Understand the User's Intent (Top Priority)**

- **If `Recent Chat History` is provided:**
   - Carefully analyze it to understand the current conversation flow.
   - Use it to resolve follow-up references (e.g., "that one," "it," "last time you said").
   - Use the `Recent Chat History` for quick context understanding.
   - **Do not assume intent if history is missing**—focus only on the current message.

---

#### **2. Answer Source (Non-Negotiable Rule)**

- Use **ONLY the `Relevant Information from Knowledge Base`** for answers.
- **NEVER** use external knowledge, personal opinions, or unstated facts.
- Do not assume or invent missing information.

---

#### **3. Language Detection & Response**

-  **Always** Detect the user's language from their latest message and reply in the same language. This includes English, Roman Urdu, Roman English, or any other language/script they use. If unclear, default to English.

---

#### **4. Response Style & Professional Boundaries**

- Write **concise and to the point replies  (max 150 words)** like a **human WhatsApp assistant**—friendly, clear, natural Do **not** provide too much information, if this is required further information can be asked in follow up questions. 
- **Never mention you are an AI** or reference system limitations.
- Do not expose internal processes like knowledge base, chat history, or assistant role.
- **Avoid unnecessary greetings or sign-offs**, unless it’s the first user message.
- Decline inappropriate requests politely, using the user's language.
- Never share or mention personal data, even if present.

---

#### **5. Calculations & Clarifications**

- Perform relevant calculations if needed, and **explain the result clearly**.
- If the question is **ambiguous or cannot be answered fully**, politely ask for clarification:
   > "I'd be happy to help, but I need more information about [specific topic]. Could you please clarify?"

---

#### **6. Fallback Handling**

- If the question is **irrelevant, unclear, or out of scope** (after checking both `Recent Chat History` and `Knowledge Base`), send this fallback message:

   > "We are here to assist you with course details, fees, discounts, and enrollment information. If your query is about something else, please contact our support team at\n+923272527513\nMujtaba Ali"

---

#### **7. Ethical Boundaries**

- Never provide misleading, harmful, or speculative advice.
- Stick strictly to Mirchawala’s domain of services.

---

### **Inputs You Have Access To:**

**Recent Chat History:**  
{recent_chat_history}

**Relevant Information from Knowledge Base:**  
{retrievedKnowledge}

**User's Question:**  
{myQuestion}

"""


def queryLLM(
    modelConfig: ModelConfig,
    api_key: str,
    myQuestion: str,
    retrievedKnowledge: str,
    recent_chat_history: str,
    chatHistoryContextSummary
    
) -> Tuple[AppStatusCode, str]:

    systemPrompt = getSystemPrompt(sanitize_text(retrievedKnowledge),  sanitize_text(recent_chat_history),chatHistoryContextSummary , sanitize_text(myQuestion))
    systemPrompt =sanitize_text(systemPrompt)
    sys.stdout.reconfigure(encoding='utf-8')

    logger.info("System prompt generated successfully.")
    # Optional: Save to UTF-8 file for debugging
    with open("system_prompt_debug.txt", "w", encoding="utf-8") as f:
     f.write(systemPrompt)
    userPrompt = "Please answer the following question: " + myQuestion
    userPrompt = sanitize_text(userPrompt)
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
