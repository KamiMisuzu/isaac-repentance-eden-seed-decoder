#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))

from tools.eden_predict import EdenPredictOptions, format_text_report, predict_eden


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("seed", nargs="?", help='8-char seed e.g. "ABCD EFGH"')
    ap.add_argument("--seed-u32", type=int)
    ap.add_argument("--p988", type=int)
    ap.add_argument("--p3ec", type=int)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--verbose", action="store_true")
    ap.add_argument("--ach-159", action="store_true")
    ap.add_argument("--table", type=Path, default=None)
    ap.add_argument("--trinket-pool", type=Path, default=None)
    ap.add_argument("--rng409", type=int, default=None)
    ap.add_argument("--trinket-cache", action="store_true")
    ap.add_argument("--skip-items", action="store_true")
    ap.add_argument("--web", action="store_true")
    ap.add_argument("--reverse", action="store_true")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--prefix", default="")
    ap.add_argument("--start", default="0")
    ap.add_argument("--end", default="ffffffff")
    ap.add_argument("--max-results", type=int, default=50)
    ap.add_argument("--max-scan", type=int, default=5_000_000)
    ap.add_argument("--workers", type=int, default=None)
    ap.add_argument("--red", type=float, default=None)
    ap.add_argument("--soul", type=float, default=None)
    ap.add_argument("--damage", type=float, default=None)
    ap.add_argument("--speed", type=float, default=None)
    ap.add_argument("--tears", type=float, default=None)
    ap.add_argument("--range", dest="range_display", type=float, default=None)
    ap.add_argument("--shot-speed", type=float, default=None)
    ap.add_argument("--luck", type=float, default=None)
    ap.add_argument("--pocket-kind", default="")
    ap.add_argument("--trinket-id", type=int, default=None)
    ap.add_argument("--pocket-id", type=int, default=None)
    ap.add_argument("--passive-id", type=int, default=None)
    ap.add_argument("--active-id", type=int, default=None)
    args = ap.parse_args()

    if args.web:
        from web.server import run_server

        run_server(host=args.host, port=args.port)
        return

    if args.reverse:
        from tools.eden_reverse import reverse_search

        body = {
            "seed_prefix": args.prefix,
            "start_u32": args.start,
            "end_u32": args.end,
            "max_results": args.max_results,
            "max_scan": args.max_scan,
            "workers": args.workers,
            "ach_159": "1" if args.ach_159 else "0",
            "red": args.red,
            "soul": args.soul,
            "damage": args.damage,
            "speed": args.speed,
            "tears": args.tears,
            "range": args.range_display,
            "shotSpeed": args.shot_speed,
            "luck": args.luck,
            "pocket_kind": args.pocket_kind,
            "trinket_id": args.trinket_id,
            "pocket_id": args.pocket_id,
            "passive_id": args.passive_id,
            "active_id": args.active_id,
        }
        result = reverse_search(
            body,
            proc_path=args.table,
            trinket_path=args.trinket_pool,
            log_terminal=True,
        )
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        else:
            for m in result.get("matches", []):
                print(m["seed"])
            print(
                f"# scanned={result.get('scanned')} "
                f"count={result.get('count')} "
                f"elapsed={result.get('elapsed_sec')}s"
            )
        return

    has_seed = args.seed_u32 is not None or bool(args.seed)
    if not has_seed and (args.p988 is not None or args.p3ec is not None):
        opts = EdenPredictOptions(
            p988=args.p988,
            p3ec=args.p3ec,
            trinket_pool=args.trinket_pool,
            trinket_rng409=args.rng409,
        )
        _emit(predict_eden(opts), args.json)
        return

    if not has_seed:
        ap.error("provide seed, --seed-u32, --p988/--p3ec, or --web")

    opts = EdenPredictOptions(
        seed_u32=args.seed_u32,
        seed_label=(args.seed or "").strip().upper(),
        p988=args.p988,
        p3ec=args.p3ec,
        achievement_159=args.ach_159,
        proc_table=args.table,
        trinket_pool=args.trinket_pool,
        trinket_rng409=args.rng409,
        trinket_use_cache=args.trinket_cache,
        include_6dae40_verbose=args.verbose,
        skip_items=args.skip_items,
    )

    result = predict_eden(opts)
    _emit(result, args.json)


def _emit(result, as_json: bool) -> None:
    if as_json:
        print(json.dumps(result.to_json_dict(), indent=2, ensure_ascii=False))
    else:
        print(format_text_report(result))


if __name__ == "__main__":
    main()
