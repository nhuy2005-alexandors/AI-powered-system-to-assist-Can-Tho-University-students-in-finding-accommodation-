# Tích hợp Risk vào hệ thống Trọ CTU

Phần chatbot đã gộp tại [CHATBOT.md](CHATBOT.md). Tài liệu này giữ phần Risk; vận hành hệ thống chung xem [LOCAL_DEPLOYMENT.md](LOCAL_DEPLOYMENT.md).

Risk được chấm khi tạo/sửa tin; score, trạng thái và lý do dùng cho card, bản đồ và trang chi tiết. UGC mức suspicious chuyển flagged để admin duyệt.

## Kiểm tra risk

Xem trước risk của một tin, không ghi DB:

```powershell
Invoke-RestMethod http://localhost:8000/risk/listings/1
```

Chấm và lưu một tin hoặc batch cần token admin:

```text
POST /risk/listings/{listing_id}/assess
POST /risk/assess-pending?limit=1000
Authorization: Bearer <admin-access-token>
```

Admin có thêm lịch sử/override có audit trail:

```text
GET /risk/listings/{listing_id}/history
PUT /risk/listings/{listing_id}/override
```

Khi `RISK_AUTO_ASSESS=true`, thao tác tạo/sửa tin và crawler đã tự chạy risk; không cần gọi batch thường xuyên.
