# 📊 NCKH/eval — Đánh giá thực nghiệm

Notebook + script đo metric cho báo cáo nghiệm thu (THS2026-66).

## Cấu trúc
```
eval/
├── data/            # ground-truth: listings, scam labels, user-mock, Q&A test
├── notebooks/       # notebook eval từng module
└── metrics.py       # hàm metric dùng chung (P@K, NDCG, ILS)
```

## Mapping notebook → metric → ngưỡng

| Notebook | Module | Metric | Ngưỡng đạt |
|---|---|---|---|
| `01_recommendation_eval.ipynb` | Recommendation | Precision@10, NDCG@10, ILS | ≥0.6 / ≥0.65 / ≤0.7 |
| `02_dedup_eval.ipynb` | Dedup | recall, false-merge | ≥90% / ≤5% |
| `03_geocoding_eval.ipynb` | Geocoding | %confidence≥medium, sai >1km | ≥80% / 0 trên 50 mẫu |
| `04_risk_eval.ipynb` | Risk | recall scam | ≥85% |
| `05_rag_eval.ipynb` | Chatbot RAG | Faithfulness, AnsRel (RAGAS) | ≥0.7 / ≥0.75 |
| `06_roommate_eval.ipynb` | Matching | MAE feedback 2 tuần | ≤1.5/5 |

## Dataset cần chuẩn bị (Sprint 0–1)

| File | Mô tả | Kích thước tối thiểu |
|---|---|---|
| `data/listings_groundtruth.json` | Listing đã verify thủ công | 100 |
| `data/scam_labels.csv` | Tin gán nhãn scam/clean | 100 (≥30 scam) |
| `data/dup_pairs.csv` | Cặp trùng/không trùng | 200 cặp |
| `data/user_mock.json` | User-mock + relevance phòng | 30 user |
| `data/qa_test.json` | Câu hỏi + answer kỳ vọng | 50 Q&A |

## Chạy
```bash
cd NCKH/eval
pip install -r requirements.txt
jupyter lab notebooks/
```
