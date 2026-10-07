import { expect, test } from "@playwright/test";

test("legacy degraded response displays its limitation warning", async ({ page }) => {
  let calls = 0;
  await page.route("**/api/chat/ask", route => route.fulfill({ json: {
    answer: "Kiểm tra giá thuê, tiền cọc và kỳ thanh toán trong hợp đồng [1].",
    sources: [], listings: [], degraded: ++calls > 1, generation_provider: "gemini-agent",
  }}));
  await page.goto("/login");
  await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
  const input = page.getByPlaceholder("Tìm trọ hoặc hỏi quy định pháp luật...");
  await input.fill("Hợp đồng thuê trọ cần ghi gì?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByText("Câu trả lời còn giới hạn; hãy đọc lưu ý và đối chiếu nguồn.")).toHaveCount(0);
  await input.fill("Tiền cọc cần điều kiện nào?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByText("Câu trả lời còn giới hạn; hãy đọc lưu ý và đối chiếu nguồn.")).toBeVisible();
});

const source = { kind: "legal_document", rank: 1, title: "Văn bản kiểm thử", heading: "Điều 3", page_from: 4, page_to: 5, excerpt: "Trích đoạn kiểm thử, chỉ mở khi yêu cầu." };

test("Word notices and model labels are hidden while answers, gaps, follow-ups and citations remain", async ({ page }) => {
  const notice = "Nguồn là bản Word/trích tuyển được cung cấp, chưa xác minh toàn bộ câu chữ với bản chính thức; không coi ghi chú biên tập là quy định pháp luật.";
  const followUp = "Hợp đồng hiện tại có điều khoản quy định về thời hạn thanh toán chưa?";
  const gap = "Chưa có nguồn cho điều kiện hoàn tiền cọc.";
  let calls = 0;
  await page.route("**/api/chat/ask", (route) => route.fulfill({ json: {
    answer: ["Kiểm tra các điều khoản trước khi ký hợp đồng [1].", "- Đọc giá thuê và ngày thanh toán [1].", gap,
      "Nguồn cung cấp trích dẫn từ bản Word chưa đối chiếu toàn văn chính thức [1].",
      "Nguồn quy định về hợp đồng nhà ở trích từ bản Word cung cấp chưa được đối chiếu toàn văn với văn bản chính thức [1].",
      "Chưa đủ căn cứ từ các đoạn này để kết luận toàn bộ yêu cầu hoặc tình huống riêng.",
      "Cần đối chiếu điều/khoản được dẫn chiếu còn thiếu; đoạn trích chưa đủ để kết luận toàn bộ điều kiện và ngoại lệ.",
      notice, "Để áp dụng vào trường hợp của bạn:", `- ${followUp}`,
      "Thông tin tham khảo từ nguồn, cần đối chiếu điều kiện áp dụng và hiệu lực."].join("\n\n"),
    listings: [], sources: [source], degraded: false, generation_provider: "gemini-agent",
    agent_trace: [{ agent: "evidence_selection", provider: ++calls === 1 ? "qwen-local" : "gemini", status: "complete" }],
  } }));
  await page.goto("/login");
  await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
  const input = page.getByPlaceholder("Tìm trọ hoặc hỏi quy định pháp luật...");
  await input.fill("Trước khi ký hợp đồng thuê trọ, sinh viên nên kiểm tra những điều khoản nào?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  const answer = page.getByTestId("chat-answer").last();
  await expect(answer).toContainText("Đọc giá thuê và ngày thanh toán");
  const expand = page.getByRole("button", { name: "Xem toàn bộ câu trả lời" });
  if (await expand.isVisible()) await expand.click();
  await expect(answer).toContainText(gap);
  await expect(answer).not.toContainText(notice);
  await expect(answer).not.toContainText("bản Word");
  await expect(answer).toContainText("Chưa đủ căn cứ từ các đoạn này");
  await expect(answer).toContainText("Để áp dụng vào trường hợp của bạn");
  await expect(answer).toContainText(followUp);
  await expect(answer).toContainText("Thông tin tham khảo từ nguồn");
  await expect(page.getByText(/^AI:/)).toHaveCount(0);
  await answer.getByRole("button", { name: "Xem nguồn 1" }).first().click();
  await expect(page.getByText("[1] Văn bản kiểm thử")).toBeVisible();
  await expect(page.getByText("Lưu ý về nguồn", { exact: true })).toHaveCount(0);
  await expect(page.getByText(notice, { exact: true })).toHaveCount(0);
  // The same presentation applies regardless of the evidence selector.
  await input.fill("Hợp đồng hiện tại của tôi có được tăng giá thuê không?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByTestId("chat-answer")).toHaveCount(3);
  if (await expand.isVisible()) await expand.click();
  await expect(page.getByTestId("chat-answer").last()).toContainText(followUp);
  await expect(page.getByTestId("chat-answer").last()).not.toContainText("bản Word");
  await expect(page.getByText(/^AI:/)).toHaveCount(0);
});

for (const width of [390, 1280]) {
  test(`chat concise answer, expandable sources and safe rendering (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 800 });
    await page.route("**/api/chat/ask", (route) => route.fulfill({ json: {
      answer: "**Kiểm tra hợp đồng trước khi đặt cọc.**\n- **Đọc điều kiện thuê [1]**.\n- *Đối chiếu nguồn*.\n<img src=x onerror=alert(1)>",
      listings: [], sources: [source], degraded: true, generation_provider: "template",
    } }));
    await page.goto("/login");
    await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
    const widget = page.getByRole("region", { name: "Trợ lý tìm nhà trọ CTU" });
    await widget.getByPlaceholder("Tìm trọ hoặc hỏi quy định pháp luật...").fill("Quy định đặt cọc thuê trọ?");
    await widget.getByRole("button", { name: "Gửi câu hỏi" }).click();
    await expect(widget.locator("strong").first()).toHaveText("Kiểm tra hợp đồng trước khi đặt cọc.");
    await expect(widget.locator("em")).toHaveText("Đối chiếu nguồn");
    await expect(widget.locator("li")).toHaveCount(2);
    await expect(widget.getByText(source.title, { exact: false })).not.toBeVisible();
    await widget.getByRole("button", { name: "Xem nguồn 1" }).click();
    await expect(widget.getByText("[1] Văn bản kiểm thử")).toBeVisible();
    await expect(widget.getByText(source.excerpt)).not.toBeVisible();
    await widget.getByText("Đọc trích đoạn", { exact: true }).click();
    await expect(widget.getByText(source.excerpt)).toBeVisible();
    await expect(widget.locator("img")).toHaveCount(0);
    await expect(widget.getByText(/Vector chưa sẵn sàng/)).toHaveCount(0);
    await expect(widget.getByRole("heading", { name: "Trợ lý Trọ CTU" })).toBeVisible();
    expect(await widget.evaluate((el) => el.scrollWidth <= el.clientWidth)).toBeTruthy();
    await page.screenshot({ path: `test-results/chat-${width}.png` });
    await widget.getByTitle("Phóng to").click();
    await expect(widget.getByTitle("Thu nhỏ")).toBeVisible();
  });
}

test("long answers remain available and follow-up history fits API limit", async ({ page }) => {
  const answer = "Thông tin tham khảo.\n" + "- Nội dung kiểm thử dài, cần đọc đầy đủ trước khi quyết định.\n".repeat(50) + "KẾT THÚC [1]";
  let calls = 0;
  await page.route("**/api/chat/ask", (route) => {
    const body = route.request().postDataJSON();
    if (++calls === 2) expect(body.conversation_history.every((turn: { content: string }) => turn.content.length <= 2000)).toBeTruthy();
    return route.fulfill({ json: { answer, listings: [], sources: [source], degraded: false, generation_provider: "qwen-local", generation_model: "qwen3.5:4b" } });
  });
  await page.goto("/login");
  await page.getByRole("button", { name: "Mở Trợ lý Trọ CTU" }).click();
  const input = page.getByPlaceholder("Tìm trọ hoặc hỏi quy định pháp luật...");
  await input.fill("Quy định hợp đồng thuê trọ?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByText("KẾT THÚC", { exact: false })).not.toBeVisible();
  expect((await page.getByTestId("chat-answer").last().innerText()).length).toBeLessThan(450);
  await page.getByRole("button", { name: "Xem toàn bộ câu trả lời" }).click();
  await expect(page.getByText("KẾT THÚC", { exact: false })).toBeVisible();
  await page.getByRole("button", { name: "Thu gọn câu trả lời" }).click();
  await input.fill("Còn tiền điện thì sao?");
  await page.getByRole("button", { name: "Gửi câu hỏi" }).click();
  await expect(page.getByRole("button", { name: "Xem toàn bộ câu trả lời" })).toHaveCount(2);
  expect(calls).toBe(2);
});
