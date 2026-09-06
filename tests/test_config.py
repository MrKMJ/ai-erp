import pytest

from app.core.config import normalize_db_url


@pytest.mark.parametrize(
    "raw, expected",
    [
        ("postgres://u:p@h:5432/db", "postgresql+psycopg://u:p@h:5432/db"),
        ("postgresql://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("postgresql+psycopg://u:p@h/db", "postgresql+psycopg://u:p@h/db"),
        ("sqlite:///./ai_erp.db", "sqlite:///./ai_erp.db"),
    ],
)
def test_normalize_db_url(raw, expected):
    assert normalize_db_url(raw) == expected
