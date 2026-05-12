from __future__ import annotations

import argparse
import csv
import io
import json
from pathlib import Path
import statistics
import sys
from typing import Any


DEFAULT_QUERY = "請判斷這份 PA450 report 是否有異常，並只根據 context 回答。"

ANALYSIS_SYSTEM_PROMPT = (
    "你是資安流量分析助理，負責分析 PA450 firewall report。"
    "你只能根據使用者提供的 context 內容判斷，不可以使用外部知識補充不存在的資料。"
    "如果 context 資料不足，必須明確回答「資料不足，需人工確認」。"
    "context 會直接提供原始 CSV 文字，第一列是表頭，後面每列都是實際資料列。"
    "你指出的異常項目必須能對應到 context 中真實存在的單筆資料列，不能把多列資料混成一筆，也不能捏造欄位值。"
    "請用繁體中文回答。"
    "回答要簡短、明確，並嚴格遵守指定格式。"
)

ANALYSIS_USER_PROMPT_TEMPLATE = """
問題：
請像監控幫手一樣分析以下 PA450 report 是否有異常流量，並說明原因。

判斷重點：
1. 是否有明顯高流量來源。
2. 是否有單筆流量明顯高於本次 CSV 其他資料。
3. 是否有同一來源對外累積大量傳輸。
4. 目的地位址是否為危險網域，例如俄羅斯相關網域。
5. 是否有 review rules 指定的正常或異常模式。

監控判斷規則：
1. 這份 context 可能本來就是 top-sources / 高流量報表，不要把所有 context rows 當成異常清單輸出。
2. 只列出符合異常判斷的資料列；沒有異常就說沒有。
3. 不限制異常筆數：有幾筆真正異常就列幾筆，但不得為了湊數列出正常資料。
4. 高位元組只能作為候選訊號，不可單獨覆蓋 review rules；若 review rules 說某應用或模式屬於正常，不能只因 bytes 高就列為異常。
5. 若資料不足以判斷是否異常，必須回答「資料不足，需人工確認」。
6. 若來源層級累積量異常，必須列出 context 中支撐該結論的實際資料列。

輸出規則：
1. 只能引用 context 裡實際存在的單筆資料列。
2. 異常項目必須逐筆列出，不可只輸出一組彙總欄位。
3. 每筆都要用同一行格式：第N筆的來源：... 目的地：... 應用程式：... 位元組：...
4. 來源、目的地、應用程式、位元組都要直接使用該筆 CSV 的原始值。
5. 若無明顯異常，不要輸出任何「第N筆」項目。

以下是 runtime 根據本次 CSV 產生的監控輔助統計，請用來避免把整份報表全列為異常；它不是固定 bytes threshold：
<monitoring_guidance>
{monitoring_guidance}
</monitoring_guidance>

請輸出以下格式：

異常狀態：有異常 / 無明顯異常 / 資料不足，需人工確認
摘要：一句話說明結果
第1筆的來源：... 目的地：... 應用程式：... 位元組：...
第2筆的來源：... 目的地：... 應用程式：... 位元組：...
...
原因：...

<context>
{context}
</context>
"""

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def build_context(input_path: str | Path) -> str:
    return Path(input_path).read_text(encoding="utf-8-sig")


def _parse_bytes(value: str | None) -> int | None:
    if value is None:
        return None
    cleaned = value.strip().replace(",", "")
    if not cleaned:
        return None
    try:
        return int(cleaned)
    except ValueError:
        return None


def _iqr_upper_fence(values: list[int]) -> float | None:
    if len(values) < 4:
        return None
    quartiles = statistics.quantiles(sorted(values), n=4, method="inclusive")
    q1, q3 = quartiles[0], quartiles[2]
    return q3 + 1.5 * (q3 - q1)


def build_monitoring_guidance(context: str) -> str:
    reader = csv.DictReader(io.StringIO(context))
    rows = list(reader)
    required_columns = {"來源位址", "目的地位址", "應用程式", "位元組"}
    fieldnames = set(reader.fieldnames or [])
    missing_columns = sorted(required_columns - fieldnames)
    if missing_columns:
        return "資料不足，需人工確認：缺少必要欄位 " + ", ".join(missing_columns)

    parsed_rows: list[tuple[int, dict[str, str], int]] = []
    for row_number, row in enumerate(rows, start=1):
        bytes_value = _parse_bytes(row.get("位元組"))
        if bytes_value is not None:
            parsed_rows.append((row_number, row, bytes_value))

    if len(parsed_rows) < 4:
        return "資料不足，需人工確認：可解析的位元組資料少於 4 筆，無法產生穩定分布判斷。"

    row_upper_fence = _iqr_upper_fence([bytes_value for _, _, bytes_value in parsed_rows])
    if row_upper_fence is None:
        return "資料不足，需人工確認：無法計算本次 CSV 的流量分布。"

    row_outliers = [
        (row_number, row, bytes_value)
        for row_number, row, bytes_value in parsed_rows
        if bytes_value > row_upper_fence
    ]

    source_totals: dict[str, int] = {}
    for _, row, bytes_value in parsed_rows:
        source = row.get("來源位址", "")
        source_totals[source] = source_totals.get(source, 0) + bytes_value

    source_upper_fence = _iqr_upper_fence(list(source_totals.values()))
    source_outliers = []
    if source_upper_fence is not None:
        source_outliers = [
            (source, total)
            for source, total in sorted(source_totals.items(), key=lambda item: item[1], reverse=True)
            if total > source_upper_fence
        ]

    lines = [
        f"資料列總數：{len(rows)}",
        f"可解析位元組資料列數：{len(parsed_rows)}",
        f"row-level IQR upper fence：{row_upper_fence}",
        "row-level 候選異常資料列：",
    ]
    if row_outliers:
        for row_number, row, bytes_value in row_outliers:
            lines.append(
                f"- 第{row_number}筆：來源 {row.get('來源位址', '')} "
                f"目的地 {row.get('目的地位址', '')} "
                f"應用程式 {row.get('應用程式', '')} 位元組 {bytes_value}"
            )
    else:
        lines.append("- 無")

    lines.append("source-level 候選異常來源：")
    if source_outliers:
        for source, total in source_outliers:
            lines.append(f"- 來源 {source} 總位元組 {total}")
    else:
        lines.append("- 無")

    lines.append("判斷提醒：上述候選只代表本次 CSV 內部分布明顯突出；仍必須套用 review rules，且不得把所有 rows 都列為異常。")
    return "\n".join(lines)


