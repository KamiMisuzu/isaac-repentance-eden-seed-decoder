from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from tools.collectible_table import ProceduralTable
from tools.eden_j460 import eden_starting_items
from tools.eden_stats import (
    EdenProfile,
    EdenStatsResult,
    eden_stats_from_start_seed,
    format_range_hud_hint,
    format_wiki_deltas_line,
    summarize_stats,
    wiki_deltas_from_p988,
    wiki_deltas_from_start_seed,
)
from tools.game_rng import eden_7bc740_pocket
from tools.seed_codec import (
    custom_start_seed_label,
    normalize_seed_string,
    seed_string_error,
    seed_to_string,
    string_to_custom_start_seed,
)
from tools.trinket_eden import (
    load_trinket_pool,
    resolve_trinket_pool_path,
    trinket_rng409_for_eden,
)

ROOT = Path(__file__).resolve().parent.parent


def resolve_proc_table_path(explicit: Path | str | None = None) -> Path | None:
    from tools.profile_store import resolve_proc_table_path as _resolve

    return _resolve(explicit)


def load_proc_table(path: Path) -> ProceduralTable:
    raw = path.read_text(encoding="utf-8").strip()
    if raw.startswith('"') and raw.endswith('"'):
        raw = json.loads(raw)
    data = json.loads(raw) if isinstance(raw, str) else raw
    return ProceduralTable.from_frida_dump(data)


@dataclass
class EdenPredictOptions:
    seed_u32: int | None = None
    seed_label: str = ""
    p988: int | None = None
    p3ec: int | None = None
    achievement_159: bool = False
    proc_table: Path | None = None
    trinket_pool: Path | None = None
    trinket_rng409: int | None = None
    trinket_use_cache: bool = False
    include_6dae40_verbose: bool = False
    skip_items: bool = False


@dataclass
class EdenPredictResult:
    mode: str
    seed_label: str
    start_seed: int | None
    encoded_seed: str | None
    a5_113620: int | None
    p988: int
    p3ec_used: int
    p988_after: int | None
    wiki_deltas: dict[str, float]
    hearts: dict[str, Any]
    range_display: dict[str, float]
    range_hint: str
    wiki_line: str
    pocket: dict[str, Any]
    items: dict[str, Any] | None
    six_dae40: dict[str, Any] | None
    trinket_meta: dict[str, Any] = field(default_factory=dict)
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)

    def to_json_dict(self) -> dict[str, Any]:
        return asdict(self)


def _parse_seed(
    seed: str | None,
    seed_u32: int | None,
) -> tuple[int, str]:
    if seed_u32 is not None:
        u32 = seed_u32 & 0xFFFFFFFF
        label = custom_start_seed_label(u32) or seed_to_string(u32)
        if custom_start_seed_label(u32) is None:
            raise ValueError(
                seed_string_error(label) or f"not a custom start seed: {u32}"
            )
        return u32, label
    if not seed:
        raise ValueError("provide seed or seed_u32")
    label = normalize_seed_string(seed)
    u32 = string_to_custom_start_seed(label)
    if u32 is not None:
        return u32, label
    raise ValueError(seed_string_error(seed) or f"bad seed: {seed!r}")


def _pocket_dict(pocket, **extra) -> dict[str, Any]:
    d: dict[str, Any] = {
        "kind": pocket.kind,
        "pickup_id": pocket.pickup_id,
        "rng_fn": pocket.rng_fn,
        "card_id": pocket.card_id,
        "pill_effect": pocket.pill_effect,
        "trinket_id": pocket.trinket_id,
        "trinket_pool_idx": pocket.trinket_pool_idx,
        "grant_mode": pocket.grant_mode,
        "roll_seed": pocket.roll_seed,
    }
    d.update(extra)
    return d


