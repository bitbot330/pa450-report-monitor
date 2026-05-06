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
    SystemMessage(
        content=(
            "你是資安流量分析助理，負責分析 PA450 firewall report。"
            "你只能根據使用者提供的 context 內容判斷，不可以使用外部知識補充不存在的資料。"
            "如果 context 資料不足，必須明確回答「資料不足，需人工確認」。"
            "請用繁體中文回答。"
            "回答要簡短、明確。"
        )
    ),
    HumanMessage(
        content=f"""
            問題：
            請分析以下 PA450 report 是否有異常流量，並說明原因。

            判斷重點：
            1. 是否有明顯高流量來源。
            2. 是否有明顯高流量目的地。
            3. 是否有可疑應用程式。
            4. 是否有單一來源對外大量傳輸。
            5. 若無法從資料判斷，請標示為需人工確認。

            請輸出以下格式：

            異常狀態：有異常 / 無明顯異常 
            摘要：一句話說明結果
            異常項目：
            - 來源：
            目的地：
            應用程式：
            位元組：
            原因：

        <context>
        {context}
        </context>
        """
    )
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
