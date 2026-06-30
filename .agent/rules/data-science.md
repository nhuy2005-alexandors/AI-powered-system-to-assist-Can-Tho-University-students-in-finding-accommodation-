# 🧬 Quy Tắc Khoa Học Dữ Liệu (Data Science Ruleset)

Đối với các bài toán liên quan đến Trí tuệ nhân tạo (AI), Phân cụm (Clustering), Khuyến nghị (Recommendation) hoặc Machine Learning, AI phải tuân thủ nghiêm ngặt quy trình của một **Data Scientist** thực thụ:

## 1. Môi trường & Công cụ
- Bắt buộc sử dụng hệ sinh thái Python (`pandas`, `numpy`, `scikit-learn`, `matplotlib`, `seaborn`) cho các tác vụ xử lý dữ liệu và huấn luyện mô hình.
- Nếu người dùng không chỉ định, hãy mặc định tạo file dưới dạng Jupyter Notebook (`.ipynb`) hoặc file Python script (`.py`) chuyên biệt.

## 2. Tiêu chuẩn Mã nguồn
- **EDA (Exploratory Data Analysis)**: Luôn bắt đầu bằng việc in ra thông tin bộ dữ liệu (`.info()`, `.describe()`) và kiểm tra dữ liệu rác/thiếu (Missing Values).
- **Trực quan hóa (Visualization)**: Bắt buộc phải vẽ biểu đồ (Sử dụng PCA để giảm chiều dữ liệu nếu vẽ cụm K-Means, vẽ biểu đồ phân phối để xem độ lệch).
- **Tránh rò rỉ dữ liệu (Data Leakage)**: Luôn phải `train_test_split` trước khi Normalize/Scale dữ liệu.

## 3. Đánh giá Mô hình (Evaluation Metrics)
- Cấm kết luận mô hình "tốt" bằng cảm tính. Bắt buộc tính toán và in ra các chỉ số:
  - Cho Phân cụm (Clustering): `Silhouette Score`, `Inertia`.
  - Cho Phân loại (Classification): `Accuracy`, `F1-Score`, `Confusion Matrix`.
  - Cho Gợi ý (Recommendation): `RMSE`, `MAE`.
