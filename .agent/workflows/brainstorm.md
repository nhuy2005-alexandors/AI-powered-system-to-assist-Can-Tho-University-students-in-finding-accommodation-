---
description: Bí ý tưởng? Dùng cái này để AI gợi ý theo chuẩn Senior.
---

# /brainstorm - Structured Strategic Exploration

$ARGUMENTS

---

## 🟢 PHASE 1: Domain Discovery & Idea Analysis
**Agent**: `orchestrator` hoặc `orchestrator`
**Mission**: Hiểu rõ giới hạn của bài toán và phân tích sâu ý tưởng.
- **Action 1**: Phân tích ý tưởng của người dùng (tính khả thi, đối tượng mục tiêu, thách thức kỹ thuật, và bối cảnh).
- **Action 2**: Scan các file liên quan để lấy ngữ cảnh thực tế của dự án.
- **Artifact**: Trình bày báo cáo phân tích ngắn gọn cho người dùng **trước khi** đề xuất các hướng đi ở Phase 2.

## 🟡 PHASE 2: Multi-Option Generation
**Agent**: `orchestrator` or specific specialist
**Mission**: Divergent thinking.
- **Action**: Provide at least 3 distinct approaches:
  - **Option A**: Conservative/Safe.
  - **Option B**: Modern/Aggressive.
  - **Option C**: Creative/Out-of-the-box.
- **Artifact**: Create a comparison table with Pros, Cons, and Effort.

## 🔵 PHASE 3: Competitive Analysis & Recommendation
**Agent**: `orchestrator`
**Mission**: Convergent thinking.
- **Action**: Analyze tradeoffs against the original goal.
- **Action**: State a professional recommendation with clear rationale.

## 🔴 PHASE 4: Strategic Handoff
**Agent**: `orchestrator`
**Mission**: Prepare for action.
- **Action**: Ask the user which path to take.
- **Transition**: Ready to trigger `/plan` based on selection.

---

## Brainstorming Rules:
- **No Code**: Focus on architecture and logic.
- **Honest Tradeoffs**: Don't hide complexity.
- **User-Centric**: Tailor solutions to the user's specific context.

---

## Examples:
- `/brainstorm state management strategy`
- `/brainstorm database schema for social media`
- `/brainstorm UI design system for mobile`
