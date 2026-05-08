from __future__ import annotations

import argparse
import json
import re
from pathlib import Path
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
請分析以下 PA450 report 是否有異常流量，並說明原因。

判斷重點：
1. 是否有明顯高流量來源。
3. 是否有可疑應用程式。
4. 是否有單一來源對外大量傳輸。

輸出規則：
1. 只能引用 context 裡實際存在的單筆資料列。
2. 如果有多筆可疑資料，必須逐筆列出，不可只輸出一組彙總欄位。
3. 每筆都要用同一行格式：第N筆的來源：... 目的地：... 應用程式：... 位元組：...
4. 來源、目的地、應用程式、位元組都要直接使用該筆 CSV 的原始值。

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
AGENT_DIR = PROJECT_ROOT / ".agent"
AGENT_PATH = AGENT_DIR / "AGENT.md"
REVIEW_PATH = AGENT_DIR / "review.md"
REPORT_PATH_PATTERN = re.compile(r"report_(\d{8})\.md$")
FEEDBACK_HEADING_PATTERN = re.compile(
    r"^(#{1,6})\s*(feedback|review|judg(?:e|ment)|rules?|guidance|回饋|評語|審查|建議|注意事項)\b",
    re.IGNORECASE,
)
LIST_ITEM_PATTERN = re.compile(r"^(?:[-*+]\s+|\d+[.)]\s+)(.+)$")
RULE_PREFIX_PATTERN = re.compile(r"^(?:should|must|avoid|ensure|prefer|always|never|請|應|需|必須|避免|確認|優先)", re.IGNORECASE)


def build_context(input_path: str | Path) -> str:
    return Path(input_path).read_text(encoding="utf-8-sig")


def _read_agent_instructions() -> str:
    if not AGENT_PATH.exists():
        raise FileNotFoundError(f"Missing required agent workflow file: {AGENT_PATH}")
    return AGENT_PATH.read_text(encoding="utf-8")


def _extract_report_date(path: Path) -> str | None:
    match = REPORT_PATH_PATTERN.fullmatch(path.name)
    return match.group(1) if match else None


def _extract_input_date(path: Path) -> str | None:
    match = re.search(r"(\d{8})", path.name)
    return match.group(1) if match else None


def _candidate_report_paths(input_path: Path | None) -> list[Path]:
    output_dir = PROJECT_ROOT / "output"
    if not output_dir.exists():
        return []

    reports = sorted(
        (path for path in output_dir.glob("report_*.md") if REPORT_PATH_PATTERN.fullmatch(path.name)),
        key=lambda path: path.name,
        reverse=True,
    )
    if not reports:
        return []

    input_date = _extract_input_date(input_path) if input_path else None
    if not input_date:
        return reports

    prioritized: list[Path] = []
    deferred: list[Path] = []
    for report_path in reports:
        if _extract_report_date(report_path) == input_date:
            prioritized.append(report_path)
        else:
            deferred.append(report_path)
    return prioritized + deferred


def _normalize_rule(text: str) -> str:
    collapsed = re.sub(r"\s+", " ", text.strip())
    collapsed = collapsed.lstrip("-•*0123456789.) ")
    return collapsed.rstrip("。.;；")


def _extract_distilled_rules(report_text: str) -> list[str]:
    lines = report_text.splitlines()
    rules: list[str] = []
    capture_depth: int | None = None

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        heading_match = FEEDBACK_HEADING_PATTERN.match(stripped)
        if heading_match:
            capture_depth = len(heading_match.group(1))
            continue

        if capture_depth is not None and stripped.startswith("#"):
            next_heading_depth = len(stripped) - len(stripped.lstrip("#"))
            if next_heading_depth <= capture_depth:
                capture_depth = None
                continue

        if capture_depth is None:
            continue

        list_match = LIST_ITEM_PATTERN.match(stripped)
        if list_match:
            candidate = _normalize_rule(list_match.group(1))
            if candidate:
                rules.append(candidate)
            continue

        if RULE_PREFIX_PATTERN.match(stripped):
            candidate = _normalize_rule(stripped)
            if candidate:
                rules.append(candidate)

    deduped: list[str] = []
    seen: set[str] = set()
    for rule in rules:
        key = rule.casefold()
        if key in seen:
            continue
        seen.add(key)
        deduped.append(rule)
    return deduped


