from pa450_report_monitor.__main__ import format_alert_message


def test_format_alert_message_keeps_local_alert_without_webhook():
    rows = [
        {"source": "a", "bytes": "101", "extra": "x"},
        {"source": "b", "bytes": "202", "extra": "y"},
    ]

    message = format_alert_message(rows, 100)

    assert message.startswith("ALERT: 2 rows exceeded bytes threshold 100")
    assert "bytes=101" in message
    assert "source=a" in message
