import re
import unicodedata

from datasketch import MinHash, MinHashLSH

from .schemas import NormalizedListing

NUM_PERM = 128
# T4: bigram shingle + ngưỡng 0.5 bắt near-dup tiếng Việt ngắn (khác dấu câu, "3/2"↔"3 2",
# thêm "quận"...) mà vẫn tách tin khác phòng. Tinh chỉnh trên tập gán nhãn khi có data thật.
JACCARD_THRESHOLD = 0.5


def _shingles(text: str, k: int = 2) -> set[str]:
    norm = unicodedata.normalize("NFD", text.lower())
    norm = "".join(c for c in norm if unicodedata.category(c) != "Mn")
    norm = re.sub(r"\s+", " ", re.sub(r"[^a-z0-9 ]", "", norm)).strip()
    tokens = norm.split(" ")
    if len(tokens) < k:
        return {norm} if norm else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def build_minhash(listing: NormalizedListing) -> MinHash:
    text = " ".join(
        p for p in [listing.title, listing.address, listing.description] if p
    )
    m = MinHash(num_perm=NUM_PERM)
    for sh in _shingles(text):
        m.update(sh.encode("utf-8"))
    return m


def find_duplicates(listings: list[NormalizedListing]) -> dict[int, int]:
    """
    Map index -> index của bản đại diện (canonical) khi trùng cross-source.
    Index không xuất hiện trong map = bản gốc, giữ nguyên.
    """
    lsh = MinHashLSH(threshold=JACCARD_THRESHOLD, num_perm=NUM_PERM)
    minhashes: list[MinHash] = []
    canonical: dict[int, int] = {}

    for i, listing in enumerate(listings):
        mh = build_minhash(listing)
        minhashes.append(mh)
        matches = lsh.query(mh)
        if matches:
            canonical[i] = int(matches[0])
        lsh.insert(str(i), mh)
    return canonical
