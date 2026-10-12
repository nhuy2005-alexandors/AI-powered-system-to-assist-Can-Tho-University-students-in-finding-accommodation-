/* Real-catalog browser check. It never supplies or intercepts catalog data. */
"use strict";

const crypto = require("node:crypto");
const fs = require("node:fs");

const EXPECTED_UI_ORIGIN = "http://127.0.0.1:3032";
const EXPECTED_API_ORIGIN = "http://127.0.0.1:8032";
const ACCEPTANCE_EVIDENCE = "REAL_POSTGRES_REAL_CATALOG";

function validateExpectedEnvelope(envelope) {
  const expectedKeys = [
    "canonical_public_json",
    "operation_id",
    "public_dto_sha256",
    "schema_version",
  ];
  if (
    envelope === null ||
    typeof envelope !== "object" ||
    Array.isArray(envelope) ||
    JSON.stringify(Object.keys(envelope).sort()) !== JSON.stringify(expectedKeys)
  ) {
    throw new Error("Invalid expected data envelope");
  }
  if (
    envelope.schema_version !== 1 ||
    typeof envelope.operation_id !== "string" ||
    !/^[0-9a-f]{8}-[0-9a-f]{4}-[1-8][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/.test(envelope.operation_id) ||
    typeof envelope.public_dto_sha256 !== "string" ||
    !/^[0-9a-f]{64}$/.test(envelope.public_dto_sha256) ||
    typeof envelope.canonical_public_json !== "string"
  ) {
    throw new Error("Invalid expected data envelope");
  }

  const digest = crypto
    .createHash("sha256")
    .update(Buffer.from(envelope.canonical_public_json, "utf8"))
    .digest("hex");
  if (digest !== envelope.public_dto_sha256) {
    throw new Error("Expected data digest mismatch");
  }

  const rows = JSON.parse(envelope.canonical_public_json);
  if (!Array.isArray(rows) || rows.length !== 789) {
    throw new Error("Expected data row count mismatch");
  }
  let previousId = 0;
  for (const row of rows) {
    if (
      row === null ||
      typeof row !== "object" ||
      !Number.isSafeInteger(row.id) ||
      row.id <= previousId ||
      typeof row.title !== "string"
    ) {
      throw new Error("Expected data membership mismatch");
    }
    previousId = row.id;
  }
  return rows;
}

function normalizeSpace(value) {
  return String(value ?? "").replace(/\s+/g, " ").trim();
}

function isPartial(row) {
  return (
    row.description_is_partial === true ||
    String(row.description_state ?? "").toUpperCase() === "PARTIAL" ||
    String(row.description_completeness ?? "").toUpperCase() === "PARTIAL"
  );
}

function isWithheld(row) {
  return (
    (row.description === null || row.description === "") &&
    String(row.description_state ?? '').toUpperCase() === 'WITHHELD_UNSAFE_CONTACT'
  );
}

function validateRenderedCards(expectedRows, cards) {
  if (cards.length !== 789 || expectedRows.length !== 789) throw Error('Card count mismatch');
  const ids = [];
  for (let i = 0; i < expectedRows.length; i++) {
    const row = expectedRows[i], card = cards[i];
    const area = (row.area == null ? 'Diện tích chưa rõ' : `${row.area} m²`) +
                 (row.district ? ` · ${row.district}` : '');
    if (card.id !== row.id || normalizeSpace(card.title) !== normalizeSpace(row.title) ||
        normalizeSpace(card.area) !== normalizeSpace(area)) throw Error('Card field mismatch');
    ids.push(card.id);
  }
  if (new Set(ids).size !== 789) throw Error('Duplicate card IDs');
  return ids;
}

function validateDescriptionEvidence(row, evidence, withheld = false) {
  if (withheld ? !isWithheld(row) : !isPartial(row) || !row.description)
    throw Error('Description representative mismatch');
  const description = row.description || 'Tin đăng chưa có mô tả.';
  if (!normalizeSpace(evidence.detailText).includes('Mô tả chưa đầy đủ') ||
      !evidence.paragraphs.map(normalizeSpace).includes(normalizeSpace(description)))
    throw Error('Description rendering mismatch');
}

function displaySafeHttpUrl(value) {
  if (typeof value !== "string" || value.length === 0) return null;
  try {
    const url = new URL(value);
    return url.protocol === "http:" || url.protocol === "https:" ? url.toString() : null;
  } catch {
    return null;
  }
}

function credentialFreeHttpUrl(value) {
  const safeUrl = displaySafeHttpUrl(value);
  if (!safeUrl) return null;
  const url = new URL(safeUrl);
  return url.username || url.password ? null : safeUrl;
}

function hasSafeContact(row) {
  return displaySafeHttpUrl(row.source_contact_url) !== null;
}

async function uniqueOptionalHref(locator) {
  if (locator === null || typeof locator?.count !== "function" ||
      typeof locator?.getAttribute !== "function") {
    throw Error("Invalid link locator");
  }
  const count = await locator.count();
  if (!Number.isSafeInteger(count) || count < 0) throw Error("Invalid link count");
  if (count === 0) return null;
  if (count !== 1) throw Error("Ambiguous link evidence");
  return await locator.getAttribute("href");
}

function binary64BitsHex(value) {
  if (typeof value !== "number" || !Number.isFinite(value)) {
    throw Error("Invalid cluster coordinate");
  }
  const normalized = Object.is(value, -0) ? 0 : value;
  const buffer = new ArrayBuffer(8);
  new DataView(buffer).setFloat64(0, normalized, false);
  return Array.from(new Uint8Array(buffer), (byte) => byte.toString(16).padStart(2, "0")).join("");
}

function validCoordinatePair(lat, lng) {
  return typeof lat === "number" && Number.isFinite(lat) && lat >= -90 && lat <= 90 &&
    typeof lng === "number" && Number.isFinite(lng) && lng >= -180 && lng <= 180;
}

function validateClusterSnapshot(expectedRows, snapshot) {
  if (!Array.isArray(expectedRows) || expectedRows.length !== 789 ||
      snapshot === null || typeof snapshot !== "object" || Array.isArray(snapshot) ||
      JSON.stringify(Object.keys(snapshot).sort()) !== JSON.stringify(["generation", "members", "state"])) {
    throw Error("Invalid listing layer snapshot");
  }
  if (!Number.isSafeInteger(snapshot.generation) || snapshot.generation < 0 || snapshot.state !== "READY" ||
      !Array.isArray(snapshot.members) || snapshot.members.length !== 787) {
    throw Error("Invalid listing layer snapshot");
  }

  const expectedMembers = [];
  for (const row of expectedRows) {
    if (row === null || typeof row !== "object" || Array.isArray(row) ||
        !Number.isSafeInteger(row.id) || row.id <= 0 || !Object.hasOwn(row, "position")) {
      throw Error("Invalid expected listing membership");
    }
    if (row.position === null) continue;
    const position = row.position;
    if (position === null || typeof position !== "object" || Array.isArray(position) ||
        !validCoordinatePair(position.lat, position.lng)) {
      throw Error("Invalid expected listing position");
    }
    expectedMembers.push({ id: row.id, lat: position.lat, lng: position.lng });
  }
  if (expectedMembers.length !== 787) throw Error("Expected positioned listing count mismatch");

  const seen = new Set();
  const actualMembers = snapshot.members.map((member) => {
    if (member === null || typeof member !== "object" || Array.isArray(member) ||
        JSON.stringify(Object.keys(member).sort()) !== JSON.stringify(["id", "lat", "lng"]) ||
        !Number.isSafeInteger(member.id) || member.id <= 0 || !validCoordinatePair(member.lat, member.lng) ||
        seen.has(member.id)) {
      throw Error("Invalid actual listing member");
    }
    seen.add(member.id);
    return { id: member.id, lat: member.lat, lng: member.lng };
  });

  expectedMembers.sort((left, right) => left.id - right.id);
  actualMembers.sort((left, right) => left.id - right.id);
  for (let index = 0; index < expectedMembers.length; index += 1) {
    const expected = expectedMembers[index];
    const actual = actualMembers[index];
    if (actual.id !== expected.id || actual.lat !== expected.lat || actual.lng !== expected.lng) {
      throw Error("Actual listing membership mismatch");
    }
  }

  const triples = actualMembers.map((member) => [
    member.id,
    binary64BitsHex(member.lat),
    binary64BitsHex(member.lng),
  ]);
  const digest = crypto.createHash("sha256").update(Buffer.from(JSON.stringify(triples), "utf8")).digest("hex");
  return {
    positioned_listing_count: actualMembers.length,
    actual_positioned_members_sha256: digest,
  };
}

async function verifyMountedClusterSnapshot(page, expectedRows) {
  if (page === null || typeof page?.getByTestId !== "function") throw Error("Browser map is unavailable");
  const mapContainer = page.getByTestId("mobility-map");
  let snapshot = null;
  for (let attempt = 0; attempt < 50; attempt += 1) {
    snapshot = await mapContainer.evaluate((container) => {
      let current = null;
      container.dispatchEvent(new CustomEvent("mobility:listing-layer-snapshot", {
        detail: { respond: (value) => { current = value; } },
      }));
      return current;
    });
    if (snapshot?.state === "READY") break;
    await new Promise((resolve) => setTimeout(resolve, 50));
  }
  return validateClusterSnapshot(expectedRows, snapshot);
}

function validateId980Evidence(expectedRows, evidence) {
  const candidates = Array.isArray(expectedRows) ? expectedRows.filter((row) => row?.id === 980) : [];
  if (candidates.length !== 1 || evidence === null || typeof evidence !== "object" || Array.isArray(evidence) ||
      JSON.stringify(Object.keys(evidence).sort()) !== JSON.stringify([
        "ariaPressed", "contactLinkHref", "detailText", "id", "paragraphs", "sourceLinkHref", "title",
      ])) {
    throw Error("ID 980 evidence mismatch");
  }
  const row = candidates[0];
  if (!isWithheld(row) || row.description_is_partial !== true || evidence.id !== 980 ||
      evidence.ariaPressed !== true || normalizeSpace(evidence.title) !== normalizeSpace(row.title)) {
    throw Error("ID 980 source row mismatch");
  }
  const fallback = "Tin đăng chưa có mô tả.";
  if (typeof evidence.detailText !== "string" ||
      !normalizeSpace(evidence.detailText).includes("Mô tả chưa đầy đủ") ||
      !Array.isArray(evidence.paragraphs) ||
      !evidence.paragraphs.map(normalizeSpace).includes(fallback)) {
    throw Error("ID 980 withheld rendering mismatch");
  }
  const sourceHref = credentialFreeHttpUrl(row.source_url);
  if (!sourceHref || evidence.sourceLinkHref !== sourceHref) throw Error("ID 980 source link mismatch");
  const contactHref = displaySafeHttpUrl(row.source_contact_url);
  if (evidence.contactLinkHref !== contactHref) throw Error("ID 980 contact link mismatch");
}

async function runBrowser(expectedRows, envelope, receiptPath, screenshotPath) {
  const { chromium } = require("playwright");
  const externalAttempts = [];
  const pageErrors = [];
  const catalogResponses = [];
  const browser = await chromium.launch({ headless: true });

  try {
    const context = await browser.newContext({
      serviceWorkers: "block",
      acceptDownloads: false,
      ignoreHTTPSErrors: false,
    });
    await context.route("**/*", async (route) => {
      let allowed = false;
      try {
        const requestUrl = new URL(route.request().url());
        allowed = requestUrl.origin === EXPECTED_UI_ORIGIN;
      } catch {
        allowed = false;
      }
      if (allowed) {
        await route.continue();
      } else {
        externalAttempts.push(true);
        await route.abort("blockedbyclient");
      }
    });

    const page = await context.newPage();
    page.setDefaultTimeout(8000);
    page.on("pageerror", () => pageErrors.push(true));
    page.on("response", (response) => {
      try {
        const responseUrl = new URL(response.url());
        if (
          responseUrl.origin === EXPECTED_UI_ORIGIN &&
          responseUrl.pathname === "/api/mobility/listings"
        ) {
          catalogResponses.push({
            status: response.status(),
            page: Number(responseUrl.searchParams.get("page")),
            size: Number(responseUrl.searchParams.get("size")),
          });
        }
      } catch {
        // No response detail is retained in the evidence.
      }
    });

    await page.goto(EXPECTED_UI_ORIGIN + "/map", {
      waitUntil: "domcontentloaded",
      timeout: 30000,
    });
    await page.waitForFunction(
      () => document.querySelector('[data-testid="catalog-count"]')?.textContent?.trim() === "789 tin",
      undefined,
      { timeout: 60000 },
    );
    if ((await page.getByRole("heading", { level: 1, name: "Bản đồ di chuyển", exact: true }).count()) !== 1) {
      throw new Error("Map title H1 missing or ambiguous");
    }

    const domRows = await page.locator("button[data-listing-id]").evaluateAll((buttons) =>
      buttons.map((button) => ({
        id: Number(button.getAttribute("data-listing-id")),
        title: button.querySelector('span:nth-of-type(1)')?.textContent ?? '',
        area: button.querySelector('span:nth-of-type(3)')?.textContent ?? '',
      })),
    );
    if (domRows.length !== 789 || expectedRows.length !== 789) {
      throw new Error("Rendered catalog count mismatch");
    }
    const domIds = validateRenderedCards(expectedRows, domRows);
    const clusterEvidence = await verifyMountedClusterSnapshot(page, expectedRows);

    const pages = catalogResponses
      .filter((response) => response.status === 200 && response.size === 100)
      .map((response) => response.page)
      .sort((a, b) => a - b);
    if (JSON.stringify(pages) !== JSON.stringify([1, 2, 3, 4, 5, 6, 7, 8])) {
      throw new Error("UI proxy pagination mismatch");
    }

    const detail = page.locator('section[aria-label="Chi tiết tin được chọn"]').last();
    async function selectAndRead(row) {
      const button = page.locator('button[data-listing-id="' + row.id + '"]');
      if ((await button.count()) !== 1) throw new Error("Catalog button missing");
      await button.click();
      if ((await button.getAttribute("aria-pressed")) !== "true") {
        throw new Error("Catalog selection failed");
      }
      const title = normalizeSpace(await detail.locator("h2").textContent());
      if (title !== normalizeSpace(row.title)) throw new Error("Selected title mismatch");
      const detailText = normalizeSpace(await detail.textContent());
      const paragraphs = await detail.locator("p").allTextContents();
      return { title, detailText, paragraphs: paragraphs.map(normalizeSpace) };
    }

    const nullArea = expectedRows.find((row) => row.area === null);
    if (!nullArea) throw new Error("Null-area listing unavailable");
    const nullAreaDetail = await selectAndRead(nullArea);
    if (!nullAreaDetail.detailText.includes("Diện tích chưa rõ")) {
      throw new Error("Null-area label mismatch");
    }

    const partial = expectedRows.find(row => isPartial(row) && typeof row.description === 'string' && row.description.length > 0);
    if (!partial || typeof partial.description !== "string") {
      throw new Error("Partial-description listing unavailable");
    }
    const partialDetail = await selectAndRead(partial);
    validateDescriptionEvidence(partial, partialDetail);

    const id980 = expectedRows.find((row) => row.id === 980);
    if (!id980) throw new Error("ID 980 source listing unavailable");
    const id980Detail = await selectAndRead(id980);
    const id980Button = page.locator('button[data-listing-id="980"]');
    const sourceLink = detail.getByRole("link", { name: "Xem tin gốc", exact: true });
    const id980ContactLink = detail.getByRole("link", { name: "Liên hệ nguồn tin", exact: true });
    const id980Evidence = {
      id: 980,
      ariaPressed: (await id980Button.getAttribute("aria-pressed")) === "true",
      title: id980Detail.title,
      detailText: id980Detail.detailText,
      paragraphs: id980Detail.paragraphs,
      sourceLinkHref: await uniqueOptionalHref(sourceLink),
      contactLinkHref: await uniqueOptionalHref(id980ContactLink),
    };
    validateId980Evidence(expectedRows, id980Evidence);

    const contact = expectedRows.find(hasSafeContact);
    if (!contact) throw new Error("Contact listing unavailable");
    await selectAndRead(contact);
    const contactLink = page.getByRole("link", { name: "Liên hệ nguồn tin", exact: true });
    if (
      (await contactLink.count()) !== 1 ||
      (await contactLink.getAttribute("href")) !== contact.source_contact_url
    ) {
      throw new Error("Contact link mismatch");
    }

    const missingPosition = expectedRows.filter((row) => row.position === null);
    if (missingPosition.length !== 2) throw new Error("Missing-position count mismatch");
    for (const row of missingPosition) {
      await selectAndRead(row);
      const detailText = normalizeSpace(await detail.textContent());
      if (!detailText.includes("Tin chưa có tọa độ; vẫn giữ trong danh sách nhưng không đặt ghim.")) {
        throw new Error("Missing-position detail mismatch");
      }
      if (
        await page.locator('[data-listing-pin-id="' + row.id + '"]').count() !== 0 ||
        !(await page.getByRole("button", { name: "Tính tuyến tới khu đã chọn" }).isDisabled()) ||
        !(await page.getByRole("button", { name: "Tính tới cả 3 khu" }).isDisabled())
      ) {
        throw new Error("Missing-position controls mismatch");
      }
    }

    const visibleChecks = {
      original_titles: true,
      null_area: true,
      partial_description: true,
      withheld_description: true,
      contact_href: true,
      actual_cluster_membership: true,
      missing_position_selectable: true,
      missing_position_has_no_pin: true,
      missing_position_route_disabled: true,
    };
    if (externalAttempts.length !== 0 || pageErrors.length !== 0) {
      throw new Error("Browser attempted external traffic or raised a page error");
    }

    await page.screenshot({ path: screenshotPath, fullPage: true, animations: "disabled" });
    const receipt = {
      schema_version: 2,
      status: "REAL_CATALOG_BROWSER_VERIFIED",
      evidence_kind: ACCEPTANCE_EVIDENCE,
      operation_id: envelope.operation_id,
      expected_public_data_sha256: envelope.public_dto_sha256,
      actual_ids_sha256: crypto
        .createHash("sha256")
        .update(Buffer.from(JSON.stringify(domIds), "utf8"))
        .digest("hex"),
      api_origin: EXPECTED_API_ORIGIN,
      ui_origin: EXPECTED_UI_ORIGIN,
      source_catalog_count: domRows.length,
      unique_listing_count: new Set(domIds).size,
      missing_position_count: missingPosition.length,
      positioned_listing_count: clusterEvidence.positioned_listing_count,
      actual_positioned_members_sha256: clusterEvidence.actual_positioned_members_sha256,
      visible_checks: visibleChecks,
      external_attempts: externalAttempts.length,
    };
    fs.writeFileSync(receiptPath, JSON.stringify(receipt) + "\n", {
      encoding: "utf8",
      flag: "wx",
    });
    await context.close();
    return receipt;
  } finally {
    await browser.close();
  }
}

async function main(args) {
  if (args.length !== 3) throw new Error("Invalid browser arguments");
  const [expectedPath, receiptPath, screenshotPath] = args;
  if (fs.existsSync(receiptPath) || fs.existsSync(screenshotPath)) {
    throw new Error("Browser evidence already exists");
  }
  const envelope = JSON.parse(fs.readFileSync(expectedPath, "utf8"));
  const rows = validateExpectedEnvelope(envelope);
  await runBrowser(rows, envelope, receiptPath, screenshotPath);
}

module.exports = {
  validateExpectedEnvelope,
  validateRenderedCards,
  validateDescriptionEvidence,
  binary64BitsHex,
  validateClusterSnapshot,
  verifyMountedClusterSnapshot,
  validateId980Evidence,
  uniqueOptionalHref,
  runBrowser,
};

if (require.main === module) {
  main(process.argv.slice(2)).catch(() => {
    process.stderr.write('{"status":"FAIL","code":"BROWSER_ACCEPTANCE_NOT_VERIFIED"}\n');
    process.exitCode = 1;
  });
}
