from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
from typing import Any


DEFAULT_QUERY = "請判斷這份 PA450 report 是否有異常，並只根據 context 回答。"


def build_context(input_path: str | Path) -> str:
    return Path(input_path).read_text(encoding="utf-8-sig")


def analyze_with_ai(query: str, context: str) -> str:
    import httpx
    import os
    from dotenv import load_dotenv
    from langchain_openai import ChatOpenAI
    from langchain_core.messages import HumanMessage, SystemMessage

    load_dotenv()
    api_key = os.getenv("api_key")
    url = os.getenv("url")

    sync_client  = httpx.Client(verify=False)
    async_client = httpx.AsyncClient(verify=False)

    llm = ChatOpenAI(
        base_url=url,
        api_key=api_key,
        model="qwen3-vl-4b-fp8",
        temperature=0.2,
        http_client=sync_client,
        http_async_client=async_client,
    )

    model = llm
    resp = model.invoke([
        SystemMessage(content="你是嚴謹的問答助理，只能根據context回答，不用作多餘的解釋。"),
        HumanMessage(content=f"問題：{query}\n\n<context>\n{context}\n</context>")
    ])
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
    args = parse_args(argv)
    context = build_context(args.input)
    analysis = analyze_with_ai(args.query, context)
    write_analysis_result(args.output, analysis)
    print(f"Analysis written: {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