def _read_existing_review_rules() -> list[str]:
    if not REVIEW_PATH.exists():
        return []
    rules: list[str] = []
    for raw_line in REVIEW_PATH.read_text(encoding="utf-8").splitlines():
        stripped = raw_line.strip()
        if not stripped:
            continue
        list_match = LIST_ITEM_PATTERN.match(stripped)
        if not list_match:
            continue
        candidate = _normalize_rule(list_match.group(1))
        if candidate:
            rules.append(candidate)
    return rules


def _write_review_rules(rules: list[str]) -> None:
    REVIEW_PATH.parent.mkdir(parents=True, exist_ok=True)
    if rules:
        content = "\n".join(f"- {rule}" for rule in rules) + "\n"
    else:
        content = ""
    REVIEW_PATH.write_text(content, encoding="utf-8")


def refresh_review_memory(input_path: Path | None = None) -> str:
    rules = _read_existing_review_rules()
    for report_path in _candidate_report_paths(input_path):
        new_rules = _extract_distilled_rules(report_path.read_text(encoding="utf-8"))
        if not new_rules:
            continue
        existing_keys = {rule.casefold() for rule in rules}
        for rule in new_rules:
            if rule.casefold() not in existing_keys:
                rules.append(rule)
                existing_keys.add(rule.casefold())
        break
    _write_review_rules(rules)
    return REVIEW_PATH.read_text(encoding="utf-8") if REVIEW_PATH.exists() else ""


def load_agent_workflow(input_path: Path | None = None) -> dict[str, str]:
    agent_instructions = _read_agent_instructions()
    review_rules = refresh_review_memory(input_path)
    return {
        "agent_instructions": agent_instructions,
        "review_rules": review_rules,
    }


def _compose_runtime_guidance(workflow: dict[str, str]) -> str:
    parts = [
        "請先遵守以下啟動工作流，再進行後續分析。",
        "<agent_workflow>",
        workflow["agent_instructions"].strip(),
        "</agent_workflow>",
    ]
    review_rules = workflow["review_rules"].strip()
    if review_rules:
        parts.extend([
            "<review_rules>",
            review_rules,
            "</review_rules>",
            "後續分析時，若 review_rules 與目前 context 相關，請優先參考這些人工回饋規則。",
        ])
    else:
        parts.append("目前沒有可用的 review_rules。")
    return "\n".join(parts)


def analyze_with_ai(query: str, context: str, workflow: dict[str, str] | None = None) -> str:
    import httpx
    import os
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

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

    sync_client  = httpx.Client(verify=False)

    model = ChatOpenAI(
        base_url=url,
        api_key=api_key,
        model=model_name,
        temperature=temperature,
        http_client=sync_client,
        model_kwargs={"reasoning_effort": "low"},
    )

    messages = []
    if workflow:
        messages.append(SystemMessage(content=_compose_runtime_guidance(workflow)))
    messages.extend([
        SystemMessage(
            content=ANALYSIS_SYSTEM_PROMPT
        ),
        HumanMessage(
            content=ANALYSIS_USER_PROMPT_TEMPLATE.format(context=context)
        ),
    ])
    resp = model.invoke(messages)
    return str(resp.content)


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
    workflow = load_agent_workflow()
    args = parse_args(argv)
    workflow["review_rules"] = refresh_review_memory(args.input)
    context = build_context(args.input)
    analysis = analyze_with_ai(args.query, context, workflow=workflow)
    write_analysis_result(args.output, analysis)
    print(f"Analysis written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
