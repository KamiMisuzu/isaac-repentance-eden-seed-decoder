from __future__ import annotations

import json
import os
import shlex
import sys
import time
from collections.abc import Iterator
from dataclasses import dataclass, field
from multiprocessing import Queue, get_context
from queue import Empty
from pathlib import Path
from typing import Any, Callable

from tools.collectible_table import ProceduralTable
from tools.eden_j460 import eden_starting_items
from tools.eden_predict import load_proc_table, resolve_proc_table_path
from tools.eden_stats import (
    EdenPanelHearts,
    eden_7bbbd0_base_panel,
    eden_7bbbd0_rolls,
    wiki_deltas_dict,
)
from tools.game_rng import eden_7bc740_pocket, p988_from_start_seed
from tools.seed_codec import (
    custom_start_seed_label,
    estimate_prefix_candidates,
    is_valid_seed_prefix,
    iter_u32_for_seed_prefix,
    normalize_seed_string,
)
from tools.trinket_eden import resolve_trinket_pool_path

try:
    from tools.eden_reverse_fast import (
        FastMatchPack,
        can_use_fast,
        fast_match_seed,
        numba_available,
        pack_criteria,
        pack_tables,
    )
except ImportError:
    numba_available = lambda: False  # type: ignore[assignment,misc]

    def pack_tables(_proc, _tri):  # type: ignore[misc]
        return None

    def pack_criteria(_criteria, tables=None):  # type: ignore[misc]
        return None

    def can_use_fast(_plan, _pack):  # type: ignore[misc]
        return False

    def fast_match_seed(_u32, _pack):  # type: ignore[misc]
        return False

    FastMatchPack = None  # type: ignore[misc,assignment]

TPL_RANGE = 6.5
STAT_EPS = 0.006
HEART_EPS = 0.01
PROGRESS_INTERVAL_SEC = 0.12
PROGRESS_EVERY_N = 40_000
WORKER_PROGRESS_INTERVAL_SEC = 0.5
WORKER_PROGRESS_EVERY_N = 500_000
DEFAULT_WORKERS = max(1, min(8, (os.cpu_count() or 4)))
_WORKER_PROGRESS_Q: Queue | None = None


def _parallel_worker_init(progress_q: Queue) -> None:
    global _WORKER_PROGRESS_Q
    _WORKER_PROGRESS_Q = progress_q


@dataclass
class EdenReverseCriteria:
    seed_prefix: str = ""
    prefix_offset: int = 0
    start_u32: int = 0
    end_u32: int = 0xFFFFFFFF
    max_results: int = 100
    max_scan: int = 20_000_000
    workers: int = 1
    achievement_159: bool = False
    proc_table: Path | None = None
    trinket_pool: Path | None = None
    red: float | None = None
    soul: float | None = None
    damage: float | None = None
    speed: float | None = None
    tears: float | None = None
    range_display: float | None = None
    shot_speed: float | None = None
    luck: float | None = None
    pocket_kind: str | None = None
    trinket_id: int | None = None
    pocket_id: int | None = None
    passive_id: int | None = None
    active_id: int | None = None

    def has_match_filters(self) -> bool:
        return any(
            v is not None
            for v in (
                self.red,
                self.soul,
                self.damage,
                self.speed,
                self.tears,
                self.range_display,
                self.shot_speed,
                self.luck,
                self.pocket_kind,
                self.trinket_id,
                self.pocket_id,
                self.passive_id,
                self.active_id,
            )
        )


@dataclass
class EdenReverseHit:
    start_seed: int
    seed_label: str
    encoded_seed: str | None = None


@dataclass
class EdenReverseResult:
    matches: list[EdenReverseHit] = field(default_factory=list)
    scanned: int = 0
    truncated: bool = False
    elapsed_sec: float = 0.0
    warnings: list[str] = field(default_factory=list)


def _parse_opt_float(v: Any) -> float | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s or s in ("±0", "—", "-"):
        return None
    if s.startswith("+"):
        s = s[1:]
    return float(s)


def _parse_opt_int(v: Any) -> int | None:
    if v is None:
        return None
    s = str(v).strip()
    if not s:
        return None
    return int(s, 0)


def _parse_workers(v: Any) -> int:
    if v is None or str(v).strip() == "":
        return DEFAULT_WORKERS
    n = int(v)
    return max(1, min(16, n))


