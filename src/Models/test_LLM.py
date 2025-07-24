import pytest
from unittest.mock import patch, MagicMock
from Models.LLM import queryLLM
from Models.AppStatusCode import AppStatusCode
from Models.ModelConfig import ModelConfig

class DummyHistory:
    def __init__(self):
        self.low_conf_count = 0
        self.unclear_count = 0

def make_model_config(modelId):
    return ModelConfig(
        modelId=modelId,
        contextWindow=128000,
        maxCompletionTokens=16384
    )

def test_local_model_invoked_on_none_client():
    with patch('Models.LLM.get_llm_client', return_value=None), \
         patch('Models.LLM.local_llama_model') as mock_local:
        mock_local.invoke.return_value = 'local response'
        status, response = queryLLM(make_model_config('unknown'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.SUCCESS
        assert response == 'local response'

def test_greeting_intent_openai():
    mock_intent = {'intent': 'greeting', 'topic_changed': 'false', 'summary': 'Hello'}
    mock_chitchat = {'response': 'Hi!', 'language': 'english'}
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_intent)))], model='m'),
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_chitchat)))], model='m')
    ]
    with patch('Models.LLM.get_llm_client', return_value=mock_client), \
         patch('Models.LLM.json.loads', side_effect=[mock_intent, mock_chitchat]):
        status, response = queryLLM(make_model_config('gpt-4o'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.SUCCESS
        assert response == mock_chitchat

def test_course_info_intent_openai():
    mock_intent = {'intent': 'course_info', 'topic_changed': 'false', 'summary': 'About course'}
    mock_rag = {'answer': 'Course details', 'is_confident': 'true', 'language': 'english'}
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_intent)))], model='m'),
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_rag)))], model='m')
    ]
    with patch('Models.LLM.get_llm_client', return_value=mock_client), \
         patch('Models.LLM.json.loads', side_effect=[mock_intent, mock_rag]):
        status, response = queryLLM(make_model_config('gpt-4o'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.SUCCESS
        assert response == 'Course details'

def test_out_of_scope_intent_openai():
    mock_intent = {'intent': 'out_of_scope', 'topic_changed': 'false', 'summary': 'Not related'}
    mock_fallback = {'response': 'Please ask about ACCA.', 'handled_as': 'out_of_scope', 'language': 'english'}
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_intent)))], model='m'),
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_fallback)))], model='m')
    ]
    with patch('Models.LLM.get_llm_client', return_value=mock_client), \
         patch('Models.LLM.json.loads', side_effect=[mock_intent, mock_fallback]):
        status, response = queryLLM(make_model_config('gpt-4o'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.SUCCESS
        assert response == 'Please ask about ACCA.'

def test_escalation_on_counseling():
    mock_intent = {'intent': 'counseling', 'topic_changed': 'false', 'summary': 'Need advice'}
    mock_rag = {'answer': 'Advice', 'is_confident': 'true', 'language': 'english'}
    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_intent)))], model='m'),
        MagicMock(choices=[MagicMock(message=MagicMock(content=str(mock_rag)))], model='m')
    ]
    with patch('Models.LLM.get_llm_client', return_value=mock_client), \
         patch('Models.LLM.json.loads', side_effect=[mock_intent, mock_rag]):
        status, response = queryLLM(make_model_config('gpt-4o'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.SUCCESS
        assert 'forwarded to a human' in response

def test_exception_handling():
    with patch('Models.LLM.get_llm_client', side_effect=Exception('fail')):
        status, response = queryLLM(make_model_config('gpt-4o'), 'key', 'Q', 'K', 'H', 'S', DummyHistory())
        assert status == AppStatusCode.LLM_ERROR
        assert 'fail' in response
