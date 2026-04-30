import csv

from pa450_report_monitor.convert import OutputColumn, rows_to_csv


def test_rows_to_csv_uses_configured_excel_columns(tmp_path):
    rows = [
        {
            "Generate Time": "2026/04/30 07:44:59",
            "Source address": "192.168.13.135",
            "Source Hostname": "192.168.13.135",
            "Source User": "",
            "Destination address": "17.253.17.203",
            "Destination Hostname": "ussc22-vip-bx-003.aaplimg.com",
            "Application": "itunes-base",
            "Bytes": "252.7 M",
        }
    ]
    csv_path = tmp_path / "report.csv"
    columns = [
        OutputColumn("產生時間", ["Generate Time", "generated-time"]),
        OutputColumn("來源位址", ["Source address", "src"]),
        OutputColumn("來源主機名稱", ["Source Hostname", "src-host"]),
        OutputColumn("來源使用者", ["Source User", "src-user"]),
        OutputColumn("目的地位址", ["Destination address", "dst"]),
        OutputColumn("目的地主機名稱", ["Destination Hostname", "dst-host"]),
        OutputColumn("應用程式", ["Application", "app"]),
        OutputColumn("位元組", ["Bytes", "bytes"]),
    ]

    rows_to_csv(rows, csv_path, columns=columns)

    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        assert reader.fieldnames == [
            "產生時間",
            "來源位址",
            "來源主機名稱",
            "來源使用者",
            "目的地位址",
            "目的地主機名稱",
            "應用程式",
            "位元組",
        ]
        assert list(reader) == [
            {
                "產生時間": "2026/04/30 07:44:59",
                "來源位址": "192.168.13.135",
                "來源主機名稱": "192.168.13.135",
                "來源使用者": "",
                "目的地位址": "17.253.17.203",
                "目的地主機名稱": "ussc22-vip-bx-003.aaplimg.com",
                "應用程式": "itunes-base",
                "位元組": "252.7 M",
            }
        ]
