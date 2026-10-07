# TimTroSV — Local Project for Student Room

Hệ thống hỗ trợ sinh viên Đại học Cần Thơ tìm nhà trọ.

- [Tài liệu tổng về chatbot: kiến trúc, KTX, lịch sử, vận hành và báo cáo](docs/CHATBOT.md)

Bản local dùng Datahouse làm kho phòng chính, Graph RAG với nguồn pháp lý từ Word và nguồn thông tin KTX công bố bởi CTU. Giữ flow cũ: Gemini phân tích câu hỏi, Qwen chọn bằng chứng, Gemini tổng hợp và kiểm chứng câu trả lời. Hỗ trợ tìm trọ, hỏi đáp KTX và pháp lý thuê trọ cơ bản; không soạn hợp đồng hoặc điền tờ khai. Cấu hình hiện hành và các báo cáo trước được gộp trong `docs/CHATBOT.md`.

Chat lưu lịch sử theo tài khoản, mở lại hội thoại cũ và dùng lại câu trả lời có nguồn khi hỏi trùng trong cùng ngữ cảnh; có nút tạo cuộc chat mới và xóa lịch sử.

- [Hướng dẫn triển khai FR1 / FR2 / FR4 / FR6 / FR7 và bàn giao FR3 / FR8](docs/FR_DELIVERY_GUIDE.md)
- [Đặc tả yêu cầu](docs/planning/SRS.md)
- [Tài liệu dự án](docs/README.md)
- [Vận hành Docker local và kiểm tra hệ thống](docs/LOCAL_DEPLOYMENT.md)

Nhánh Datahouse/Graph RAG: `codex/source-grounded-datahouse-20261004`.
Các mốc trước đó: nhánh sao lưu `codex/baseline-before-fr-updates` (`6d36e9a`) và triển khai FR `codex/fr1-fr2-fr4-fr6-fr7`.

Đọc hướng dẫn migration trước khi chạy phiên bản mới trên database đang có.
Không commit `.env` hoặc dùng cấu hình dev để triển khai public.