def criteria_from_dict(d: dict[str, Any]) -> EdenReverseCriteria:
    def _hex_or_int(key: str, default: int) -> int:
        raw = d.get(key)
        if raw is None or str(raw).strip() == "":
            return default
        s = str(raw).strip().lower()
        if s.startswith("0x"):
            return int(s, 16) & 0xFFFFFFFF
        try:
            return int(s) & 0xFFFFFFFF
        except ValueError:
            return int(s, 16) & 0xFFFFFFFF

    pocket_kind = str(d.get("pocket_kind") or "").strip().lower() or None
    trinket_id = _parse_opt_int(d.get("trinket_id"))
    pocket_id = _parse_opt_int(d.get("pocket_id"))
    if pocket_kind == "trinket":
        pocket_id = None
    elif pocket_kind in ("card", "pill"):
        trinket_id = None
    elif pocket_kind == "none":
        trinket_id = None
        pocket_id = None

    def _parse_nonneg_int(key: str, default: int = 0) -> int:
        raw = d.get(key)
        if raw is None or str(raw).strip() == "":
            return default
        return max(0, int(str(raw).strip()))

    return EdenReverseCriteria(
        seed_prefix=normalize_seed_string(str(d.get("seed_prefix") or "")),
        prefix_offset=_parse_nonneg_int("prefix_offset", 0),
        start_u32=_hex_or_int("start_u32", 0),
        end_u32=_hex_or_int("end_u32", 0xFFFFFFFF),
        max_results=max(1, min(500, int(d.get("max_results") or 100))),
        max_scan=max(1, min(500_000_000, int(d.get("max_scan") or 20_000_000))),
        workers=_parse_workers(d.get("workers")),
        achievement_159=str(d.get("ach_159", "0")).lower() in ("1", "true", "yes"),
        red=_parse_opt_float(d.get("red")),
        soul=_parse_opt_float(d.get("soul")),
        damage=_parse_opt_float(d.get("damage")),
        speed=_parse_opt_float(d.get("speed")),
        tears=_parse_opt_float(d.get("tears")),
        range_display=_parse_opt_float(d.get("range")),
        shot_speed=_parse_opt_float(d.get("shotSpeed")),
        luck=_parse_opt_float(d.get("luck")),
        pocket_kind=pocket_kind,
        trinket_id=trinket_id,
        pocket_id=pocket_id,
        passive_id=_parse_opt_int(d.get("passive_id")),
        active_id=_parse_opt_int(d.get("active_id")),
    )


def describe_criteria(criteria: EdenReverseCriteria) -> dict[str, Any]:
    filter_keys = (
        "red",
        "soul",
        "damage",
        "speed",
        "tears",
        "range_display",
        "shot_speed",
        "luck",
        "pocket_kind",
        "trinket_id",
        "pocket_id",
        "passive_id",
        "active_id",
    )
    active: list[str] = []
    for key in filter_keys:
        val = getattr(criteria, key)
        if val is not None:
            active.append(f"{key}={val}")

    prefix_scan = _is_prefix_scan(criteria)
    start = criteria.start_u32 & 0xFFFFFFFF
    end = criteria.end_u32 & 0xFFFFFFFF
    if end < start:
        start, end = end, start
    span = end - start + 1
    prefix_total = estimate_prefix_candidates(criteria.seed_prefix) if prefix_scan else 0

    return {
        "mode": "filter" if criteria.has_match_filters() else "list",
        "scan_mode": "prefix" if prefix_scan else "range",
        "prefix": criteria.seed_prefix or None,
        "prefix_offset": criteria.prefix_offset if prefix_scan else None,
        "prefix_total": prefix_total if prefix_scan else None,
        "start_u32": start,
        "end_u32": end,
        "start_hex": f"0x{start:08x}",
        "end_hex": f"0x{end:08x}",
        "span": span,
        "max_scan": criteria.max_scan,
        "max_results": criteria.max_results,
        "workers": criteria.workers,
        "filters": active,
        "filter_count": len(active),
        "check_hearts": criteria.red is not None or criteria.soul is not None,
        "check_stats": any(
            getattr(criteria, k) is not None
            for k in ("damage", "speed", "tears", "range_display", "shot_speed", "luck")
        ),
        "check_pocket": _needs_pocket(criteria),
        "check_items": _needs_items(criteria),
        "ach_159": criteria.achievement_159,
        "numba": numba_available(),
    }


def _near(a: float, b: float, eps: float = STAT_EPS) -> bool:
    return abs(a - b) <= eps


def _match_stats(wiki: dict[str, float], c: EdenReverseCriteria) -> bool:
    if c.damage is not None and not _near(wiki["damage"], c.damage):
        return False
    if c.speed is not None and not _near(wiki["speed"], c.speed):
        return False
    if c.tears is not None and not _near(wiki["tears"], c.tears):
        return False
    if c.range_display is not None:
        post = wiki.get("rangeGame", 0.0) + TPL_RANGE
        if not _near(post, c.range_display):
            return False
    if c.shot_speed is not None and not _near(wiki["shotSpeed"], c.shot_speed):
        return False
    if c.luck is not None and not _near(wiki["luck"], c.luck):
        return False
    return True


def _match_hearts(rolls, c: EdenReverseCriteria) -> bool:
    if c.red is not None and not _near(rolls.red1232 / 2.0, c.red, HEART_EPS):
        return False
    if c.soul is not None and not _near(rolls.soul1235 / 2.0, c.soul, HEART_EPS):
        return False
    return True


def _match_hearts_panel(panel: EdenPanelHearts, c: EdenReverseCriteria) -> bool:
    if c.red is not None and not _near(panel.red1232 / 2.0, c.red, HEART_EPS):
        return False
    if c.soul is not None and not _near(panel.soul1235 / 2.0, c.soul, HEART_EPS):
        return False
    return True


def _match_pocket(pocket, c: EdenReverseCriteria) -> bool:
    from tools.pocket_lookup import pocket_hud_item_id, pocket_hud_kind

    hud_kind = pocket_hud_kind(pocket)
    if c.pocket_kind is not None and hud_kind != c.pocket_kind:
        return False
    if c.trinket_id is not None:
        if hud_kind != "trinket" or pocket.trinket_id != c.trinket_id:
            return False
    if c.pocket_id is not None:
        if pocket_hud_item_id(pocket) != c.pocket_id:
            return False
    return True


