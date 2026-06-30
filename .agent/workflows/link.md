---
name: link
description: Tự động kết nối một dự án vệ tinh với não bộ Omni Assistant
---

# Lệnh /link

Lệnh này dùng để tự động thiết lập cầu nối (Brain-Limb) giữa một dự án độc lập nằm ở thư mục khác và hệ thống trung tâm Omni Assistant.

## Chức năng
1. Sinh file `.mcp.json` tại dự án đích trỏ về Omni Assistant.
2. Copy `GEMINI.md` để đồng bộ luật lệ.
3. Tạo `task.md` theo chuẩn.
4. Tạo cấu trúc cờ hiệu `.agent/state/`.

## Cách sử dụng

```bash
/link <Đường_dẫn_tuyệt_đối_đến_dự_án>
```

Ví dụ:
```bash
/link D:\Dev\Workspaces\SaaS_Project
```

## Cách thực thi (Dành cho Gemini)
Khi người dùng gọi lệnh `/link`, bạn cần chạy:
`node .agent/scripts/link-project.js "<Đường_dẫn_tuyệt_đối>"`