def _build_ai_model():
    import httpx
    import os
    from langchain_openai import ChatOpenAI

    from config import load_dotenv

    load_dotenv()
    api_key = os.getenv("AI_GATEWAY_API_KEY")
    url = os.getenv("AI_GATEWAY_URL")
    model_name = os.getenv("AI_MODEL") or "gpt-oss-20b"
    temperature = float(os.getenv("AI_TEMPERATURE") or "0.4")

    if not url:
        raise RuntimeError("Missing AI_GATEWAY_URL in .env")
    if not api_key:
        raise RuntimeError("Missing AI_GATEWAY_API_KEY in .env")

    sync_client = httpx.Client(verify=False)
    return ChatOpenAI(
        base_url=url,
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        http_client=sync_client,
        model_kwargs={"reasoning_effort": "low"},
    )


def analyze_with_ai(query: str, context: str) -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    from runtime.prompt_builder import build_system_prompt
    from runtime.review_tools import read_review_memory

    model = _build_ai_model()
    review_rules = read_review_memory(PROJECT_ROOT)
    messages = [
        SystemMessage(
            content=build_system_prompt(
                ANALYSIS_SYSTEM_PROMPT,
                start_dir=PROJECT_ROOT,
                review_rules=review_rules,
            )
        ),
        HumanMessage(
            content=ANALYSIS_USER_PROMPT_TEMPLATE.format(
                context=context,
                monitoring_guidance=build_monitoring_guidance(context),
            )
        ),
    ]
    resp = model.invoke(messages)
    return str(resp.content)


def extract_review_rules_from_feedback(feedback: str, existing_rules: str = "") -> str:
    from langchain_core.messages import HumanMessage, SystemMessage

    model = _build_ai_model()
    messages = [
        SystemMessage(
            content=(
                "你負責從使用者 feedback 萃取可重用的 PA450 report review 規則。"
                "只輸出可重複使用的簡短 markdown bullet rules。"
                "不要輸出本次分析結果、CSV 原始資料、一次性結論、冗長解釋或敏感資訊。"
                "如果沒有可重用規則，輸出空字串。"
            )
        ),
        HumanMessage(
            content=(
                "既有 review rules:\n"
                f"{existing_rules.strip() or '(empty)'}\n\n"
                "使用者 feedback:\n"
                f"{feedback.strip()}"
            )
        ),
    ]
    resp = model.invoke(messages)
    return str(resp.content).strip()


def process_pending_feedback() -> str:
    from runtime.review_tools import (
        mark_feedback_processed,
        read_review_memory,
        read_unprocessed_feedback,
        write_review_memory,
    )

    feedback_text, latest_date = read_unprocessed_feedback(PROJECT_ROOT)
    if latest_date is None:
        return "No pending feedback."

    if not feedback_text.strip():
        mark_feedback_processed(latest_date, PROJECT_ROOT)
        return f"Processed empty feedback through {latest_date}."

    existing_rules = read_review_memory(PROJECT_ROOT)
    new_rules = extract_review_rules_from_feedback(feedback_text, existing_rules)
    if new_rules:
        write_review_memory(new_rules, PROJECT_ROOT)
    mark_feedback_processed(latest_date, PROJECT_ROOT)
    return f"Processed feedback through {latest_date}."


def write_analysis_result(output_path: str | Path, analysis: str) -> None:
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    payload: dict[str, Any] = {"analysis": analysis}
    Path(output_path).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Analyze PA450 report CSV with AI")
    parser.add_argument("--input", required=True, type=Path, help="Path to PA450 report CSV")
    parser.add_argument("--output", required=True, type=Path, help="Path to analysis JSON output")
    parser.add_argument("--query", default=DEFAULT_QUERY, help="Question for the AI model")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    print(process_pending_feedback())
    context = build_context(args.input)
    analysis = analyze_with_ai(args.query, context)
    write_analysis_result(args.output, analysis)
    print(f"Analysis written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
