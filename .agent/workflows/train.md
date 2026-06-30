---
description: Kích hoạt quy trình xử lý dữ liệu và huấn luyện mô hình Trí tuệ Nhân tạo (Machine Learning/AI).
---

# Quy trình Huấn luyện Mô hình AI (Model Training)
**Trigger (Lệnh kích hoạt)**: `/train`

## Mục tiêu
Tự động hóa chu trình từ dữ liệu thô (Raw Data) đến việc đưa ra một mô hình Machine Learning/AI hoạt động được, cụ thể áp dụng cho hệ thống **Gợi ý & Ghép cặp phòng trọ**.

## Các bước thực hiện

### Bước 1: Khởi tạo Dữ liệu & Tiền xử lý (Data Preprocessing)
- Load dữ liệu (từ file CSV hoặc query qua Postgres MCP).
- Xử lý các giá trị Null, Outliers (nếu là giá tiền trọ), và chuyển hóa dữ liệu hạng mục (One-hot encoding cho Giới tính, Khu vực).

### Bước 2: Huấn luyện Mô hình (Model Training)
- Dựa trên yêu cầu, thiết lập thuật toán:
  - Nếu là ghép cặp bạn cùng phòng: Sử dụng **K-Means Clustering** hoặc **KNN**.
  - Nếu là gợi ý nhà trọ: Sử dụng **Collaborative Filtering** hoặc **Content-based Filtering**.
- Tiến hành fit mô hình trên tập Train.

### Bước 3: Đánh giá & Tối ưu (Evaluation)
- Sử dụng các chỉ số trong `data-science.md` để chấm điểm mô hình.
- In ra báo cáo tóm tắt hiệu năng (Ví dụ: "Thuật toán phân nhóm sinh viên với Silhouette Score = 0.75, cụm rất rõ nét").

### Bước 4: Lưu trữ Mô hình
- Serialize mô hình bằng `joblib` hoặc `pickle` để Backend (Nodejs/Python) có thể sử dụng lại mà không cần train lại từ đầu.