def _needs_pocket(c: EdenReverseCriteria) -> bool:
    return any(
        x is not None
        for x in (c.pocket_kind, c.trinket_id, c.pocket_id)
    )


def _needs_items(c: EdenReverseCriteria) -> bool:
    return c.passive_id is not None or c.active_id is not None


def _is_prefix_scan(criteria: EdenReverseCriteria) -> bool:
    return bool(criteria.seed_prefix) and is_valid_seed_prefix(criteria.seed_prefix)


@dataclass
class _ScanPlan:
    need_match: bool
    check_hearts: bool
    check_stats: bool
    need_pocket: bool
    need_items: bool
    use_prefix: bool
    use_prefix_iter: bool
    use_fast: bool
    fast_pack: Any = None


def _scan_plan(
    criteria: EdenReverseCriteria,
    *,
    proc_table: ProceduralTable | None,
    trinket_path: str | Path | None,
    start: int,
    end: int,
) -> _ScanPlan:
    need_match = criteria.has_match_filters()
    check_hearts = criteria.red is not None or criteria.soul is not None
    check_stats = any(
        getattr(criteria, k) is not None
        for k in ("damage", "speed", "tears", "range_display", "shot_speed", "luck")
    )
    use_prefix = _is_prefix_scan(criteria)
    fast_tables = pack_tables(proc_table, trinket_path)
    fast_pack = pack_criteria(criteria, fast_tables)
    plan = _ScanPlan(
        need_match=need_match,
        check_hearts=check_hearts,
        check_stats=check_stats,
        need_pocket=_needs_pocket(criteria),
        need_items=_needs_items(criteria) and proc_table is not None,
        use_prefix=use_prefix,
        use_prefix_iter=use_prefix,
        use_fast=False,
        fast_pack=fast_pack,
    )
    plan.use_fast = can_use_fast(plan, fast_pack) if fast_pack is not None else False
    return plan


def _iter_scan_u32(
    plan: _ScanPlan,
    prefix: str,
    *,
    range_start: int,
    range_end: int,
    prefix_offset: int = 0,
    prefix_limit: int | None = None,
) -> Iterator[int]:
    if plan.use_prefix_iter:
        yield from iter_u32_for_seed_prefix(prefix, offset=prefix_offset, limit=prefix_limit)
    else:
        for u32 in range(range_start, range_end + 1):
            yield u32


def _seed_label(u32: int) -> str | None:
    return custom_start_seed_label(u32)


def _load_tables_in_worker(
    proc_path: str | None,
    trinket_path: str | None,
) -> tuple[ProceduralTable | None, str | None]:
    table = None
    if proc_path and Path(proc_path).is_file():
        table = load_proc_table(Path(proc_path))
    tri = trinket_path if trinket_path and Path(trinket_path).is_file() else None
    return table, tri


def _seed_matches(
    u32: int,
    criteria: EdenReverseCriteria,
    plan: _ScanPlan,
    *,
    proc_table: ProceduralTable | None,
    trinket_pool_path: str | None,
) -> str | None:
    if not plan.need_match:
        return _seed_label(u32)

    if plan.use_fast and plan.fast_pack is not None:
        if not fast_match_seed(u32, plan.fast_pack):
            return None
        return _seed_label(u32)

    p988 = p988_from_start_seed(u32)

    if plan.check_stats:
        rolls = eden_7bbbd0_rolls(p988)
        if plan.check_hearts and not _match_hearts(rolls, criteria):
            return None
        wiki = wiki_deltas_dict(rolls)
        if not _match_stats(wiki, criteria):
            return None
    elif plan.check_hearts:
        panel = eden_7bbbd0_base_panel(p988)
        if not _match_hearts_panel(panel, criteria):
            return None

    if plan.need_pocket:
        pocket = eden_7bc740_pocket(
            p988,
            trinket_pool_path=trinket_pool_path,
            start_seed=u32,
        )
        if not _match_pocket(pocket, criteria):
            return None

    if plan.need_items and proc_table is not None:
        j = eden_starting_items(
            u32,
            table=proc_table,
            trinket_pool_path=Path(trinket_pool_path) if trinket_pool_path else None,
        )
        if criteria.passive_id is not None and j["passive_id"] != criteria.passive_id:
            return None
        if criteria.active_id is not None and j["active_id"] != criteria.active_id:
            return None

    return _seed_label(u32)


