from __future__ import annotations

import argparse
import asyncio
import os
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from rich.console import Console

from world_cafe.graph import build_world_cafe_graph, create_initial_state
from world_cafe.llm import DryRunCafeLLM, OpenAICafeLLM
from world_cafe.profiles import load_agent_profiles, load_questions
from world_cafe.report import write_outputs


console = Console()


def main() -> None:
    load_dotenv()
    args = _parse_args()
    asyncio.run(_amain(args))


async def _amain(args: argparse.Namespace) -> None:
    questions = _resolve_questions(args)
    agents = load_agent_profiles(args.agents_file) if args.agents_file else None
    llm = _build_llm(args)
    initial_state = create_initial_state(
        questions=questions,
        agents=agents,
        rounds=args.rounds,
        table_count=args.tables,
        seats_per_table=args.seats,
    )
    graph = build_world_cafe_graph(llm)
    config = {"configurable": {"thread_id": initial_state["run_id"]}}

    if args.stream:
        final_state: dict[str, Any] | None = None
        async for chunk in graph.astream(
            initial_state,
            config=config,
            stream_mode=["custom", "values"],
            version="v2",
        ):
            if chunk["type"] == "custom":
                event = chunk["data"]
                console.print(
                    f"[cyan]{event['stage']}[/cyan] {event['message']} "
                    f"[dim]{event.get('metadata', {})}[/dim]"
                )
            elif chunk["type"] == "values":
                final_state = chunk["data"]
        if final_state is None:
            raise RuntimeError("graph stream ended without final state")
    else:
        final_state = await graph.ainvoke(initial_state, config=config)

    report_path, trace_path = write_outputs(final_state, args.output_dir)
    console.print(f"[green]World cafe completed.[/green] run_id={final_state['run_id']}")
    console.print(f"Report: {Path(report_path).resolve()}")
    console.print(f"Trace:  {Path(trace_path).resolve()}")


def _resolve_questions(args: argparse.Namespace) -> list[str] | dict[str, str]:
    if args.questions_file:
        return load_questions(args.questions_file)
    if args.questions:
        return args.questions
    raise SystemExit("please provide --questions or --questions-file")


def _build_llm(args: argparse.Namespace):
    if args.dry_run:
        return DryRunCafeLLM()
    if args.model:
        os.environ["OPENAI_MODEL"] = args.model
    return OpenAICafeLLM.from_env(temperature=args.temperature, max_tokens=args.max_tokens)


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run a LangGraph world-cafe multi-agent discussion.")
    parser.add_argument(
        "--questions",
        nargs="+",
        help="Exactly one initial question per table. Default expects 4 questions.",
    )
    parser.add_argument("--questions-file", help="YAML file with a list or a 'tables' mapping.")
    parser.add_argument("--agents-file", help="YAML file with agent profiles.")
    parser.add_argument("--rounds", type=int, default=3, help="Discussion rounds. Default: 3.")
    parser.add_argument("--tables", type=int, default=4, help="Number of tables. Default: 4.")
    parser.add_argument("--seats", type=int, default=4, help="Agents per table. Default: 4.")
    parser.add_argument("--model", help="OpenAI-compatible model id. Default: OPENAI_MODEL.")
    parser.add_argument("--max-tokens", type=int, default=1600)
    parser.add_argument("--temperature", type=float, default=0.7)
    parser.add_argument("--dry-run", action="store_true", help="Use deterministic local output.")
    parser.add_argument("--stream", action="store_true", help="Print LangGraph custom stream events.")
    parser.add_argument("--output-dir", default="runs", help="Where reports and trace files are written.")
    return parser.parse_args()


if __name__ == "__main__":
    main()
