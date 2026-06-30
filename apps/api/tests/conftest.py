import sys
from pathlib import Path

# cho phép `import app...` khi chạy pytest từ apps/api
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture
def phongtro_html() -> str:
    return (FIXTURES / "phongtro123_list.html").read_text(encoding="utf-8")


@pytest.fixture
def phongtro_detail_html() -> str:
    return (FIXTURES / "phongtro123_detail.html").read_text(encoding="utf-8")
