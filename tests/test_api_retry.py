"""Tests for EPİAŞ API fetch with retry logic."""

from unittest.mock import MagicMock, patch


def _make_collector():
    with patch("database.epias_consumption_manager.TGTManager"):
        from database.epias_consumption_manager import EPIASConsumptionCollector

        collector = EPIASConsumptionCollector.__new__(EPIASConsumptionCollector)
        collector.tgt_manager = MagicMock()
        collector.tgt_manager.get_valid_tgt.return_value = "mock-tgt-token"
        collector.consumption_url = "https://mock-epias.example.com/consumption"
        collector.headers_getdata = {"Content-Type": "application/json"}
        return collector


def test_fetch_returns_data_on_first_success():
    collector = _make_collector()

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {
        "items": [
            {"date": "2025-09-01T00:00:00+03:00", "consumption": 21500.0}
        ]
    }

    with patch("requests.post", return_value=mock_response) as mock_post:
        result = collector.get_realtime_consumption_data(
            "2025-09-01T00:00:00+03:00",
            "2025-09-01T23:00:00+03:00",
        )

    assert result is not None
    assert len(result["items"]) == 1
    mock_post.assert_called_once()
