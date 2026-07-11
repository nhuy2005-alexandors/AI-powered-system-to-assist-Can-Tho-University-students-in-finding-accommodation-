Vì sao
enabled: false — scheduler KHÔNG chạy. crawler_enabled mặc định False, env trong container rỗng. Mọi run trong lịch sử (list trên) đều do tao trigger tay, không phải tự động.

Treo máy giờ → không cào gì hết.

Data lần sau CÓ sạch không? — CÓ, nếu scheduler bật
Cơ chế đã đúng: mỗi _job chạy run_source → run_cleaner tự động. Fix + cleaner 5 tầng nằm trong code, chạy lần nào cũng áp dụng. Chỉ thiếu bật scheduler.

Để treo máy tự cào
Cần 3 thứ:

Bật CRAWLER_ENABLED=true trong docker-compose api env
Máy + Docker Desktop luôn mở (container tắt khi shutdown/sleep máy)
Lịch hiện tại: incremental mỗi 5h + full sweep 3h sáng
Còn 1 rủi ro cần kiểm: cron hour="*/5" — nếu container mới start giữa chừng, job kế mới chạy sau tối đa 5h. Và scheduler dùng in-memory (APScheduler AsyncIO) — restart container = mất job đang chờ, chờ chu kỳ kế.

Muốn tao bật CRAWLER_ENABLED + verify scheduler load job thật (đọc log "Added job") không? Xong đó mày treo máy để yên tâm nó tự cào + tự làm sạch.