def _scan_chunk_worker(payload: dict[str, Any]) -> dict[str, Any]:
    import sys

    root = Path(__file__).resolve().parent.parent
    if str(root) not in sys.path:
        sys.path.insert(0, str(root))

    criteria = criteria_from_dict(payload["criteria"])
    chunk_start = payload["chunk_start"]
    chunk_end = payload["chunk_end"]
    chunk_budget = payload["chunk_budget"]
    hit_cap = payload["hit_cap"]
    prefix_offset = int(payload.get("prefix_offset") or 0)
    prefix_limit = payload.get("prefix_limit")
    proc_path = payload.get("proc_path")
    trinket_path = payload.get("trinket_path")

    proc_table, tri = _load_tables_in_worker(proc_path, trinket_path)
    plan = _scan_plan(criteria, proc_table=proc_table, trinket_path=tri, start=chunk_start, end=chunk_end)
    prefix = criteria.seed_prefix

    hits: list[dict[str, Any]] = []
    scanned = 0
    truncated = False
    progress_q = _WORKER_PROGRESS_Q
    chunk_id = payload["chunk_id"]
    last_worker_progress = 0.0
    last_u32 = chunk_start

    for u32 in _iter_scan_u32(
        plan,
        prefix,
        range_start=chunk_start,
        range_end=chunk_end,
        prefix_offset=prefix_offset,
        prefix_limit=prefix_limit,
    ):
        last_u32 = u32
        scanned += 1
        if scanned > chunk_budget:
            truncated = True
            break

        label = _seed_matches(
            u32,
            criteria,
            plan,
            proc_table=proc_table,
            trinket_pool_path=tri,
        )
        if label is not None:
            hits.append({"seed": label, "start_seed": u32})
            if progress_q is not None:
                try:
                    progress_q.put_nowait(
                        {
                            "chunk_id": chunk_id,
                            "scanned": scanned,
                            "current_u32": u32,
                            "hits": len(hits),
                        }
                    )
                except Exception:
                    pass
                last_worker_progress = time.perf_counter()
            if len(hits) >= hit_cap:
                break
            continue

        now = time.perf_counter()
        if progress_q is not None and (
            scanned == 1
            or now - last_worker_progress >= WORKER_PROGRESS_INTERVAL_SEC
            or scanned % WORKER_PROGRESS_EVERY_N == 0
        ):
            try:
                progress_q.put_nowait(
                    {
                        "chunk_id": chunk_id,
                        "scanned": scanned,
                        "current_u32": u32,
                        "hits": len(hits),
                    }
                )
            except Exception:
                pass
            last_worker_progress = now

    return {
        "chunk_id": payload["chunk_id"],
        "hits": hits,
        "scanned": scanned,
        "truncated": truncated,
        "end_u32": chunk_end,
        "last_u32": last_u32,
        "chunk_start": chunk_start,
    }


def _round_window_end(start: int, end: int, max_scan: int) -> int:
    span = end - start + 1
    if max_scan <= 0 or max_scan >= span:
        return end
    return (start + max_scan - 1) & 0xFFFFFFFF


def _prefix_round_limit(prefix_offset: int, prefix_total: int, max_scan: int) -> int:
    remaining = max(0, prefix_total - prefix_offset)
    if max_scan <= 0:
        return remaining
    return min(max_scan, remaining)


def _prefix_done_meta(prefix_offset: int, scanned: int, prefix_total: int) -> dict[str, Any]:
    next_offset = prefix_offset + scanned
    can_continue = next_offset < prefix_total
    return {
        "scan_mode": "prefix",
        "last_u32": 0,
        "last_hex": "0x00000000",
        "prefix_offset": prefix_offset,
        "next_prefix_offset": next_offset,
        "prefix_total": prefix_total,
        "next_start_u32": 0,
        "next_start_hex": "0x00000000",
        "can_continue": can_continue,
        "range_end_u32": 0xFFFFFFFF,
        "range_end_hex": "0xffffffff",
    }


def _reverse_done_meta(start: int, end: int, last_u32: int) -> dict[str, Any]:
    next_start = (int(last_u32) + 1) & 0xFFFFFFFF
    can_continue = next_start <= end
    return {
        "scan_mode": "range",
        "last_u32": int(last_u32) & 0xFFFFFFFF,
        "last_hex": f"0x{int(last_u32) & 0xFFFFFFFF:08x}",
        "next_start_u32": next_start,
        "next_start_hex": f"0x{next_start:08x}",
        "can_continue": can_continue,
        "range_end_u32": end,
        "range_end_hex": f"0x{end:08x}",
    }


def _split_prefix_chunks(prefix_offset: int, prefix_limit: int, workers: int) -> list[tuple[int, int]]:
    span = prefix_limit
    if span <= 0:
        return []
    workers = max(1, min(workers, span))
    chunk = span // workers
    rem = span % workers
    chunks: list[tuple[int, int]] = []
    cur = prefix_offset
    for i in range(workers):
        size = chunk + (1 if i < rem else 0)
        if size <= 0:
            break
        chunks.append((cur, size))
        cur += size
    return chunks


def _parallel_next_start(chunks: list[tuple[int, int]], results: list[dict[str, Any]], start: int) -> int:
    by_id = {r["chunk_id"]: r for r in results}
    next_start = start
    for i, (cs, ce) in enumerate(chunks):
        r = by_id.get(i)
        if r is None:
            return cs
        chunk_span = ce - cs + 1
        if r.get("truncated") or r["scanned"] < chunk_span:
            last = int(r.get("last_u32", cs - 1)) & 0xFFFFFFFF
            return (last + 1) & 0xFFFFFFFF
        next_start = (ce + 1) & 0xFFFFFFFF
    return next_start


def _split_chunks(start: int, end: int, workers: int) -> list[tuple[int, int]]:
    span = end - start + 1
    workers = max(1, min(workers, span))
    chunk = span // workers
    rem = span % workers
    chunks: list[tuple[int, int]] = []
    cur = start
    for i in range(workers):
        size = chunk + (1 if i < rem else 0)
        if size <= 0:
            break
        chunks.append((cur, cur + size - 1))
        cur += size
    return chunks


