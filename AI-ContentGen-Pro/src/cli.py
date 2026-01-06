"""Command-line interface for AI-ContentGen-Pro.

Usage examples:
    python -m src.cli list
    python -m src.cli list --category marketing --verbose
    python -m src.cli generate product_description --var product_name="Laptop" --var features="Fast, Lightweight" --var audience="Students" --show-stats
    python -m src.cli variations social_media_post --count 3 --var topic="AI" --var platform="LinkedIn"
    python -m src.cli batch --input requests.json --output results/
    python -m src.cli history --limit 5 --template product_description --export history.json
    python -m src.cli stats --detailed
    python -m src.cli validate product_description --var product_name="Widget"
    python -m src.cli init
    python -m src.cli cost-estimate product_description --var product_name="Phone" --var features="5G, OLED" --var audience="Gamers"

Each command prints human-friendly output and supports JSON/plain modes where appropriate.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime
from getpass import getpass
from pathlib import Path
from typing import Any, Dict, List, Optional

from prettytable import PrettyTable

try:  # Maintain compatibility with current config module
    from .config import Config  # type: ignore
except Exception:  # pragma: no cover - fallback alias
    from .config import AppConfig as Config  # type: ignore

try:
    from .config import load_config
except Exception:  # pragma: no cover - load_config may not be available
    load_config = None

from .content_generator import ContentGenerator


class Colors:
    """ANSI color codes for terminal output."""

    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    CYAN = "\033[96m"
    BOLD = "\033[1m"
    END = "\033[0m"


class NoColors:
    """Fallback when ANSI colors are not supported."""

    GREEN = ""
    RED = ""
    YELLOW = ""
    CYAN = ""
    BOLD = ""
    END = ""


class ContentGeneratorCLI:
    """Command-line interface wrapper for ContentGenerator."""

    VERSION = "1.0.0"

    def __init__(self) -> None:
        self.supports_color = self._supports_color()
        self.colors = Colors if self.supports_color else NoColors
        self.config = None
        self.config_error: Optional[Exception] = None

        # Load configuration if available
        if load_config:
            try:
                self.config = load_config()
            except Exception as exc:  # Configuration may be missing, keep running
                self.config_error = exc

        api_key = None
        if self.config and hasattr(self.config, "openai_api_key"):
            api_key = getattr(self.config, "openai_api_key", None)
        if not api_key:
            api_key = os.getenv("OPENAI_API_KEY")

        try:
            self.generator = ContentGenerator(api_key=api_key)
        except Exception as exc:
            self.generator = ContentGenerator(api_key=None, load_defaults=True)
            self.config_error = exc

        self.parser = self.setup_parser()

    # ------------------------------------------------------------------
    # Parser setup
    # ------------------------------------------------------------------
    def setup_parser(self) -> argparse.ArgumentParser:
        parser = argparse.ArgumentParser(
            prog="ai-content-gen",
            description="AI Content Generator - Create marketing content using AI",
            epilog="For more information, visit: https://github.com/yourusername/AI-ContentGen-Pro",
        )
        parser.add_argument("--version", action="version", version=self.VERSION)

        subparsers = parser.add_subparsers(dest="command", help="Available commands")

        # list
        list_parser = subparsers.add_parser("list", help="List available templates")
        list_parser.add_argument("--category", help="Filter by category", default=None)
        list_parser.add_argument("--verbose", action="store_true", help="Show detailed template info")

        # generate
        gen_parser = subparsers.add_parser("generate", help="Generate content using a template")
        gen_parser.add_argument("template", help="Template name")
        gen_parser.add_argument("--var", action="append", default=[], help="Template variable KEY=VALUE (repeatable)")
        gen_parser.add_argument("--output", help="Save output to file")
        gen_parser.add_argument("--json", action="store_true", help="Output JSON")
        gen_parser.add_argument("--no-cache", action="store_true", dest="no_cache", help="Disable cache for this run")
        gen_parser.add_argument("--show-stats", action="store_true", help="Display token and cost stats")

        # variations
        var_parser = subparsers.add_parser("variations", help="Generate multiple variations")
        var_parser.add_argument("template", help="Template name")
        var_parser.add_argument("--count", type=int, default=3, help="Number of variations")
        var_parser.add_argument("--var", action="append", default=[], help="Template variable KEY=VALUE (repeatable)")
        var_parser.add_argument("--output-dir", help="Directory to save variations")

        # batch
        batch_parser = subparsers.add_parser("batch", help="Process batch requests from JSON file")
        batch_parser.add_argument("--input", required=True, help="JSON file with requests")
        batch_parser.add_argument("--output", help="Directory to save batch results")
        batch_parser.add_argument("--parallel", action="store_true", help="Process in parallel")

        # history
        history_parser = subparsers.add_parser("history", help="Show generation history")
        history_parser.add_argument("--limit", type=int, default=10, help="Limit number of items")
        history_parser.add_argument("--template", help="Filter by template name")
        history_parser.add_argument("--export", help="Export history to file (json/csv/txt)")
        history_parser.add_argument("--since", help="Only show items after date (YYYY-MM-DD)")

        # stats
        stats_parser = subparsers.add_parser("stats", help="Show usage statistics")
        stats_parser.add_argument("--detailed", action="store_true", help="Show per-template breakdown")
        stats_parser.add_argument("--json", action="store_true", help="Output JSON")

        # validate
        val_parser = subparsers.add_parser("validate", help="Validate template variables")
        val_parser.add_argument("template", help="Template name")
        val_parser.add_argument("--var", action="append", default=[], help="Template variable KEY=VALUE (repeatable)")

        # init
        subparsers.add_parser("init", help="Interactive setup wizard")

        # cost-estimate
        cost_parser = subparsers.add_parser("cost-estimate", help="Estimate cost before generation")
        cost_parser.add_argument("template", help="Template name")
        cost_parser.add_argument("--var", action="append", default=[], help="Template variable KEY=VALUE (repeatable)")

        return parser

    # ------------------------------------------------------------------
    # Entry point
    # ------------------------------------------------------------------
    def run(self) -> None:
        args = self.parser.parse_args()
        if not args.command:
            self.parser.print_help()
            sys.exit(0)

        handlers = {
            "list": self._cmd_list,
            "generate": self._cmd_generate,
            "variations": self._cmd_variations,
            "batch": self._cmd_batch,
            "history": self._cmd_history,
            "stats": self._cmd_stats,
            "validate": self._cmd_validate,
            "init": self._cmd_init,
            "cost-estimate": self._cmd_cost_estimate,
        }

        handler = handlers.get(args.command)
        if not handler:
            self._print_error(f"Unknown command: {args.command}")
            sys.exit(2)

        try:
            handler(args)
        except ValueError as exc:
            self._print_error(str(exc))
            sys.exit(2)
        except KeyboardInterrupt:
            print("\nOperation cancelled by user")
            sys.exit(130)
        except Exception as exc:
            self._print_error(f"Unexpected error: {exc}")
            sys.exit(1)

    # ------------------------------------------------------------------
    # Command handlers
    # ------------------------------------------------------------------
    def _cmd_list(self, args: argparse.Namespace) -> None:
        templates = self.generator.list_available_templates()
        if args.category:
            cat = args.category.lower()
            templates = [t for t in templates if str(t.get("category", "")).lower() == cat]

        rows: List[Dict[str, Any]] = []
        for tpl in templates:
            rows.append(
                {
                    "Template Name": tpl.get("name", ""),
                    "Category": tpl.get("category", ""),
                    "Required Variables": ", ".join(tpl.get("required_variables", [])),
                }
            )

        self._print_header("Available Content Templates")
        if rows:
            self._display_table(rows, ["Template Name", "Category", "Required Variables"])
        else:
            print("No templates found.")

        if args.verbose:
            print("\nDetails:")
            for tpl in templates:
                print(f"- {tpl.get('name')}: {tpl.get('description', 'No description')}")

    def _cmd_generate(self, args: argparse.Namespace) -> None:
        variables = self._parse_variables(args.var)
        result = self.generator.generate(
            args.template,
            variables,
            use_cache=not args.no_cache,
        )

        if args.json:
            print(json.dumps(result, indent=2))
        else:
            self._display_result(result, show_stats=args.show_stats)

        if args.output and result.get("content"):
            self._save_output(result.get("content", ""), args.output)

        if not result.get("success", False):
            sys.exit(3)

    def _cmd_variations(self, args: argparse.Namespace) -> None:
        variables = self._parse_variables(args.var)
        results = self.generator.generate_multiple_variations(
            args.template,
            variables,
            count=args.count,
        )

        for res in results:
            print("-" * 60)
            title = f"Variation {res.get('variation_number', '?')}"
            print(f"{title} (temp={res.get('variation_temperature', 0):.2f})")
            self._display_result(res, show_stats=True, compact=True)
            if args.output_dir and res.get("content"):
                filename = f"{args.template}_var{res.get('variation_number', 0)}.txt"
                path = Path(args.output_dir) / filename
                self._save_output(res.get("content", ""), str(path))

        if any(not r.get("success", False) for r in results):
            sys.exit(3)

    def _cmd_batch(self, args: argparse.Namespace) -> None:
        input_path = Path(args.input)
        if not input_path.exists():
            raise ValueError(f"Input file not found: {input_path}")

        try:
            requests = json.loads(input_path.read_text(encoding="utf-8"))
        except Exception as exc:
            raise ValueError(f"Failed to parse input JSON: {exc}") from exc

        if not isinstance(requests, list):
            raise ValueError("Input JSON must be a list of request objects")

        total = len(requests)
        results = []
        for idx, req in enumerate(requests, start=1):
            self._show_progress(idx - 1, total, "Processing")
            tpl = req.get("template") or req.get("template_name")
            variables = req.get("variables", {})
            result = self.generator.generate_batch(
                [
                    {
                        "template_name": tpl,
                        "variables": variables,
                    }
                ],
                parallel=args.parallel,
            )[0]
            results.append(result)
            self._show_progress(idx, total, "Processing")
        print()

        summary_rows = []
        for i, res in enumerate(results, start=1):
            summary_rows.append(
                {
                    "#": i,
                    "Template": res.get("template_used", ""),
                    "Success": "Yes" if res.get("success") else "No",
                    "Cost": f"${res.get('cost', 0):.6f}",
                }
            )
        self._print_header("Batch Summary")
        self._display_table(summary_rows, ["#", "Template", "Success", "Cost"])

        if args.output:
            out_dir = Path(args.output)
            out_dir.mkdir(parents=True, exist_ok=True)
            for i, res in enumerate(results, start=1):
                filename = out_dir / f"batch_{i}_{res.get('template_used','unknown')}.json"
                filename.write_text(json.dumps(res, indent=2), encoding="utf-8")

        if any(not r.get("success", False) for r in results):
            sys.exit(3)

    def _cmd_history(self, args: argparse.Namespace) -> None:
        start_date = None
        if args.since:
            try:
                start_date = datetime.fromisoformat(args.since)
            except ValueError:
                raise ValueError("--since must be in YYYY-MM-DD format")

        history = self.generator.get_history(
            limit=args.limit,
            template_filter=args.template,
            start_date=start_date,
            success_only=False,
        )

        rows = []
        for item in history:
            rows.append(
                {
                    "Timestamp": item.get("timestamp", ""),
                    "Template": item.get("template_used", ""),
                    "Cost": f"${item.get('cost', 0):.6f}",
                    "Success": "Yes" if item.get("success") else "No",
                }
            )

        self._print_header("Generation History")
        if rows:
            self._display_table(rows, ["Timestamp", "Template", "Cost", "Success"])
        else:
            print("No history available.")

        if args.export:
            export_path = args.export
            fmt = Path(export_path).suffix.replace(".", "") or "json"
            self.generator.export_history(export_path, format=fmt)
            print(f"History exported to {export_path}")

    def _cmd_stats(self, args: argparse.Namespace) -> None:
        stats = self.generator.get_statistics()
        if args.json:
            print(json.dumps(stats, indent=2))
            return

        self._print_header("Usage Statistics")
        print(f"Total generations : {stats.get('total_generations', 0)}")
        print(f"Total cost        : ${stats.get('total_cost', 0):.6f}")
        print(f"Total tokens      : {stats.get('total_tokens', 0)}")
        print(f"Success rate      : {stats.get('success_rate', 0):.2f}%")
        print(f"Cache hit rate    : {stats.get('cache_hit_rate', 0):.2f}%")
        print(f"Avg gen time      : {stats.get('average_generation_time', 0):.3f}s")

        if args.detailed:
            templates = stats.get("templates_used", {})
            cost_by_template = stats.get("cost_by_template", {})
            rows = []
            for name, count in templates.items():
                rows.append(
                    {
                        "Template": name,
                        "Count": count,
                        "Cost": f"${cost_by_template.get(name, 0):.6f}",
                    }
                )
            if rows:
                print()
                self._display_table(rows, ["Template", "Count", "Cost"])

    def _cmd_validate(self, args: argparse.Namespace) -> None:
        variables = self._parse_variables(args.var)
        valid, missing = self.generator.validate_template_variables(args.template, variables)
        if valid:
            msg = f"Variables are valid for template '{args.template}'."
            print(self._color(msg, self.colors.GREEN))
        else:
            msg = f"Missing variables for '{args.template}': {', '.join(missing)}"
            print(self._color(msg, self.colors.RED))
            sys.exit(2)

    def _cmd_init(self, args: argparse.Namespace) -> None:  # noqa: ARG002
        self._print_header("Interactive Setup")
        api_key = getpass("Enter OpenAI API key: ")
        default_model = self._prompt_interactive("Default model (gpt-4 or gpt-3.5-turbo)", "gpt-4")
        temperature = self._prompt_interactive("Default temperature (0.0-2.0)", "0.7")
        max_tokens = self._prompt_interactive("Max tokens", "2000")

        env_lines = [
            f"OPENAI_API_KEY={api_key}",
            f"OPENAI_MODEL={default_model}",
            f"TEMPERATURE={temperature}",
            f"MAX_TOKENS={max_tokens}",
        ]

        env_path = Path(".env")
        env_path.write_text("\n".join(env_lines), encoding="utf-8")
        print(self._color(f".env created at {env_path.resolve()}", self.colors.GREEN))

    def _cmd_cost_estimate(self, args: argparse.Namespace) -> None:
        variables = self._parse_variables(args.var)
        estimate = self.generator.estimate_cost(args.template, variables)
        if not estimate.get("success"):
            self._print_error(estimate.get("error", "Estimation failed"))
            sys.exit(3)

        self._print_header("Cost Estimate")
        print(f"Model: {estimate.get('model')}")
        print(f"Prompt tokens: {estimate.get('estimated_prompt_tokens')}")
        print(f"Completion tokens: {estimate.get('estimated_completion_tokens')}")
        print(f"Total tokens: {estimate.get('estimated_total_tokens')}")
        print(f"Estimated cost: ${estimate.get('estimated_cost', 0):.6f}")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------
    def _display_result(self, result: Dict[str, Any], show_stats: bool = False, compact: bool = False) -> None:
        if not result.get("success"):
            err = result.get("error", "Unknown error")
            print(self._format_error(err))
            return

        self._print_header("Generated Content", compact=compact)
        print(result.get("content", ""))
        print("-" * 60)
        print("Generation Details:")
        print(f"  Template : {result.get('template_used', '')}")
        print(f"  Timestamp: {result.get('timestamp', '')}")
        if show_stats:
            tokens = result.get("tokens_used", {})
            print(f"  Tokens   : {tokens.get('total', 0)} (Prompt: {tokens.get('prompt', 0)}, Completion: {tokens.get('completion', 0)})")
            print(f"  Cost     : ${result.get('cost', 0):.6f}")
        print(f"  Cached   : {'Yes' if result.get('cached') else 'No'}")
        print(f"  Model    : {result.get('model', '')}")

    def _display_table(self, data: List[Dict[str, Any]], columns: List[str]) -> None:
        table = PrettyTable()
        table.field_names = ["#"] + columns
        table.align = "l"

        for idx, row in enumerate(data, start=1):
            table.add_row([idx] + [row.get(col, "") for col in columns])

        print(table)

    def _prompt_interactive(self, message: str, default: Optional[str] = None) -> str:
        prompt = f"{message}"
        if default is not None:
            prompt += f" [{default}]"
        prompt += ": "
        response = input(prompt).strip()
        return response or (default or "")

    def _save_output(self, content: str, filepath: str) -> None:
        path = Path(filepath)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
        print(self._color(f"Saved output to {path.resolve()}", self.colors.GREEN))

    def _parse_variables(self, var_args: List[str]) -> Dict[str, Any]:
        variables: Dict[str, Any] = {}
        for raw in var_args:
            if "=" not in raw:
                raise ValueError(f"Invalid --var format: {raw}. Use KEY=VALUE")
            key, value = raw.split("=", 1)
            variables[key.strip()] = value.strip().strip('"').strip("'")
        return variables

    def _format_error(self, error_msg: str) -> str:
        suggestion = "Check template name and required variables."
        return self._color(f"Error: {error_msg}\n{suggestion}", self.colors.RED)

    def _show_progress(self, current: int, total: int, message: str) -> None:
        total = max(total, 1)
        current = min(current, total)
        bar_length = 30
        filled_length = int(bar_length * current / total)
        bar = "#" * filled_length + "-" * (bar_length - filled_length)
        sys.stdout.write(f"\r[{bar}] {current}/{total} {message}")
        sys.stdout.flush()
        if current == total:
            sys.stdout.write("\n")

    def _color(self, text: str, color: str) -> str:
        return f"{color}{text}{self.colors.END}" if self.supports_color else text

    def _print_header(self, title: str, compact: bool = False) -> None:
        line = "=" * 60
        if compact:
            print(f"{line}\n{title}\n{line}")
        else:
            print(line)
            print(f"{title}")
            print(line)

    def _print_error(self, message: str) -> None:
        print(self._color(message, self.colors.RED), file=sys.stderr)

    def _supports_color(self) -> bool:
        return sys.stdout.isatty() and os.getenv("TERM", "") != "dumb"


def main() -> None:  # pragma: no cover - CLI entry point
    cli = ContentGeneratorCLI()
    cli.run()


if __name__ == "__main__":  # pragma: no cover
    try:
        main()
    except KeyboardInterrupt:
        print("\nOperation cancelled by user")
        sys.exit(130)
    except Exception as exc:  # Fallback safety net
        print(f"Unexpected error: {exc}")
        sys.exit(1)
