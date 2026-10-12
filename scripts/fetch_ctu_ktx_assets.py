"""Download CTU-published dormitory photographs and preserve their provenance."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "apps/web/public/images/ktx"
ARTICLE = "https://ssc.ctu.edu.vn/hoat/160-cs1.html"
INTRO = "https://ssc.ctu.edu.vn/hoat/213-ktx25.html"
ASSETS = [
    ("khu-a.jpg", "Gioithieu/1a.jpg", "Ký túc xá khu A", "A", INTRO),
    ("khu-b.jpg", "Gioithieu/1b.jpg", "Ký túc xá khu B", "B", INTRO),
    *[(f"phong-b-{i}.jpg", f"slideshow_right/B_{i}.jpg", f"Phòng ở khu B — ảnh {i}", "B", ARTICLE) for i in range(1, 4)],
    *[(f"phong-a2-{i}.jpg", f"slideshow_right/AC_{i}.jpg", f"Phòng ở khu A, dãy A2 — ảnh {i}", "A", ARTICLE) for i in range(1, 3)],
    *[(f"phong-3-nguoi-{i}.jpg", f"slideshow_right/A3_{i}.jpg", f"Phòng được nấu ăn, giường bộ, 3 người — ảnh {i}", "A", ARTICLE) for i in range(1, 3)],
    *[(f"phong-5-6-nguoi-{i}.jpg", f"slideshow_right/A6_{i}.jpg", f"Phòng được nấu ăn, giường bộ, 5–6 người — ảnh {i}", "A", ARTICLE) for i in range(1, 4)],
    *[(f"phong-8-nguoi-{i}.jpg", f"slideshow_right/A8_{i}.jpg", f"Phòng được nấu ăn, giường tầng, 8 người — ảnh {i}", "A", ARTICLE) for i in range(1, 3)],
]


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    images = []
    for name, remote, caption, area, article in ASSETS:
        url = "https://ssc.ctu.edu.vn/images/upload/" + remote
        path = OUT / name
        if not path.exists():
            request = Request(url, headers={"User-Agent": "CTUStudentHousingResearch/1.0"})
            with urlopen(request, timeout=30) as response:
                if not response.headers.get_content_type().startswith("image/"):
                    raise ValueError("Not an image: " + url)
                raw = response.read(12_000_001)
                if len(raw) > 12_000_000:
                    raise ValueError("Image exceeds download limit: " + url)
            path.write_bytes(raw)
        images.append(dict(src="/images/ktx/" + name, alt=caption, dormitory_id=area,
                           original_url=url, source_url=article, credit="Đại học Cần Thơ / Trung tâm Phục vụ Sinh viên",
                           sha256=hashlib.sha256(path.read_bytes()).hexdigest(), bytes=path.stat().st_size))
        print(name, path.stat().st_size, flush=True)
    manifest = dict(retrieved_at=datetime.now(timezone.utc).isoformat(), images=images)
    (OUT / "sources.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Saved {len(images)} original CTU images and sources.json")


if __name__ == "__main__":
    main()