def _progress_payload(
    *,
    scanned: int,
    current_u32: int,
    hits: int,
    t0: float,
    criteria: EdenReverseCriteria,
    start: int,
    end: int,
    phase: str,
    workers: int = 1,
    budget: int | None = None,
) -> dict[str, Any]:
    elapsed = time.perf_counter() - t0
    rate = scanned / elapsed if elapsed > 0 else 0
    if budget is None:
        span = end - start + 1
        budget = min(span, criteria.max_scan)
    pct = min(100.0, scanned / budget * 100) if budget else 0
    return {
        "type": "progress",
        "scanned": scanned,
        "current_u32": current_u32,
        "current_hex": f"0x{current_u32 & 0xFFFFFFFF:08x}",
        "current_seed": _seed_label(current_u32) if scanned == 1 or scanned % 250_000 == 0 else None,
        "hits": hits,
        "elapsed_sec": round(elapsed, 2),
        "rate": int(rate),
        "percent": round(pct, 1),
        "phase": phase,
        "workers": workers,
    }


def _iter_reverse_serial(
    criteria: EdenReverseCriteria,
    *,
    proc_table: ProceduralTable | None,
    trinket_pool_path: Path | None,
    start: int,
    end: int,
    warnings: list[str],
    t0: float,
) -> Iterator[dict[str, Any]]:
    need_match = criteria.has_match_filters()
    pool_s = str(trinket_pool_path) if trinket_pool_path else None
    plan = _scan_plan(criteria, proc_table=proc_table, trinket_path=pool_s, start=start, end=end)
    prefix = criteria.seed_prefix
    phase = "prefix" if plan.use_prefix else ("list" if not need_match else "match")
    if plan.use_prefix_iter:
        phase = f"prefix enum {normalize_seed_string(prefix)}"

    matches: list[EdenReverseHit] = []
    scanned = 0
    last_progress = 0.0
    prefix_total = estimate_prefix_candidates(prefix) if plan.use_prefix_iter else 0
    prefix_offset = criteria.prefix_offset
    prefix_limit = _prefix_round_limit(prefix_offset, prefix_total, criteria.max_scan)
    window_end = _round_window_end(start, end, criteria.max_scan)
    last_u32 = start

    for u32 in _iter_scan_u32(
        plan,
        prefix,
        range_start=start,
        range_end=window_end,
        prefix_offset=prefix_offset,
        prefix_limit=prefix_limit,
    ):
        last_u32 = u32
        scanned += 1
        now = time.perf_counter()
        if scanned == 1 or now - last_progress >= PROGRESS_INTERVAL_SEC or scanned % PROGRESS_EVERY_N == 0:
            yield _progress_payload(
                scanned=scanned,
                current_u32=u32,
                hits=len(matches),
                t0=t0,
                criteria=criteria,
                start=start,
                end=end,
                phase=phase,
                workers=1,
                budget=prefix_limit if plan.use_prefix_iter else None,
            )
            last_progress = now

        label = _seed_matches(
            u32,
            criteria,
            plan,
            proc_table=proc_table,
            trinket_pool_path=pool_s,
        )
        if label is None:
            continue

        matches.append(EdenReverseHit(start_seed=u32, seed_label=label, encoded_seed=label))
        yield {"type": "hit", "seed": label, "start_seed": u32}
        if len(matches) >= criteria.max_results:
            break

    if plan.use_prefix_iter:
        done_meta = _prefix_done_meta(prefix_offset, scanned, prefix_total)
    else:
        done_meta = _reverse_done_meta(start, end, last_u32 if scanned else (start - 1) & 0xFFFFFFFF)
    rows = [{"seed": h.seed_label, "start_seed": h.start_seed} for h in matches]
    yield {
        "type": "done",
        "ok": True,
        "matches": rows,
        "count": len(rows),
        "scanned": scanned,
        "truncated": done_meta["can_continue"],
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "warnings": warnings,
        "window_end_u32": window_end,
        "window_end_hex": f"0x{window_end:08x}",
        **done_meta,
    }


