# Đánh giá Risk và recommendation

Hướng dẫn/báo cáo chatbot đã gộp tại [CHATBOT.md](../docs/CHATBOT.md#verification).

## Risk và recommendation

Risk chỉ được công bố recall/precision khi có JSONL nhãn độc lập:

```json
{"id":"R001","label_source":"manual","is_risky":true,"district_median_price":2100000,"listing":{"title":"...","description":"...","price":900000}}
```

```powershell
& .\.venv\Scripts\python.exe eval\risk_eval.py --dataset path\to\risk_labels.jsonl
```

Recommendation cần relevance judgment theo từng người dùng; `relevance` là gain 0–3 và `recommended_ids` là output đã khóa của hệ thống:

```json
{"user_id":"U001","label_source":"student_survey","recommended_ids":[12,9,31],"relevance":{"12":3,"9":1,"31":0}}
```

```powershell
& .\.venv\Scripts\python.exe eval\recommendation_eval.py --dataset path\to\recommendation_labels.jsonl --k 10
```

Runner chủ động từ chối `label_source=synthetic`. Với risk, dữ liệu giả sinh từ chính các rule sẽ gây đánh giá vòng tròn. Với recommendation, lượt tương tác dùng để tạo hồ sơ phải tách theo thời gian khỏi lượt tương tác dùng làm test.


## 6. Nguồn nghiên cứu chính

1. Es et al. (2024), *RAGAS: Automated Evaluation of Retrieval Augmented Generation*, EACL Demo, DOI [10.18653/v1/2024.eacl-demo.16](https://aclanthology.org/2024.eacl-demo.16/).
2. Saad-Falcon et al. (2024), *ARES: An Automated Evaluation Framework for Retrieval-Augmented Generation Systems*, NAACL, DOI [10.18653/v1/2024.naacl-long.20](https://aclanthology.org/2024.naacl-long.20/).
3. Lewis et al. (2020), *Retrieval-Augmented Generation for Knowledge-Intensive NLP Tasks*, [NeurIPS 2020](https://papers.neurips.cc/paper/2020/hash/6b493230205f780e1bc26945df7481e5-Abstract.html).
4. Järvelin & Kekäläinen (2002), *Cumulated gain-based evaluation of IR techniques*, DOI [10.1145/582415.582418](https://doi.org/10.1145/582415.582418).
5. Hu, Koren & Volinsky (2008), *Collaborative Filtering for Implicit Feedback Datasets*, DOI [10.1109/ICDM.2008.22](https://doi.org/10.1109/ICDM.2008.22).
6. Liu, Ting & Zhou (2008), *Isolation Forest*, [IEEE ICDM 2008](https://doi.org/10.1109/ICDM.2008.17).
7. NIST (2024), *AI RMF: Generative AI Profile*, DOI [10.6028/NIST.AI.600-1](https://doi.org/10.6028/NIST.AI.600-1).
