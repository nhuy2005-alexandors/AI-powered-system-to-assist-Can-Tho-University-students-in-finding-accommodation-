"""Save the public CTU source pages/PDFs with provenance; no student login."""
import hashlib
import json
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "Data/student_housing/sources"
catalog = json.loads((ROOT / "apps/api/app/ktx/catalog.json").read_text(encoding="utf-8"))
OUT.mkdir(parents=True, exist_ok=True)
manifest = []
for source in catalog["sources"]:
    url = source["url"]
    if not url:
        continue
    suffix = ".pdf" if url.lower().endswith(".pdf") else ".html"
    path = OUT / (source["id"] + suffix)
    if not path.exists():
        with urlopen(Request(url, headers={"User-Agent": "CTU-housing-research/1.0"}), timeout=45) as response:
            payload = response.read()
        if suffix == ".pdf" and not payload.startswith(b"%PDF"):
            raise ValueError("The source is not a PDF: " + url)
        path.write_bytes(payload)
    raw = path.read_bytes()
    manifest.append({"id": source["id"], "title": source["title"], "url": url,
                     "file": path.relative_to(ROOT).as_posix(), "bytes": len(raw),
                     "sha256": hashlib.sha256(raw).hexdigest(), "downloaded_at": "2026-10-12"})
    print(source["id"] + ": " + str(len(raw)) + " bytes", flush=True)
(OUT / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
