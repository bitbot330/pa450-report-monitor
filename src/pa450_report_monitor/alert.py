from __future__ import annotations

import json
import urllib.request


def format_alert_message(alert_rows: list[dict[str, str]], threshold: int) -> str:
    lines = [f"PA450 Report Alert: {len(alert_rows)} rows exceeded bytes threshold {threshold}."]
    for row in alert_rows[:10]:
        preview = ", ".join(f"{key}={value}" for key, value in sorted(row.items())[:8])
        lines.append(f"- {preview}")
    if len(alert_rows) > 10:
        lines.append(f"... and {len(alert_rows) - 10} more rows")
    return "\n".join(lines)


def send_discord_webhook(webhook_url: str, content: str) -> None:
    payload = json.dumps({"content": content}).encode("utf-8")
    request = urllib.request.Request(
        webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if response.status >= 300:
            raise RuntimeError(f"Discord webhook failed with status {response.status}")
