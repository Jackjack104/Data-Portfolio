from __future__ import annotations

import argparse
import json
import os
import subprocess
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from sales_crm_pipeline.config import PROJECT_ROOT, Settings
from sales_crm_pipeline.generate import GenerationConfig, generate_synthetic_data
from sales_crm_pipeline.load import load_generated_data

DEFAULT_DATA_DIR = PROJECT_ROOT / "data" / "generated"


def _add_generation_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", type=Path, default=DEFAULT_DATA_DIR)
    parser.add_argument("--seed", type=int, default=2026)
    parser.add_argument("--companies", type=int, default=500)
    parser.add_argument("--contacts", type=int, default=1_200)
    parser.add_argument("--orders", type=int, default=10_000)
    parser.add_argument("--batches", type=int, default=3)
    parser.add_argument("--overwrite", action="store_true")


def _generation_config(args: argparse.Namespace, force_overwrite: bool = False) -> GenerationConfig:
    return GenerationConfig(
        output_dir=args.output.resolve(),
        seed=args.seed,
        company_count=args.companies,
        contact_count=args.contacts,
        order_count=args.orders,
        batch_count=args.batches,
        overwrite=force_overwrite or args.overwrite,
    )


def _run_dbt() -> None:
    load_dotenv(PROJECT_ROOT / ".env")
    command = [
        "dbt",
        "build",
        "--project-dir",
        str(PROJECT_ROOT),
        "--profiles-dir",
        str(PROJECT_ROOT),
    ]
    subprocess.run(command, cwd=PROJECT_ROOT, env=os.environ.copy(), check=True)


def _print_result(result: dict[str, Any]) -> None:
    print(json.dumps(result, indent=2, sort_keys=True, default=str))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="sales-crm-pipeline",
        description="Generate, load, and transform synthetic CRM and ERP data.",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Generate source batches.")
    _add_generation_arguments(generate_parser)

    load_parser = subparsers.add_parser("load", help="Load source batches into PostgreSQL.")
    load_parser.add_argument("--input", type=Path, default=DEFAULT_DATA_DIR)

    run_parser = subparsers.add_parser("run", help="Run generation, ingestion, and dbt.")
    _add_generation_arguments(run_parser)
    run_parser.add_argument(
        "--skip-dbt",
        action="store_true",
        help="Generate and load data without running dbt.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "generate":
        _print_result(generate_synthetic_data(_generation_config(args)))
        return

    settings = Settings.from_env()
    if args.command == "load":
        _print_result(load_generated_data(settings, args.input.resolve()))
        return

    generation_result = generate_synthetic_data(_generation_config(args, force_overwrite=True))
    load_result = load_generated_data(settings, args.output.resolve())
    if not args.skip_dbt:
        _run_dbt()
    _print_result(
        {
            "generation": generation_result["requested_counts"],
            "ingestion": load_result,
            "dbt_completed": not args.skip_dbt,
        }
    )
