from app.config import Settings
from app.room_service.chatbot.schemas import ChatAskRequest
from app.room_service.chatbot.service import ChatService
from app.room_service.chatbot.providers import DeterministicFakeEmbedder, FallbackResponseGenerator

def test_proxy_key_is_exclusive_and_masked():
    config = Settings(_env_file=None, gemini_proxy_api_key="proxy-test-only", gemini_api_key="old-google")
    assert config.configured_gemini_keys == ["proxy-test-only"]
    assert "proxy-test-only" not in repr(config)

def test_direct_google_fallback_is_preserved():
    config = Settings(_env_file=None, gemini_proxy_api_key="", gemini_api_key="google-test", gemini_api_key_1="", gemini_api_key_2="", gemini_api_key_3="")
    assert config.configured_gemini_keys == ["google-test"]

def test_emergency_keeps_priority_over_ktx(monkeypatch):
    import app.ktx.chat as ktx
    def forbidden(*args):
        raise AssertionError("Emergency must not enter KTX handler")
    monkeypatch.setattr(ktx, "answer_ktx", forbidden)
    service = ChatService(object(), DeterministicFakeEmbedder(), FallbackResponseGenerator([]))
    response = service.ask(ChatAskRequest(message="KTX đang cháy, cứu tôi với!"))
    assert response.intent == "emergency"

def test_dormitory_response_is_returned_before_generic_legal(monkeypatch):
    import app.ktx.chat as ktx
    marker = object()
    monkeypatch.setattr(ktx, "answer_ktx", lambda *args: marker)
    service = ChatService(object(), DeterministicFakeEmbedder(), FallbackResponseGenerator([]))
    assert service.ask(ChatAskRequest(message="KTX A4 có gì?")) is marker

def test_general_ktx_fire_safety_is_not_an_emergency():
    from app.room_service.chatbot.parser import parse_query
    for question in ["KTX có nội quy phòng cháy chữa cháy nào?", "Xe đang chạy trong KTX thì phải gửi ở đâu?"]:
        assert parse_query(question).intent != "emergency"
