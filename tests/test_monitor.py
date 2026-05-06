from pa450_report_monitor.report import parse_int, rows_exceeding_bytes_threshold


def test_parse_int_accepts_commas():
    assert parse_int("1,234") == 1234


def test_rows_exceeding_bytes_threshold_uses_field_candidates():
    rows = [
        {"source": "a", "bytes": "99"},
        {"source": "b", "Bytes": "101"},
        {"source": "c", "bytes": "not-a-number"},
    ]

    alerts = rows_exceeding_bytes_threshold(rows, ["bytes", "Bytes"], 100)

    assert alerts == [{"source": "b", "Bytes": "101"}]
