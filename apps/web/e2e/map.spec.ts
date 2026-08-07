import { test, expect } from "@playwright/test";

// Verify /map 3 thứ phiên trước không drive được từ CLI: campus picker, marker cluster, popup "phút tới trường".
test("map renders campus picker, clusters, and route popup", async ({ page }) => {
  await page.goto("/map");

  // Campus picker: 3 nút khu I/II/III, khu II active mặc định (FR-M.3).
  const khu2 = page.getByRole("button", { name: "Khu II", exact: true });
  await expect(khu2).toBeVisible();
  await expect(khu2).toHaveClass(/bg-emerald-600/);

  // Marker cluster: leaflet.markercluster render .marker-cluster khi nhiều tin trùng toạ độ.
  await expect(page.locator(".marker-cluster").first()).toBeVisible({ timeout: 15_000 });

  // Chấm xanh đơn (divIcon, không thuộc cluster) hiện sẵn — leaflet gắn handler lên .leaflet-marker-icon.
  // dispatchEvent thay .click(): một số chấm nằm dưới div campus picker, browser hit-test chặn click
  // thật ("intercepts pointer events"); dispatch bắn event tổng hợp thẳng lên element, listener vẫn fire.
  const marker = page.locator(".leaflet-marker-icon:not(.marker-cluster)").first();
  await expect(marker).toBeVisible({ timeout: 10_000 });
  await marker.dispatchEvent("click");

  // Popup có dòng thời gian di chuyển (hoặc "Chưa có thời gian").
  await expect(page.locator(".leaflet-popup")).toContainText(/phút tới trường|Chưa có thời gian/);
});