def predict_eden(opts: EdenPredictOptions) -> EdenPredictResult:
    pool_path = resolve_trinket_pool_path(opts.trinket_pool)
    proc_path = resolve_proc_table_path(opts.proc_table)
    warnings: list[str] = []

    no_seed = opts.seed_u32 is None and not (opts.seed_label or "").strip()
    if no_seed and (opts.p988 is not None or opts.p3ec is not None):
        p3ec = (opts.p3ec if opts.p3ec is not None else opts.p988) & 0xFFFFFFFF
        rolls, wiki = wiki_deltas_from_p988(0, p3ec=p3ec)
        pocket = eden_7bc740_pocket(
            p3ec,
            trinket_pool_path=str(pool_path) if pool_path else None,
            start_seed=None,
            trinket_rng409=opts.trinket_rng409,
        )
        return EdenPredictResult(
            mode="p988_only",
            seed_label="",
            start_seed=None,
            encoded_seed=None,
            a5_113620=None,
            p988=p3ec,
            p3ec_used=p3ec,
            p988_after=None,
            wiki_deltas=wiki,
            hearts={
                "red1232": rolls.red1232,
                "red_hud": rolls.red1232 / 2.0,
                "soul1235": rolls.soul1235,
                "cap1233": 15,
            },
            range_display=wiki,
            range_hint=format_range_hud_hint(rolls),
            wiki_line=format_wiki_deltas_line(rolls),
            pocket=_pocket_dict(pocket),
            items=None,
            six_dae40=None,
            warnings=["p988 only"],
        )

    u32, label = _parse_seed(opts.seed_label or None, opts.seed_u32)
    try:
        encoded = seed_to_string(u32)
    except Exception:
        encoded = None

    profile = EdenProfile(achievement_159=opts.achievement_159)
    u32, p988, rolls, wiki = wiki_deltas_from_start_seed(u32, p3ec=opts.p3ec)
    stats: EdenStatsResult = eden_stats_from_start_seed(u32, profile)
    summary = summarize_stats(stats)
    p3ec_used = (opts.p3ec if opts.p3ec is not None else p988) & 0xFFFFFFFF

    pocket = eden_7bc740_pocket(
        p3ec_used,
        trinket_pool_path=str(pool_path) if pool_path else None,
        start_seed=u32,
        trinket_rng409=opts.trinket_rng409,
        trinket_use_cache=opts.trinket_use_cache,
    )

    trinket_meta: dict[str, Any] = {}
    if pool_path and pocket.kind == "trinket":
        pool = load_trinket_pool(pool_path)
        rng_used, rng_src = trinket_rng409_for_eden(
            u32,
            pool,
            pool_path=pool_path,
            rng409_override=opts.trinket_rng409,
            use_cache=opts.trinket_use_cache,
        )
        trinket_meta = {
            "rng409": rng_used,
            "rng_source": rng_src,
            "pool_file": pool_path.name,
        }
        if pocket.trinket_id is None and rng_src == "missing":
            warnings.append("trinket pool missing")
        elif pocket.trinket_id is None:
            warnings.append("trinket id unknown")
    elif pocket.kind == "trinket" and not pool_path:
        warnings.append("no trinket_pool.json")

    items_block: dict[str, Any] | None = None
    if not opts.skip_items:
        if proc_path is None:
            warnings.append("no proc table")
        else:
            try:
                table = load_proc_table(proc_path)
                j = eden_starting_items(
                    u32,
                    table=table,
                    trinket_pool_path=pool_path,
                    p3ec=opts.p3ec,
                )
                items_block = {
                    "passive_index": j["index_passive_v161"],
                    "active_index": j["index_active_v162"],
                    "passive_id": j["passive_id"],
                    "active_id": j["active_id"],
                    "table_count": j["table_count"],
                    "proc_file": proc_path.name,
                }
            except Exception as e:
                warnings.append(f"items failed: {e}")

    six_dae40 = {
        "outer_cases": summary["outer_cases"],
        "final_layout_case": summary["final_layout_case"],
        "stat_rolls_rad": summary["stat_rolls_rad"],
        "pickups": {
            "bombs": summary["bombs"],
            "keys": summary["keys"],
            "coins": summary["coins_pickup"],
            "empty_heart": summary["empty_heart"],
        },
        "tail_treasures_pool0": summary["treasure_items"],
        "command_count": summary["command_count"],
    }
    if opts.include_6dae40_verbose:
        six_dae40["commands"] = [
            {"type": c.cmd_type, "a3": c.a3, "a4": c.a4, "rng": c.rng}
            for c in stats.commands
        ]

    return EdenPredictResult(
        mode="seed",
        seed_label=label,
        start_seed=u32,
        encoded_seed=encoded,
        a5_113620=stats.a5_113620,
        p988=p988,
        p3ec_used=p3ec_used,
        p988_after=stats.p988_after,
        wiki_deltas=wiki,
        hearts={
            "red1232": rolls.red1232,
            "red_hud": rolls.red1232 / 2.0,
            "soul1235": rolls.soul1235,
            "cap1233": 15,
            "base_6dae40": {
                "red1232": summary["red1232"],
                "soul1235": summary["soul1235"],
            },
        },
        range_display={
            "range_game": wiki.get("rangeGame", 0),
            "range1312": wiki.get("range1312", 0),
            "range_bar": wiki.get("rangeBar", 0),
        },
        range_hint=format_range_hud_hint(rolls),
        wiki_line=format_wiki_deltas_line(rolls),
        pocket=_pocket_dict(pocket),
        items=items_block,
        six_dae40=six_dae40,
        trinket_meta=trinket_meta,
        warnings=warnings,
    )


def format_text_report(r: EdenPredictResult) -> str:
    lines: list[str] = []

    if r.mode == "p988_only":
        lines.append(f"p988={r.p3ec_used}")
    else:
        lines.append(f"seed={r.seed_label}")
        if r.encoded_seed:
            lines.append(f"enc={r.encoded_seed}")
        lines.append(f"start={r.start_seed} (0x{(r.start_seed or 0):08x})")
        lines.append(f"p988={r.p988}")

    h = r.hearts
    lines.append(f"hearts red={h['red1232']} soul={h['soul1235']} cap={h.get('cap1233', 15)}")
    lines.append(r.wiki_line)
    lines.append(r.range_hint)
    pk = r.pocket
    if pk["kind"] == "trinket":
        tid = pk.get("trinket_id")
        lines.append(f"trinket={tid if tid is not None else '?'}")
    elif pk["kind"] == "none":
        lines.append("pocket=none")
    elif pk.get("kind") in ("card", "pill"):
        from tools.game_rng import Eden7bc740Pocket
        from tools.pocket_format import format_pocket_lines

        pocket_obj = Eden7bc740Pocket(
            kind=pk["kind"],
            rng_fn=pk.get("rng_fn"),
            pickup_id=pk.get("pickup_id"),
            card_id=pk.get("card_id"),
            pill_effect=pk.get("pill_effect"),
            grant_mode=pk.get("grant_mode"),
        )
        lines.extend(format_pocket_lines(pocket_obj))
    else:
        lines.append(f"pocket={pk['kind']} id={pk.get('pickup_id')}")

    if r.items:
        it = r.items
        lines.append(f"passive={it['passive_id']} active={it['active_id']}")

    for w in r.warnings:
        lines.append(f"! {w}")

    return "\n".join(lines)
