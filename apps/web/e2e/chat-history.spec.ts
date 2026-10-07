import { expect, test } from "@playwright/test";

const id = "aa8a6384-42f3-4edc-a99f-a1e523596c90";
const question = "Phí ở KTX CTU bao nhiêu một tháng?";
const answer = "Phí KTX theo khung công bố của CTU [1].";

for (const width of [390, 1280]) {
  test(`saved history survives reload, repeat, new chat and deletion (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    let turns: { id: number; question: string; response: Record<string, unknown>; created_at: string }[] = [];
    const seenIds: (string | null)[] = [];
    await page.route("**/api/chat/conversations**", async route => {
      const url = new URL(route.request().url());
      if (route.request().method() === "DELETE") {
        turns = [];
        return route.fulfill({ status: 204 });
      }
      if (url.pathname.endsWith(id)) {
        return route.fulfill({ json: { id, title: question, turns, has_more: false } });
      }
      return route.fulfill({ json: { items: turns.length ? [{ id, title: question, updated_at: new Date().toISOString(), turn_count: turns.length }] : [], has_more: false } });
    });
    await page.route("**/api/chat/ask", async route => {
      const body = route.request().postDataJSON();
      seenIds.push(body.conversation_id ?? null);
      const result = { answer, conversation_id: id, turn_id: turns.length + 1, reused_answer: turns.length > 0,
        listings: [], sources: [{ kind: "legal_document", rank: 1, title: "Nguồn KTX CTU", heading: "Phí ở", excerpt: "Nguồn công bố của CTU" }],
        degraded: false, generation_provider: "gemini-agent", event_id: null };
      turns.push({ id: turns.length + 1, question: body.message, response: result, created_at: new Date().toISOString() });
      return route.fulfill({ json: result });
    });
    await page.goto("/login");
    await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
    const input = page.getByPlaceholder("Tìm trọ hoặc hỏi quy định pháp luật...");
    await input.fill(question);
    await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
    await expect(page.getByTestId("chat-answer").last()).toContainText("Phí KTX theo khung");
    await page.reload();
    await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
    await expect(page.getByTestId("chat-answer").last()).toContainText("Phí KTX theo khung");
    await page.getByRole("button", { name: "Xem nguồn 1" }).click();
    await expect(page.getByText("[1] Nguồn KTX CTU")).toBeVisible();
    await input.fill(question);
    await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
    await expect(page.getByText("Đã dùng lại câu trả lời đã lưu.")).toBeVisible();
    expect(seenIds).toEqual([null, id]);
    await page.getByTitle("Cuộc trò chuyện mới").click();
    await expect(page.getByTestId("chat-answer")).toHaveCount(1);
    await page.getByRole("button", { name: "Lịch sử trò chuyện" }).click();
    await expect(page.getByText("Lịch sử của bạn")).toBeVisible();
    await expect(page.getByText("2 câu hỏi", { exact: false })).toBeVisible();
    await page.screenshot({ path: `test-results/chat-history-list-${width}.png` });
    await page.getByRole("button", { name: new RegExp(`^${question.replace(/[?]/g, "\\?")}`) }).click();
    await expect(page.getByTestId("chat-answer")).toHaveCount(3);
    await page.getByRole("button", { name: "Lịch sử trò chuyện" }).click();
    await page.getByRole("button", { name: `Xóa cuộc trò chuyện: ${question}` }).click();
    await expect(page.getByTestId("chat-answer")).toHaveCount(1);
    await page.getByRole("button", { name: "Lịch sử trò chuyện" }).click();
    await expect(page.getByText("Chưa có cuộc trò chuyện đã lưu.")).toBeVisible();
    const widget = page.getByRole("region", { name: "Trợ lý tìm nhà trọ CTU" });
    expect(await widget.evaluate(el => el.scrollWidth <= el.clientWidth)).toBeTruthy();
    await page.screenshot({ path: `test-results/chat-history-${width}.png` });
  });
}

test("history authentication failure is visible and does not expose saved messages", async ({ page }) => {
  await page.route("**/api/chat/conversations**", route => route.fulfill({ status: 401, json: { detail: "Chưa đăng nhập" } }));
  await page.goto("/login");
  await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
  await page.getByRole("button", { name: "Lịch sử trò chuyện" }).click();
  await expect(page.getByRole("region", { name: "Trợ lý tìm nhà trọ CTU" }).getByRole("alert")).toHaveText("Chưa đăng nhập");
  await expect(page.getByText("Lịch sử của bạn")).toBeVisible();
});
