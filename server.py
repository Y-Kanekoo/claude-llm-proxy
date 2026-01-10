#!/usr/bin/env python3
"""
Claude Code LLM Proxy - MCPサーバー

無料LLMプロバイダーをClaude CodeのツールとしてMCP経由で提供
"""

import asyncio
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

from router import router, TaskType

server = Server("llm-proxy")

AGENTS_DIR = Path(__file__).parent / "agents"


def load_agent_prompt(agent_name: str) -> str:
    """エージェントプロンプトをファイルから読み込む"""
    file_path = AGENTS_DIR / f"{agent_name}.md"
    if file_path.exists():
        return file_path.read_text(encoding="utf-8")
    return ""


@server.list_tools()
async def list_tools():
    """利用可能なツール一覧を返す"""
    return [
        Tool(
            name="code_review",
            description="コードレビュー - バグ、セキュリティ、改善点を指摘",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "レビュー対象のコード"},
                    "language": {"type": "string", "description": "プログラミング言語"},
                    "context": {"type": "string", "description": "追加のコンテキスト情報"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="generate_tests",
            description="ユニットテストを生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "テスト対象のコード"},
                    "language": {"type": "string", "description": "プログラミング言語"},
                    "framework": {"type": "string", "description": "テストフレームワーク（pytest, jestなど）"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="generate_docs",
            description="ドキュメントを生成",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "ドキュメント対象のコード"},
                    "doc_type": {"type": "string", "description": "ドキュメント種別（docstring/readme/api）"},
                    "language": {"type": "string", "description": "プログラミング言語"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="design_consult",
            description="設計に関する相談",
            inputSchema={
                "type": "object",
                "properties": {
                    "question": {"type": "string", "description": "設計に関する質問"},
                    "context": {"type": "string", "description": "プロジェクトのコンテキスト"}
                },
                "required": ["question"]
            }
        ),
        Tool(
            name="refactor_advice",
            description="リファクタリングの提案",
            inputSchema={
                "type": "object",
                "properties": {
                    "code": {"type": "string", "description": "リファクタリング対象のコード"},
                    "goals": {"type": "string", "description": "リファクタリングの目標"},
                    "language": {"type": "string", "description": "プログラミング言語"}
                },
                "required": ["code"]
            }
        ),
        Tool(
            name="llm_status",
            description="LLMプロバイダーの状態を確認",
            inputSchema={"type": "object", "properties": {}, "required": []}
        )
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict):
    """ツールを実行"""

    if name == "llm_status":
        status = router.get_status()
        available = router.get_available_providers()
        lines = ["# LLMプロバイダー状態\n"]
        for provider, info in status.items():
            emoji = "OK" if info["available"] and info["can_request"] else "NG"
            lines.append(f"[{emoji}] {provider}: {info['model']}")
        lines.append(f"\n利用可能: {', '.join(available) if available else 'なし'}")
        return [TextContent(type="text", text="\n".join(lines))]

    elif name == "code_review":
        system = load_agent_prompt("code_review")
        code = arguments.get("code", "")
        language = arguments.get("language", "")
        context = arguments.get("context", "")
        prompt = f"## Code\n```{language}\n{code}\n```"
        if context:
            prompt += f"\n\n## Context\n{context}"
        response = await router.route_request(prompt, TaskType.CODE_REVIEW, system)
        result = response.content if response.content else f"Error: {response.error}"
        result += f"\n\n---\n*Provider: {response.provider} | Model: {response.model}*"
        return [TextContent(type="text", text=result)]

    elif name == "generate_tests":
        system = load_agent_prompt("test_generator")
        code = arguments.get("code", "")
        language = arguments.get("language", "python")
        framework = arguments.get("framework", "pytest")
        prompt = f"## Code\n```{language}\n{code}\n```\n\nGenerate {framework} tests."
        response = await router.route_request(prompt, TaskType.TEST_GENERATION, system)
        result = response.content if response.content else f"Error: {response.error}"
        return [TextContent(type="text", text=result)]

    elif name == "generate_docs":
        system = load_agent_prompt("doc_generator")
        code = arguments.get("code", "")
        doc_type = arguments.get("doc_type", "docstring")
        language = arguments.get("language", "python")
        prompt = f"## Code\n```{language}\n{code}\n```\n\nGenerate {doc_type} documentation."
        response = await router.route_request(prompt, TaskType.DOCUMENTATION, system)
        result = response.content if response.content else f"Error: {response.error}"
        return [TextContent(type="text", text=result)]

    elif name == "design_consult":
        system = load_agent_prompt("design_consultant")
        question = arguments.get("question", "")
        context = arguments.get("context", "")
        prompt = f"## Question\n{question}"
        if context:
            prompt += f"\n\n## Context\n{context}"
        response = await router.route_request(prompt, TaskType.DESIGN_CONSULT, system)
        result = response.content if response.content else f"Error: {response.error}"
        return [TextContent(type="text", text=result)]

    elif name == "refactor_advice":
        system = load_agent_prompt("refactor_advisor")
        code = arguments.get("code", "")
        goals = arguments.get("goals", "improve readability")
        language = arguments.get("language", "")
        prompt = f"## Code\n```{language}\n{code}\n```\n\n## Goals\n{goals}"
        response = await router.route_request(prompt, TaskType.REFACTORING, system)
        result = response.content if response.content else f"Error: {response.error}"
        return [TextContent(type="text", text=result)]

    return [TextContent(type="text", text=f"Unknown tool: {name}")]


async def main():
    """メインエントリーポイント"""
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    print("MCP Server running on stdio", file=sys.stderr)
    asyncio.run(main())
