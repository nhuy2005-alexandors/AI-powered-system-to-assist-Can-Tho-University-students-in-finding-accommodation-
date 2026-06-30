---
trigger: "When Co-op mode is activated or Claude Code is running in the workspace."
---

# COOP_PROTOCOL.md - Giao thức Phối hợp Đa Tác nhân (Claude & Gemini)

> **Mục tiêu**: Xóa bỏ sự mơ hồ trong giao tiếp giữa các AI. Biến "Stigmergy" (Giao tiếp qua dấu vết môi trường) từ một khái niệm trên giấy thành các quy tắc mã hóa cứng (code-driven).

---

## 1. MÂU THUẪN DANH TÍNH (Identity Override Rules)

Theo mặc định (Solo-Ninja Mode), Gemini (Antigravity IDE) là Orchestrator toàn cục. Tuy nhiên, khi **Claude Co-op Mode** được kích hoạt, danh tính bị ghi đè như sau:
- **Claude Code**: Nắm quyền Orchestrator (Kiến trúc sư / Planner). Có quyền thay đổi kiến trúc, tạo và phân rã task.
- **Gemini**: Bị giáng cấp xuống làm **Lead Executor**. Phải tuân thủ `task.md` do Claude Code tạo ra và tập trung vào viết code, test, chạy terminal.

---

## 2. NHẬN DIỆN CHẾ ĐỘ CO-OP (Trigger Detect)

Làm sao để hệ thống biết đang ở chế độ Co-op? Không phải ngầm hiểu, mà thông qua **Cờ hiệu vật lý (Physical Flag)**:
1. **Bắt đầu Session**: Khi Claude Code bắt đầu phiên làm việc điều phối, nó **BẮT BUỘC** phải tạo một file cờ hiệu tại `.agent/state/coop-mode.flag` (Nội dung file có thể rỗng hoặc chứa timestamp).
2. **Override Kích hoạt**: Sự xuất hiện của file này là tín hiệu (interrupt) để Gemini ngay lập tức vô hiệu hóa tính cách Orchestrator tự biên tự diễn của mình và chuyển sang trạng thái "Sẵn sàng nhận Task".
3. **Kết thúc Session**: Khi Claude Code hoàn thành đợt quy hoạch, nó có trách nhiệm xóa file cờ hiệu này đi. Nếu file bị xóa, Gemini quay lại làm Solo-Ninja.

---

## 3. FILE LOCKING (Chống Race Condition)

Vì cả hai AI dùng chung `task.md` và `ERRORS.md`, để tránh ghi đè lẫn nhau:
1. **Nguyên tắc Lock**: Bất kỳ AI nào (Claude hoặc Gemini) muốn sửa `task.md` đều PHẢI tạo file `.agent/state/task.md.lock` trước khi sửa.
2. **Check Lock**: Trước khi đọc/ghi `task.md`, AI phải kiểm tra sự tồn tại của file `.lock`. Nếu có, phải chờ cho đến khi file bị xóa.
3. **Release Lock**: Sau khi ghi xong, AI **BẮT BUỘC** phải xóa file `.lock`.
4. *Khuyến cáo sau này*: Sử dụng `active-tasks.json` để lock ở cấp độ Task thay vì khóa toàn bộ file text.

---

## 4. CHỨNG TỪ (Evidence-based Workflow)

- **Không Evidence = Không Xong Task**: Executor (Gemini) không được tự ý đánh dấu `[x]` vào `task.md` nếu không để lại link tới PR, hoặc copy paste Terminal Log Output chứng minh code chạy được thành công.
- **Error Handoff**: Nếu Gemini bị kẹt (bug khó), nó không được tự mình đâm đầu vào ngõ cụt. Nó phải gọi `error-logger.js` để ném lỗi vào `ERRORS.md`, sau đó đánh dấu task là `[ ] Chờ review` để Claude Code thức dậy và quy hoạch lại kiến trúc.
