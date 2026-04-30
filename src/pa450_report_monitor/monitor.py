from __future__ import annotations


def parse_int(value: str | int | None) -> int | None:
    if value is None:
        return None
    if isinstance(value, int):
        return value
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def rows_exceeding_bytes_threshold(
    rows: list[dict[str, str]],
    field_candidates: list[str],
    threshold: int,
) -> list[dict[str, str]]:
    alerts: list[dict[str, str]] = []
    for row in rows:
        value = None
        for field in field_candidates:
            value = parse_int(row.get(field))
            if value is not None:
                break
        if value is not None and value > threshold:
            alerts.append(row)
    return alerts
