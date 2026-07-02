# CLAUDE.md — Omni Assistant

## Subagent Orchestration (BẮT BUỘC — token economy)

Khi model chính là **Opus**, áp dụng mô hình orchestrator → executor → review:

**Opus (main) = orchestrator + reviewer.** Giữ cho mình:
- Đọc plan, phân rã task
- Quyết định kiến trúc, security, business logic phức tạp
- Review diff/summary của subagent (đọc thay đổi THẬT, không tin lời tóm tắt)
- Quyết bước kế tiếp

**Sonnet subagent = executor.** Delegate qua `Agent` tool với `model: sonnet` cho việc TỐN TOKEN:
- Đọc/quét nhiều file (recon, tìm symbol, map codebase)
- Code cơ học rõ ràng: boilerplate, CRUD, viết test, refactor đơn giản, rename
- Chạy build/test và tóm kết quả
- Việc song song độc lập → nhiều subagent cùng lúc (1 message, nhiều Agent call)

### Quy tắc delegate

1. **Prompt subagent phải TỰ CHỨA** — nó không thấy hội thoại này. Nhồi đủ context: file path, dòng, spec cụ thể, kết quả mong đợi.
2. **Trust but verify** — subagent báo "xong" ≠ đúng. Opus PHẢI đọc diff thật trước khi báo sếp hoàn thành.
3. **KHÔNG delegate** khi: việc nhỏ (sửa1-2 dòng — Opus tự làm nhanh hơn), quyết định kiến trúc, hoặc việc cần full ngữ cảnh hội thoại mà không nhồi hết vào prompt được.
4. **LUÔN dùng `model: sonnet`, TUYỆT ĐỐI KHÔNG `haiku`** — subagent mặc định kế thừa model main (Opus). Không chỉ định = vẫn Opus = không tiết kiệm. LƯU Ý: trong setup này `haiku` bị map thành Opus 4.7 (đắt) qua proxy — chỉ `sonnet` mới thật rẻ.

### Cách sếp ép delegate chắc chắn

- Prompt mơ hồ → Opus không chia được → tự làm hết. Muốn chắc, prompt rõ: nêu plan/spec, tách task, hoặc nói thẳng "delegate code cho Sonnet subagent, mày review".
- Cần deterministic 100% (không phụ thuộc Opus tự judge) → dùng Workflow script định sẵn stage nào Sonnet, stage nào Opus.

### Vòng lặp chuẩn

```
Opus: đọc plan → chia task tự-chứa
  ├─ Agent(sonnet): "đọc + tóm module X"        → summary
  ├─ Agent(sonnet): "impl file Y theo spec Z"   → diff
Opus: đọc diff thật → review → quyết bước kế
  └─ Agent(sonnet): "viết test + chạy"          → kết quả
Opus: verify diff → báo sếp
```

Mục tiêu: giảm ~60% token Opus vs Opus-solo. Rác (5000 dòng code đọc) chết trong context subagent, main chỉ nuốt summary.
