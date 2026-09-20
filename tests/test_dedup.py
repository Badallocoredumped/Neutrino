"""Tests for consumption data deduplication."""

import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch


def _make_repo():
    with patch(
        "database.epias_data_repository.EPIASDataRepository.connect",
        return_value=True,
    ):
        from database.epias_data_repository import EPIASDataRepository

        repo = EPIASDataRepository.__new__(EPIASDataRepository)
        repo.pg_conn = MagicMock()
        return repo


def test_dedup_removes_duplicate_dates():
    repo = _make_repo()
    rows = [
        {"datetime": datetime(2025, 9, 1), "consumption_mwh": 21000.0},
        {"datetime": datetime(2025, 9, 2), "consumption_mwh": 22000.0},
        {"datetime": datetime(2025, 9, 3), "consumption_mwh": 23000.0},
    ]
    df = pd.DataFrame(rows)
    result = repo._deduplicate_records(df)
    assert len(result) == 3
    assert list(result["consumption_mwh"]) == [21000.0, 22000.0, 23000.0]
