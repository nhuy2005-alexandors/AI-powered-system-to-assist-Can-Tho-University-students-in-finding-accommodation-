import { test, expect, type Page } from "@playwright/test";

async function login(page: Page, email: string) {
  await page.goto("/login");
  await page.getByLabel("Email").fill(email);
  await page.getByLabel("Mật khẩu").fill("123456");
  await page.getByRole("button", { name: "Đăng nhập" }).click();
  await expect(page).toHaveURL(/\/$/);
}

test("stale auth cookies do not trap guests on the home page", async ({ page }) => {
  await page.context().addCookies([
    { name: "access_token", value: "expired-access-token", url: "http://localhost:3000" },
    { name: "refresh_token", value: "expired-refresh-token", url: "http://localhost:3000" },
  ]);

  await page.goto("/");
  await page.getByRole("link", { name: "Đăng nhập", exact: true }).click();
  await expect(page).toHaveURL(/\/login$/);
  await expect(page.getByRole("heading", { name: "Đăng nhập" })).toBeVisible();
});

test("user logs in to the main page and account page has useful navigation", async ({ page }) => {
  await login(page, "nguyenvana@ctu.edu.vn");
  await expect(page.getByRole("link", { name: /Nguyễn Văn A/ })).toBeVisible();

  await page.goto("/me");
  await expect(page.getByRole("heading", { name: /Xin chào, Nguyễn Văn A/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Về trang tìm trọ/ })).toBeVisible();
  await expect(page.locator("main").getByRole("link", { name: /Tin của tôi/ })).toBeVisible();
  await expect(page.getByRole("link", { name: /Đăng tin mới/ })).toBeVisible();
});

test("admin shell keeps its sidebar while navigating management pages", async ({ page }) => {
  await login(page, "admin@ctu.edu.vn");
  await page.goto("/admin");

  const sidebar = page.locator("aside");
  await expect(sidebar.getByText("Trọ CTU Admin")).toBeVisible();
  await expect(page.getByRole("heading", { name: "Dashboard quản trị" })).toBeVisible();
  await expect(page.getByText("Tổng bài tin", { exact: true })).toBeVisible();
  await expect(page.getByText("Người dùng", { exact: true }).first()).toBeVisible();

  await sidebar.getByRole("link", { name: /Báo cáo tin/ }).click();
  await expect(page).toHaveURL(/\/admin\/reports/);
  await expect(page.getByRole("heading", { name: "Kiểm duyệt báo cáo tin" })).toBeVisible();
  await expect(sidebar.getByText("Trọ CTU Admin")).toBeVisible();

  await sidebar.getByRole("link", { name: /Quản lý bài tin/ }).click();
  await expect(page).toHaveURL(/\/admin\/listings/);
  await expect(page.getByRole("heading", { name: "Quản lý bài tin phòng trọ" })).toBeVisible();

  await sidebar.getByRole("link", { name: /Người dùng/ }).click();
  await expect(page).toHaveURL(/\/admin\/users/);
  await expect(page.getByRole("heading", { name: "Quản lý người dùng" })).toBeVisible();
});
