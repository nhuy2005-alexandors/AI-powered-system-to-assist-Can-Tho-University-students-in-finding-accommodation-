import hashlib
from pathlib import Path
import json

import pytest

from app.room_service.legal_knowledge.index_corpus import _matches_checksum, index_corpus


@pytest.mark.parametrize("original,checkout", [
    (b'{\n"a": 1\n}\n', b'{\r\n"a": 1\r\n}\r\n'),
    (b'{\r\n"a": 1\r\n}\r\n', b'{\n"a": 1\n}\n'),
])
def test_checksum_allows_git_line_endings_only(tmp_path, original, checkout):
    path = tmp_path / "corpus.json"
    path.write_bytes(checkout)
    expected = hashlib.sha256(original).hexdigest()
    assert _matches_checksum(path, expected)
    path.write_bytes(checkout.replace(b'1', b'2'))
    assert not _matches_checksum(path, expected)


def test_bundled_corpus_checksums():
    corpus = Path(__file__).resolve().parents[1] / "chatbot_corpus"
    manifest = json.loads((corpus / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["documents"]
    for entry in manifest["documents"]:
        assert _matches_checksum(corpus / entry["file"], entry["sha256"]), entry["file"]


def test_invalid_bundle_fails_before_database_or_embedding(tmp_path):
    (tmp_path / "bad.json").write_bytes(b'{}')
    (tmp_path / "manifest.json").write_text(json.dumps({"documents": [
        {"file": "bad.json", "sha256": "not-a-checksum"},
    ]}), encoding="utf-8")
    with pytest.raises(SystemExit, match="checksum"):
        index_corpus(None, tmp_path, "legal_ctu_v1", None)
