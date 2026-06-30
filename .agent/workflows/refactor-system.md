# Quy trình: Refactor System (Tái cấu trúc hệ thống)

**Trigger (Lệnh kích hoạt)**: `/config`, `/refactor`

## Mục tiêu
Cho phép AI thực hiện tái cấu trúc lớn (Refactor) lên chính mã nguồn cốt lõi (Core Runtime) của hệ thống `.agent`.

## Chi tiết
Đây là một quy trình đặc biệt **rủi ro cao (high risk)** và bắt buộc phải tuân theo các State Machine chuẩn:
1. Yêu cầu phê duyệt từ sếp (Approval Gate).
2. Kiểm thử chặt chẽ (Validation Gate) sau khi chạy.
3. Kích hoạt bộ Policy riêng biệt.

Mọi chi tiết thực thi (Step by step) đã được định nghĩa tại `refactor-system.json`.
