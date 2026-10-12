"""Chatbot tìm trọ / KTX / pháp lý thuê trọ — ghép từ branch PHUC (07/10), chỉ phần chatbot.

Risk Detection tạm hoãn; chatbot không dùng điểm rủi ro trong xếp hạng hoặc ngữ cảnh sinh câu trả lời.
"""

from .chatbot import chatbot_router, init_chatbot

__all__ = ["chatbot_router", "init_chatbot"]
