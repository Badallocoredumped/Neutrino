"""Tests for the peak consumption hour report."""

import pandas as pd
from datetime import datetime
from unittest.mock import MagicMock, patch


def _make_repo_with_data(rows):
    """Return an EPIASDataRepository whose get_consumption_data_by_date_range
    returns the provided list of (datetime, consumption_mwh) tuples."""
    df = pd.DataFrame(rows, columns=["datetime", "consumption_mwh"])
    with patch(
        "database.epias_data_repository.EPIASDataRepository.connect",
        return_value=True,
    ):
        from database.epias_data_repository import EPIASDataRepository

        repo = EPIASDataRepository.__new__(EPIASDataRepository)
        repo.pg_conn = MagicMock()
        repo.get_consumption_data_by_date_range = MagicMock(return_value=df)
        return repo


def test_peak_hour_returns_correct_hour():
    rows = [
        (datetime(2025, 9, 1, 8, 0), 21000.0),
        (datetime(2025, 9, 1, 14, 0), 27500.0),
        (datetime(2025, 9, 1, 20, 0), 24300.0),
    ]
    repo = _make_repo_with_data(rows)

    result = repo.get_peak_consumption_hour(
        datetime(2025, 9, 1, 0, 0), datetime(2025, 9, 1, 23, 59)
    )

    assert result["consumption_mwh"] == 27500.0
    assert result["datetime"] == datetime(2025, 9, 1, 14, 0)
