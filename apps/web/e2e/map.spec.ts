import { test, expect } from "@playwright/test";

// /map sau khi đổi sang layout 2 cột kiểu Google Maps: panel kết quả trái + map phải.
// Test giữ 4 thứ không kiểm được bằng curl: sidebar có tin, cluster, chọn tin 2 chiều,
// và polyline đường đi (đi qua proxy same-origin /api/listings/[id]/route-path).
test("map renders sidebar results, clusters, and draws route on select", async ({
  page,
}) => {
  await page.goto("/map");

  // Panel trái: header "Kết quả" + dòng đếm "N tin trong X km".
  await expect(page.getByRole("heading", { name: "Kết quả" })).toBeVisible();
  await expect(page.getByText(/\d+ tin trong [\d.]+ km/)).toBeVisible();

  // Campus picker: 3 nút khu I/II/III, khu II active mặc định (FR-M.3).
  const khu2 = page.getByRole("button", { name: "Khu II", exact: true });
  await expect(khu2).toBeVisible();
  await expect(khu2).toHaveClass(/bg-emerald-600/);

  // Có hàng kết quả trong sidebar (mỗi hàng mang data-listing-id).
  const firstRow = page.locator("[data-listing-id]").first();
  await expect(firstRow).toBeVisible({ timeout: 15_000 });

  // Marker cluster: leaflet.markercluster gộp các tin gần nhau.
  await expect(page.locator(".marker-cluster").first()).toBeVisible({
    timeout: 15_000,
  });

  // Chọn tin từ panel → hàng sáng lên + map fetch đường đi và vẽ polyline.
  const routeCall = page.waitForResponse(
    (r) => r.url().includes("/route-path") && r.status() === 200,
    { timeout: 20_000 },
  );
  await firstRow.click();
  await routeCall;

  await expect(firstRow.locator("div.bg-emerald-50")).toBeVisible();
  await expect(page.locator(".leaflet-overlay-pane path").first()).toBeVisible({
    timeout: 10_000,
  });

  // Tin đang chọn hiện link sang trang chi tiết.
  await expect(firstRow.getByRole("link", { name: /Xem chi tiết/ })).toBeVisible();
});
