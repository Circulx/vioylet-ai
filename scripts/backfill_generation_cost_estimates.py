from __future__ import annotations

import argparse

from app.services.generation_trace import GenerationTraceService


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill generation trace cost_estimation.json files.")
    parser.add_argument("--limit", type=int, default=0, help="Maximum number of trace folders to process. 0 means all.")
    parser.add_argument("--missing-only", action=argparse.BooleanOptionalAction, default=True)
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    service = GenerationTraceService()
    if not service.enabled:
        print("Generation tracing is disabled; nothing to backfill.")
        return 0
    trace_dirs = [
        path
        for path in sorted(service.base_dir.iterdir(), key=lambda item: item.stat().st_mtime, reverse=True)
        if path.is_dir() and (path / "manifest.json").exists()
    ]
    if args.limit and args.limit > 0:
        trace_dirs = trace_dirs[: args.limit]
    written = 0
    skipped = 0
    for trace_dir in trace_dirs:
        if args.missing_only and (trace_dir / "cost_estimation.json").exists():
            skipped += 1
            continue
        output = service.write_cost_estimation(trace_dir.name)
        if output:
            written += 1
        else:
            skipped += 1
    print(f"cost_estimation backfill complete: written={written} skipped={skipped}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