def _iter_reverse_parallel(
    criteria: EdenReverseCriteria,
    *,
    proc_table: ProceduralTable | None,
    trinket_pool_path: Path | None,
    proc_path: Path | None,
    start: int,
    end: int,
    warnings: list[str],
    t0: float,
) -> Iterator[dict[str, Any]]:
    workers = criteria.workers
    prefix_scan = _is_prefix_scan(criteria)
    prefix_total = estimate_prefix_candidates(criteria.seed_prefix) if prefix_scan else 0
    prefix_offset = criteria.prefix_offset
    prefix_limit = _prefix_round_limit(prefix_offset, prefix_total, criteria.max_scan)
    window_end = _round_window_end(start, end, criteria.max_scan)
    if prefix_scan:
        prefix_chunks = _split_prefix_chunks(prefix_offset, prefix_limit, workers)
        chunks = [(0, 0) for _ in prefix_chunks]
    else:
        prefix_chunks = []
        chunks = _split_chunks(start, window_end, workers)
    per_chunk_hits = max(1, (criteria.max_results + len(chunks) - 1) // len(chunks))

    proc_path_str = str(proc_path) if proc_path and Path(proc_path).is_file() else None
    tri_path_str = str(trinket_pool_path) if trinket_pool_path else None

    raw_criteria = {
        k: v
        for k, v in {
            "seed_prefix": criteria.seed_prefix,
            "prefix_offset": criteria.prefix_offset,
            "start_u32": criteria.start_u32,
            "end_u32": criteria.end_u32,
            "max_results": criteria.max_results,
            "max_scan": criteria.max_scan,
            "ach_159": "1" if criteria.achievement_159 else "0",
            "red": criteria.red,
            "soul": criteria.soul,
            "damage": criteria.damage,
            "speed": criteria.speed,
            "tears": criteria.tears,
            "range": criteria.range_display,
            "shotSpeed": criteria.shot_speed,
            "luck": criteria.luck,
            "pocket_kind": criteria.pocket_kind,
            "trinket_id": criteria.trinket_id,
            "pocket_id": criteria.pocket_id,
            "passive_id": criteria.passive_id,
            "active_id": criteria.active_id,
        }.items()
        if v is not None and v != ""
    }

    payloads = []
    chunk_results: list[dict[str, Any]] = []
    if prefix_scan:
        for i, (poff, plim) in enumerate(prefix_chunks):
            payloads.append(
                {
                    "chunk_id": i,
                    "chunk_start": 0,
                    "chunk_end": 0,
                    "chunk_budget": plim,
                    "prefix_offset": poff,
                    "prefix_limit": plim,
                    "hit_cap": per_chunk_hits,
                    "criteria": raw_criteria,
                    "proc_path": proc_path_str,
                    "trinket_path": tri_path_str,
                }
            )
    else:
        for i, (cs, ce) in enumerate(chunks):
            payloads.append(
                {
                    "chunk_id": i,
                    "chunk_start": cs,
                    "chunk_end": ce,
                    "chunk_budget": ce - cs + 1,
                    "hit_cap": per_chunk_hits,
                    "criteria": raw_criteria,
                    "proc_path": proc_path_str,
                    "trinket_path": tri_path_str,
                }
            )

    all_hits: list[dict[str, Any]] = []
    truncated = False
    done_chunks = 0
    last_progress = 0.0
    chunk_live: dict[int, dict[str, int]] = {}
    chunk_done_scanned: dict[int, int] = {}
    last_current_u32 = start

    def _total_scanned() -> int:
        return sum(chunk_done_scanned.values()) + sum(
            v["scanned"] for v in chunk_live.values()
        )

    def _emit_parallel_progress(phase: str, *, force: bool = False) -> Iterator[dict[str, Any]]:
        nonlocal last_progress, last_current_u32
        now = time.perf_counter()
        if not force and now - last_progress < PROGRESS_INTERVAL_SEC:
            return
        total = min(_total_scanned(), criteria.max_scan)
        cur = last_current_u32
        yield _progress_payload(
            scanned=total,
            current_u32=cur,
            hits=len(all_hits),
            t0=t0,
            criteria=criteria,
            start=start,
            end=end,
            phase=phase,
            workers=len(chunks),
            budget=prefix_limit if prefix_scan else None,
        )
        last_progress = now

    yield _progress_payload(
        scanned=0,
        current_u32=start,
        hits=0,
        t0=t0,
        criteria=criteria,
        start=start,
        end=end,
        phase=f"parallel×{len(chunks)}",
        workers=len(chunks),
        budget=prefix_limit if prefix_scan else None,
    )

    mp_ctx = get_context("spawn")
    progress_q: Queue = mp_ctx.Queue()
    pool = mp_ctx.Pool(len(chunks), initializer=_parallel_worker_init, initargs=(progress_q,))
    pending: list[Any] = []
    try:
        async_results = [pool.apply_async(_scan_chunk_worker, (p,)) for p in payloads]
        pending = list(async_results)

        while pending:
            while True:
                try:
                    msg = progress_q.get_nowait()
                except Empty:
                    break
                chunk_live[msg["chunk_id"]] = msg
                last_current_u32 = msg["current_u32"]

            yield from _emit_parallel_progress(
                f"parallel {done_chunks}/{len(chunks)}",
            )

            still_pending: list[Any] = []
            stop = False
            for ar in pending:
                if ar.ready():
                    result = ar.get()
                    chunk_results.append(result)
                    done_chunks += 1
                    chunk_id = result["chunk_id"]
                    chunk_live.pop(chunk_id, None)
                    chunk_done_scanned[chunk_id] = result["scanned"]
                    last_current_u32 = result["end_u32"]
                    truncated = truncated or result["truncated"]
                    for hit in result["hits"]:
                        if len(all_hits) >= criteria.max_results:
                            break
                        all_hits.append(hit)
                        yield {"type": "hit", **hit}

                    yield from _emit_parallel_progress(
                        f"parallel {done_chunks}/{len(chunks)}",
                        force=True,
                    )

                    if len(all_hits) >= criteria.max_results:
                        stop = True
                        break
                    if _total_scanned() >= criteria.max_scan:
                        truncated = True
                        stop = True
                        break
                else:
                    still_pending.append(ar)
            if stop:
                pending.clear()
                break
            pending = still_pending
            if pending:
                time.sleep(PROGRESS_INTERVAL_SEC)
    finally:
        if pending:
            pool.terminate()
        else:
            pool.close()
        pool.join()

    scanned = min(_total_scanned(), criteria.max_scan)

    all_hits.sort(key=lambda h: h["start_seed"])
    all_hits = all_hits[: criteria.max_results]
    if prefix_scan:
        done_meta = _prefix_done_meta(prefix_offset, scanned, prefix_total)
    else:
        next_start = _parallel_next_start(chunks, chunk_results, start)
        last_u32 = (next_start - 1) & 0xFFFFFFFF if next_start > start else (start - 1) & 0xFFFFFFFF
        if scanned == 0:
            last_u32 = (start - 1) & 0xFFFFFFFF
        done_meta = _reverse_done_meta(start, end, last_u32)
    yield {
        "type": "done",
        "ok": True,
        "matches": all_hits,
        "count": len(all_hits),
        "scanned": min(scanned, criteria.max_scan),
        "truncated": done_meta["can_continue"],
        "elapsed_sec": round(time.perf_counter() - t0, 2),
        "warnings": warnings,
        "window_end_u32": window_end,
        "window_end_hex": f"0x{window_end:08x}",
        **done_meta,
    }


def iter_reverse_search(
    criteria: EdenReverseCriteria,
    *,
    proc_table: ProceduralTable | None = None,
    trinket_pool_path: Path | None = None,
    proc_path: Path | None = None,
) -> Iterator[dict[str, Any]]:
    warnings: list[str] = []
    if _needs_items(criteria) and proc_table is None:
        warnings.append("missing proc table")
    if (criteria.trinket_id is not None or criteria.pocket_kind == "trinket") and not trinket_pool_path:
        warnings.append("missing trinket pool")

    prefix_scan = _is_prefix_scan(criteria)
    start = criteria.start_u32 & 0xFFFFFFFF
    end = criteria.end_u32 & 0xFFFFFFFF
    if end < start:
        start, end = end, start

    if proc_path:
        criteria.proc_table = proc_path

    info = describe_criteria(criteria)
    yield {
        "type": "start",
        "plan": info,
        "warnings": warnings,
    }

    t0 = time.perf_counter()
    if prefix_scan:
        prefix_limit = _prefix_round_limit(
            criteria.prefix_offset,
            estimate_prefix_candidates(criteria.seed_prefix),
            criteria.max_scan,
        )
        use_parallel = criteria.workers > 1 and prefix_limit >= criteria.workers * 1000
    else:
        use_parallel = criteria.workers > 1 and (end - start) >= criteria.workers * 1000

    if use_parallel:
        yield from _iter_reverse_parallel(
            criteria,
            proc_table=proc_table,
            trinket_pool_path=trinket_pool_path,
            proc_path=proc_path,
            start=start,
            end=end,
            warnings=warnings,
            t0=t0,
        )
    else:
        yield from _iter_reverse_serial(
            criteria,
            proc_table=proc_table,
            trinket_pool_path=trinket_pool_path,
            start=start,
            end=end,
            warnings=warnings,
            t0=t0,
        )


def _terminal_print_start(
    raw: dict[str, Any],
    *,
    proc_path: Path | None,
    trinket_path: Path | None,
    source: str = "cli",
) -> None:
    if source == "cli":
        cmd = format_reverse_cli_command(raw, proc_path=proc_path, trinket_path=trinket_path)
        _terminal_print(f"reverse {cmd}")
    else:
        shown = {k: v for k, v in raw.items() if k != "stream" and v not in (None, "")}
        _terminal_print(f"reverse {json.dumps(shown, ensure_ascii=False, sort_keys=True)}")


def log_reverse_event(event: dict[str, Any], *, hit_index: int | None = None) -> int | None:
    t = event.get("type")
    if t == "start":
        for w in event.get("warnings") or []:
            _terminal_print(f"reverse ! {w}")
        return hit_index
    if t == "progress":
        seed_part = f" seed={event['current_seed']}" if event.get("current_seed") else ""
        w_part = f" workers={event['workers']}" if event.get("workers", 1) > 1 else ""
        _terminal_print(
            f"reverse {event.get('percent', 0):5.1f}% "
            f"scanned={event.get('scanned')} hits={event.get('hits')} "
            f"{event.get('rate')}/s {event.get('elapsed_sec')}s "
            f"u32={event.get('current_hex')}{seed_part}{w_part}"
        )
        return hit_index
    if t == "hit":
        hit_index = (hit_index or 0) + 1
        _terminal_print(
            f"reverse hit #{hit_index}: {event.get('seed')} "
            f"(0x{int(event.get('start_seed', 0)) & 0xFFFFFFFF:08x})"
        )
        return hit_index
    if t == "done":
        _terminal_print(
            f"reverse done count={event.get('count')} "
            f"scanned={event.get('scanned')} "
            f"elapsed={event.get('elapsed_sec')}s"
        )
        for w in event.get("warnings") or []:
            _terminal_print(f"reverse ! {w}")
        return hit_index
    return hit_index


def search_eden_seeds(
    criteria: EdenReverseCriteria,
    *,
    proc_table: ProceduralTable | None = None,
    trinket_pool_path: Path | None = None,
    on_event: Callable[[dict[str, Any]], None] | None = None,
) -> EdenReverseResult:
    result = EdenReverseResult()
    for event in iter_reverse_search(
        criteria,
        proc_table=proc_table,
        trinket_pool_path=trinket_pool_path,
    ):
        if on_event:
            on_event(event)
        if event.get("type") == "hit":
            result.matches.append(
                EdenReverseHit(
                    start_seed=event["start_seed"],
                    seed_label=event["seed"],
                )
            )
        elif event.get("type") == "done":
            result.scanned = event["scanned"]
            result.truncated = event["truncated"]
            result.elapsed_sec = event["elapsed_sec"]
            result.warnings = event.get("warnings", [])
    return result


def _load_tables(
    raw: dict[str, Any],
    *,
    proc_path: Path | None = None,
    trinket_path: Path | None = None,
) -> tuple[EdenReverseCriteria, ProceduralTable | None, Path | None, Path | None]:
    criteria = criteria_from_dict(raw)
    proc_path = proc_path or resolve_proc_table_path(None)
    trinket_path = trinket_path or resolve_trinket_pool_path(None)
    table = None
    if proc_path and proc_path.is_file():
        table = load_proc_table(proc_path)
    return criteria, table, proc_path, trinket_path


_CLI_FLAG_MAP: tuple[tuple[str, str, str], ...] = (
    ("seed_prefix", "prefix", "str"),
    ("start_u32", "start", "hex"),
    ("end_u32", "end", "hex"),
    ("max_results", "max-results", "int"),
    ("max_scan", "max-scan", "int"),
    ("workers", "workers", "int"),
    ("red", "red", "float"),
    ("soul", "soul", "float"),
    ("damage", "damage", "float"),
    ("speed", "speed", "float"),
    ("tears", "tears", "float"),
    ("range", "range", "float"),
    ("shotSpeed", "shot-speed", "float"),
    ("luck", "luck", "float"),
    ("pocket_kind", "pocket-kind", "str"),
    ("trinket_id", "trinket-id", "int"),
    ("pocket_id", "pocket-id", "int"),
    ("passive_id", "passive-id", "int"),
    ("active_id", "active-id", "int"),
)


def _fmt_cli_value(kind: str, value: Any) -> str:
    if kind == "hex":
        s = str(value).strip().lower()
        n = int(s, 16) if s.startswith("0x") else int(s, 16 if not s.isdecimal() else 10)
        n &= 0xFFFFFFFF
        return hex(n) if n > 0xFFFF else str(n)
    if kind == "float":
        return str(value)
    return str(value)


def format_reverse_cli_command(
    raw: dict[str, Any],
    *,
    proc_path: Path | None = None,
    trinket_path: Path | None = None,
    script: Path | None = None,
) -> str:
    script = script or Path(__file__).resolve().parent.parent / "predict_eden.py"
    parts = [sys.executable, str(script), "--reverse"]
    for key, flag, kind in _CLI_FLAG_MAP:
        if key not in raw:
            continue
        val = raw.get(key)
        if val is None or str(val).strip() == "":
            continue
        parts.extend([f"--{flag}", _fmt_cli_value(kind, val)])
    if str(raw.get("ach_159", "0")).lower() in ("1", "true", "yes"):
        parts.append("--ach-159")
    if proc_path:
        parts.extend(["--table", str(proc_path)])
    if trinket_path:
        parts.extend(["--trinket-pool", str(trinket_path)])
    return " ".join(shlex.quote(p) for p in parts)


def _terminal_print(msg: str) -> None:
    print(msg, file=sys.stderr, flush=True)


def iter_reverse_search_from_raw(
    raw: dict[str, Any],
    *,
    proc_path: Path | None = None,
    trinket_path: Path | None = None,
    log_terminal: bool = False,
    log_source: str = "cli",
) -> Iterator[dict[str, Any]]:
    criteria, table, proc_path, trinket_path = _load_tables(
        raw, proc_path=proc_path, trinket_path=trinket_path
    )
    if log_terminal:
        _terminal_print_start(
            raw,
            proc_path=proc_path,
            trinket_path=trinket_path,
            source=log_source,
        )
    hit_index: int | None = None
    for event in iter_reverse_search(
        criteria,
        proc_table=table,
        trinket_pool_path=trinket_path,
        proc_path=proc_path,
    ):
        if log_terminal:
            hit_index = log_reverse_event(event, hit_index=hit_index)
        yield event


def reverse_search(
    raw: dict[str, Any],
    *,
    proc_path: Path | None = None,
    trinket_path: Path | None = None,
    log_terminal: bool = False,
    log_source: str = "cli",
) -> dict[str, Any]:
    done: dict[str, Any] | None = None
    for event in iter_reverse_search_from_raw(
        raw,
        proc_path=proc_path,
        trinket_path=trinket_path,
        log_terminal=log_terminal,
        log_source=log_source,
    ):
        if event.get("type") == "done":
            done = event
    if done is None:
        raise RuntimeError("reverse search produced no result")
    return {
        "ok": True,
        "matches": done["matches"],
        "count": done["count"],
        "scanned": done["scanned"],
        "truncated": done["truncated"],
        "elapsed_sec": done["elapsed_sec"],
        "warnings": done.get("warnings", []),
        "plan": describe_criteria(criteria_from_dict(raw)),
    }
