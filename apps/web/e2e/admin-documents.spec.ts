import { expect, test } from "@playwright/test";

for (const width of [390, 1280]) {
  test(`admin reviews documents, updates metadata and suspends a source (${width}px)`, async ({ page }) => {
    await page.setViewportSize({ width, height: 850 });
    await page.goto("/login");
    await page.getByLabel("Email").fill("admin@ctu.edu.vn");
    await page.getByLabel("Mật khẩu").fill("123456");
    await page.getByRole("button", { name: "Đăng nhập" }).click();
    await expect(page).toHaveURL(/\/$/);
    let doc = { id: 42, title: "Nội quy ký túc xá CTU", category: "student_housing", source_path: "ctu/noi-quy.docx",
      document_type: "docx", status: "ready", admin_enabled: true, page_count: 2, chunk_count: 2,
      error_message: null, updated_at: new Date().toISOString() };
    let moreRequested = false;
    await page.route("**/api/admin/documents**", async route => {
      const url = new URL(route.request().url());
      if (route.request().method() === "PATCH") {
        doc = { ...doc, ...route.request().postDataJSON() };
        return route.fulfill({ json: { corpus_schema: "legal_ctu_test", document: doc } });
      }
      if (url.pathname.endsWith("/42")) {
        const offset = Number(url.searchParams.get("offset") || 0);
        moreRequested = moreRequested || offset > 0;
        return route.fulfill({ json: { corpus_schema: "legal_ctu_test", document: doc, has_more: offset === 0,
          chunks: [{ id: offset + 1, heading: offset ? "Quy định sinh hoạt" : "Điều kiện đăng ký", content: offset ? "Sinh viên tuân thủ nội quy ký túc xá." : "Sinh viên đăng ký theo thông báo của trường.", page_from: offset + 1, page_to: offset + 1, quality_warning: null }] } });
      }
      return route.fulfill({ json: { corpus_schema: "legal_ctu_test", items: [doc], total: 1, has_more: false } });
    });
    await page.goto("/admin/documents");
    await expect(page.getByRole("heading", { name: "Tài liệu chatbot", exact: true })).toBeVisible();
    await page.getByRole("button", { name: "Kiểm tra", exact: true }).filter({ visible: true }).click();
    const detail = page.getByRole("region", { name: "Chi tiết tài liệu" });
    await expect(detail.getByText("Sinh viên đăng ký theo thông báo của trường.")).toBeVisible();
    await detail.getByRole("button", { name: "Xem thêm nội dung" }).click();
    await expect(detail.getByText("Sinh viên tuân thủ nội quy ký túc xá.")).toBeVisible();
    expect(moreRequested).toBeTruthy();
    await detail.getByLabel("Tên tài liệu").fill("Nội quy ký túc xá đã kiểm tra");
    await detail.getByRole("button", { name: "Lưu thông tin" }).click();
    await expect(page.getByRole("status")).toContainText("Đã cập nhật tài liệu");
    await detail.getByRole("button", { name: "Tắt sử dụng tài liệu" }).click();
    await expect(detail.getByRole("button", { name: "Bật sử dụng tài liệu" })).toBeVisible();
    await expect(page.getByText("Đã tắt", { exact: true }).filter({ visible: true })).toBeVisible();
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBeTruthy();
    await page.evaluate(() => window.scrollTo(0, 0));
    await page.screenshot({ path: `test-results/admin-documents-${width}.png`, fullPage: true });
    await detail.getByRole("button", { name: "Bật sử dụng tài liệu" }).click();
    await expect(detail.getByRole("button", { name: "Tắt sử dụng tài liệu" })).toBeVisible();
  });
}

test("ordinary users cannot open document administration", async ({ page }) => {
  await page.goto("/login");
  await page.getByLabel("Email").fill("nguyenvana@ctu.edu.vn");
  await page.getByLabel("Mật khẩu").fill("123456");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);
  await page.goto("/admin/documents");
  await expect(page.getByRole("heading", { name: "Không có quyền truy cập" })).toBeVisible();
  await expect(page.getByRole("button", { name: "Kiểm tra", exact: true })).toHaveCount(0);
});
