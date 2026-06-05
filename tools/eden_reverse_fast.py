from __future__ import annotations

from pathlib import Path
from typing import Any

import numpy as np

try:
    from numba import njit

    _NUMBA_OK = True
except ImportError:
    _NUMBA_OK = False

    def njit(*args: Any, **kwargs: Any):  # type: ignore[misc]
        def _wrap(fn: Any) -> Any:
            return fn

        if args and callable(args[0]):
            return args[0]
        return _wrap


QWORD_9EB880 = 98784247811
DWORD_9EB880 = 25
QWORD_B1F504 = 47244640257
DWORD_B1F50C = 16
QWORD_7BC740_EDEN = 21474836481
DWORD_7BC740_EDEN = 19
QWORD_734180_PILL = 12884901891
DWORD_734180_PILL = 29
QWORD_POOL_INIT = 38654705665
DWORD_POOL_INIT = 29
QWORD_TRINKET_RETRY = 38654705669
DWORD_TRINKET_RETRY = 7
EDEN_S1 = QWORD_7BC740_EDEN & 0xFFFFFFFF
EDEN_S2 = (QWORD_7BC740_EDEN >> 32) & 0xFFFFFFFF
EDEN_S3 = DWORD_7BC740_EDEN & 0xFFFFFFFF

TPL_RANGE = 6.5
STAT_EPS = 0.006
HEART_EPS = 0.01
RANGE_GAME_SCALE = 40.0
FLOAT_U32 = 2.3283062e-10
_FILTER_OFF = 1.0e9
_FILTER_I_OFF = -1

PK_NONE = 0
PK_TRINKET = 1
PK_CARD = 2
PK_PILL = 3

_POCKET_KIND = {"none": PK_NONE, "trinket": PK_TRINKET, "card": PK_CARD, "pill": PK_PILL}


@njit(cache=True)
def _mix_qword_dword(seed: int, qword: int, third: int) -> int:
    s1 = qword & 0xFFFFFFFF
    s2 = (qword >> 32) & 0xFFFFFFFF
    s3 = third & 0xFFFFFFFF
    s = seed & 0xFFFFFFFF
    t = (s ^ (s >> s1)) & 0xFFFFFFFF
    t = (t ^ ((t << s2) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return (t ^ (t >> s3)) & 0xFFFFFFFF


@njit(cache=True)
def _eden_rng_step(seed: int) -> int:
    return _mix_qword_dword(seed, QWORD_7BC740_EDEN, DWORD_7BC740_EDEN)


@njit(cache=True)
def _rng_next_int(seed: int, s1: int, s2: int, s3: int, bound: int) -> tuple[int, int]:
    qword = (s1 & 0xFFFFFFFF) | ((s2 & 0xFFFFFFFF) << 32)
    nseed = _mix_qword_dword(seed, qword, s3)
    if bound <= 0:
        return nseed, 0
    return nseed, nseed % bound


@njit(cache=True)
def _eden_cfg_mix(seed: int) -> int:
    return _mix_qword_dword(seed, QWORD_7BC740_EDEN, DWORD_7BC740_EDEN)


@njit(cache=True)
def _eden_cfg_mix_v69_v28(v69: int, v28: int) -> int:
    t = (v69 ^ (v28 >> EDEN_S1)) & 0xFFFFFFFF
    u = (t ^ ((t << EDEN_S2) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return (u ^ (u >> EDEN_S3)) & 0xFFFFFFFF


@njit(cache=True)
def _eden_stat_rng_step(seed: int) -> int:
    term = (seed ^ (seed >> EDEN_S1)) & 0xFFFFFFFF
    mid = (term ^ ((term << EDEN_S2) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return (mid ^ (mid >> EDEN_S3)) & 0xFFFFFFFF


@njit(cache=True)
def _u32_to_float01(u: int) -> float:
    return (u & 0xFFFFFFFF) * FLOAT_U32


@njit(cache=True)
def _mix_734900(seed: int) -> int:
    a = seed & 0xFFFFFFFF
    t = (a ^ (a >> 2)) & 0xFFFFFFFF
    t = (t ^ (((a ^ (a >> 2)) << 7) & 0xFFFFFFFF)) & 0xFFFFFFFF
    return (t ^ (t >> 9)) & 0xFFFFFFFF


@njit(cache=True)
def a5_from_u32(u32: int) -> int:
    s = u32 & 0xFFFFFFFF
    for _ in range(15):
        s = _mix_qword_dword(s, QWORD_9EB880, DWORD_9EB880)
    return s & 0xFFFFFFFF


@njit(cache=True)
def p988_from_u32(u32: int) -> int:
    s = a5_from_u32(u32)
    for _ in range(5):
        s = _mix_qword_dword(s, QWORD_B1F504, DWORD_B1F50C)
    return s & 0xFFFFFFFF


@njit(cache=True)
def trinket_rng409_from_u32(u32: int) -> int:
    a5 = a5_from_u32(u32)
    s = _mix_qword_dword(a5, QWORD_9EB880, DWORD_9EB880)
    s = _mix_qword_dword(s, QWORD_9EB880, DWORD_9EB880)
    return _mix_qword_dword(s, QWORD_POOL_INIT, DWORD_POOL_INIT) & 0xFFFFFFFF


@njit(cache=True)
def _rng7e9020(state: int, shr: int, shl: int, fin: int, bound: int) -> tuple[int, int]:
    s = state & 0xFFFFFFFF
    t = (s ^ (s >> shr)) & 0xFFFFFFFF
    t = (t ^ ((t << shl) & 0xFFFFFFFF)) & 0xFFFFFFFF
    t = (t ^ (t >> fin)) & 0xFFFFFFFF
    if bound > 0:
        return t, t % bound
    return t, 0


@njit(cache=True)
def roll_trinket_id(
    rng409: int,
    tri_raw: np.ndarray,
    tri_ok: np.ndarray,
    tri_count: int,
    shr: int,
    shl: int,
    fin: int,
) -> int:
    n = tri_count
    if n <= 0:
        return 0
    state, idx = _rng7e9020(rng409, shr, shl, fin, n)
    v5 = state
    max_tries = max(1, n >> 1)
    for _ in range(max_tries):
        if 0 <= idx < n and tri_ok[idx] != 0:
            return int(tri_raw[idx])
        v5 = _mix_qword_dword(v5, QWORD_TRINKET_RETRY, DWORD_TRINKET_RETRY)
        idx = v5 % n if n else 0
    state, idx = _rng7e9020(state, shr, shl, fin, n)
    for off in range(n):
        j = (idx + off) % n
        if tri_ok[j] != 0:
            return int(tri_raw[j])
    return int(tri_raw[idx]) if n else 0


@njit(cache=True)
def roll_card_734900(roll_seed: int) -> int:
    v1 = _mix_734900(roll_seed)
    return (v1 % 13) + 1


@njit(cache=True)
def roll_pill_734180(roll_seed: int) -> int:
    seed = roll_seed & 0xFFFFFFFF
    v7 = _mix_qword_dword(seed, QWORD_734180_PILL, DWORD_734180_PILL)
    v7b = _mix_qword_dword(v7, QWORD_734180_PILL, DWORD_734180_PILL)
    n = 22
    v13 = (v7b % n) + 1
    v7c = _mix_qword_dword(v7b, QWORD_734180_PILL, DWORD_734180_PILL)
    if 1 <= v13 <= 22 and v7c % 7 == 0:
        v13 += 55
    return int(v13) & 0xFFFFFFFF


@njit(cache=True)
def eden_pre_trinket_rng(p988: int) -> int:
    v1 = _eden_rng_step(p988)
    if v1 % 3 == 0:
        return v1
    v1 = _eden_rng_step(v1)
    if v1 & 1:
        return v1
    v150 = _eden_rng_step(v1)
    return _eden_cfg_mix(v150)


@njit(cache=True)
def pocket_kind_and_ids(
    p988: int,
    u32: int,
    tri_raw: np.ndarray,
    tri_ok: np.ndarray,
    tri_count: int,
    tri_shr: int,
    tri_shl: int,
    tri_fin: int,
    has_tri: int,
) -> tuple[int, int, int]:
    v1 = _eden_rng_step(p988)
    if v1 % 3 == 0:
        tid = 0
        if has_tri != 0:
            rng409 = trinket_rng409_from_u32(u32)
            tid = roll_trinket_id(rng409, tri_raw, tri_ok, tri_count, tri_shr, tri_shl, tri_fin)
        return PK_TRINKET, tid, 0
    v1 = _eden_rng_step(v1)
    if v1 & 1:
        return PK_NONE, 0, 0
    v150 = _eden_rng_step(v1)
    roll = _eden_rng_step(v150)
    if v150 & 1:
        return PK_PILL, 0, roll_card_734900(roll)
    return PK_CARD, roll_pill_734180(roll), 0


@njit(cache=True)
def _v61_skipped(v61: int) -> bool:
    return v61 == 234 or v61 == 42 or v61 == 60


@njit(cache=True)
def treasure_item_ids(
    p988: int,
    proc_item_ids: np.ndarray,
    proc_blocked: np.ndarray,
    proc_passive: np.ndarray,
    proc_count: int,
) -> tuple[int, int]:
    v60 = proc_count - 1
    if v60 <= 0:
        return 0, 0
    v1 = eden_pre_trinket_rng(p988)
    v161 = 0
    v162 = 0
    for _ in range(100):
        v1 = _eden_rng_step(v1)
        v61 = v1 % v60 if v60 else 0
        if _v61_skipped(v61):
            continue
        v62 = v61 + 1
        if v62 <= 0 or v62 >= proc_count:
            continue
        if proc_blocked[v62] != 0:
            continue
        if proc_passive[v62] != 0:
            if v161 == 0:
                v161 = v62
        elif v162 == 0:
            v162 = v62
        if v161 != 0 and v162 != 0:
            break
    id1 = int(proc_item_ids[v161]) if v161 else 0
    id2 = int(proc_item_ids[v162]) if v162 else 0
    return id1, id2


@njit(cache=True)
def eden_7bbbd0_wiki_stats(p988: int) -> tuple[int, int, float, float, float, float, float, float]:
    p = p988 & 0xFFFFFFFF
    v64 = _eden_cfg_mix(p)
    v23 = v64 & 3
    red = 2 * v23
    bound = 4 - v23 if v23 else 4
    soul_seed, soul_half = _rng_next_int(v64, EDEN_S1, EDEN_S2, EDEN_S3, bound)
    soul = 2 * soul_half
    if red == 0 and soul <= 2:
        soul = 4

    v27 = _eden_cfg_mix(soul_seed)
    v69 = v27
    if v27 % 3:
        v28 = _eden_cfg_mix(v27)
        v69 = v28
        if v28 & 1:
            v69 = _eden_cfg_mix_v69_v28(v69, v28)
            v29 = v69
            v64b = v69
            rem = v69 % 3
            if rem == 2:
                _, _ = _rng_next_int(v64b, EDEN_S1, EDEN_S2, EDEN_S3, 2)
                v69 = v64b
            elif rem != 1:
                v69 = _eden_cfg_mix(v29)

    v28 = v69
    v30 = _eden_cfg_mix_v69_v28(v69, v28)
    u = _u32_to_float01(v30)
    spd = u + u - 1.0
    v32 = v30
    v68 = _eden_cfg_mix_v69_v28(v30, v32)
    tears_small = _u32_to_float01(v68) * 0.30000001 - 0.15000001
    v36 = _eden_stat_rng_step(v68)
    tears_mid = _u32_to_float01(v36) * 1.5 - 0.75
    v38 = _eden_stat_rng_step(v36)
    rng_delta = _u32_to_float01(v38) * 120.0 - 60.0
    v40 = _eden_stat_rng_step(v38)
    shotspeed = _u32_to_float01(v40) * 0.5 - 0.25
    v42 = _eden_stat_rng_step(v40)
    u2 = _u32_to_float01(v42)
    luck = u2 + u2 - 1.0
    return red, soul, spd, tears_small, tears_mid, rng_delta, shotspeed, luck


@njit(cache=True)
def eden_7bbbd0_hearts(p988: int) -> tuple[int, int]:
    p = p988 & 0xFFFFFFFF
    v64 = _eden_cfg_mix(p)
    v23 = v64 & 3
    red = 2 * v23
    bound = 4 - v23 if v23 else 4
    _, soul_half = _rng_next_int(v64, EDEN_S1, EDEN_S2, EDEN_S3, bound)
    soul = 2 * soul_half
    if red == 0 and soul <= 2:
        soul = 4
    return red, soul


@njit(cache=True)
def _near(a: float, b: float, eps: float) -> bool:
    d = a - b
    return d <= eps and d >= -eps


@njit(cache=True)
def _match_stats_packed(
    red1232: int,
    soul1235: int,
    dmg: float,
    spd: float,
    tears: float,
    rng_delta: float,
    shot: float,
    luck: float,
    red_t: float,
    soul_t: float,
    dmg_t: float,
    spd_t: float,
    tears_t: float,
    rng_t: float,
    shot_t: float,
    luck_t: float,
) -> bool:
    if red_t < _FILTER_OFF:
        if not _near(red1232 / 2.0, red_t, HEART_EPS):
            return False
    if soul_t < _FILTER_OFF:
        if not _near(soul1235 / 2.0, soul_t, HEART_EPS):
            return False
    if dmg_t < _FILTER_OFF:
        if not _near(dmg, dmg_t, STAT_EPS):
            return False
    if spd_t < _FILTER_OFF:
        if not _near(spd, spd_t, STAT_EPS):
            return False
    if tears_t < _FILTER_OFF:
        if not _near(tears, tears_t, STAT_EPS):
            return False
    if rng_t < _FILTER_OFF:
        post = rng_delta / RANGE_GAME_SCALE + TPL_RANGE
        if not _near(post, rng_t, STAT_EPS):
            return False
    if shot_t < _FILTER_OFF:
        if not _near(shot, shot_t, STAT_EPS):
            return False
    if luck_t < _FILTER_OFF:
        if not _near(luck, luck_t, STAT_EPS):
            return False
    return True


@njit(cache=True)
def fast_match_u32(
    u32: int,
    red_t: float,
    soul_t: float,
    dmg_t: float,
    spd_t: float,
    tears_t: float,
    rng_t: float,
    shot_t: float,
    luck_t: float,
    check_stats: int,
    check_pocket: int,
    check_items: int,
    pocket_kind_f: int,
    trinket_id_f: int,
    pocket_id_f: int,
    passive_id_f: int,
    active_id_f: int,
    proc_item_ids: np.ndarray,
    proc_blocked: np.ndarray,
    proc_passive: np.ndarray,
    proc_count: int,
    has_proc: int,
    tri_raw: np.ndarray,
    tri_ok: np.ndarray,
    tri_count: int,
    tri_shr: int,
    tri_shl: int,
    tri_fin: int,
    has_tri: int,
) -> int:
    if u32 == 0:
        return 0
    p988 = p988_from_u32(u32)

    if check_stats != 0:
        red, soul, dmg, spd, tears, rng_delta, shot, luck = eden_7bbbd0_wiki_stats(p988)
        if not _match_stats_packed(
            red, soul, dmg, spd, tears, rng_delta, shot, luck,
            red_t, soul_t, dmg_t, spd_t, tears_t, rng_t, shot_t, luck_t,
        ):
            return 0
    elif red_t < _FILTER_OFF or soul_t < _FILTER_OFF:
        red, soul = eden_7bbbd0_hearts(p988)
        if not _match_stats_packed(
            red, soul, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
            red_t, soul_t, _FILTER_OFF, _FILTER_OFF, _FILTER_OFF, _FILTER_OFF, _FILTER_OFF, _FILTER_OFF,
        ):
            return 0

    if check_pocket != 0:
        pk, id_a, id_b = pocket_kind_and_ids(
            p988, u32, tri_raw, tri_ok, tri_count, tri_shr, tri_shl, tri_fin, has_tri,
        )
        if pocket_kind_f >= 0 and pk != pocket_kind_f:
            return 0
        if trinket_id_f >= 0:
            if pk != PK_TRINKET or id_a != trinket_id_f:
                return 0
        if pocket_id_f >= 0:
            pid = id_a if pk == PK_CARD else id_b
            if pid != pocket_id_f:
                return 0

    if check_items != 0:
        if has_proc == 0:
            return 0
        id1, id2 = treasure_item_ids(p988, proc_item_ids, proc_blocked, proc_passive, proc_count)
        if passive_id_f >= 0 and id2 != passive_id_f:
            return 0
        if active_id_f >= 0 and id1 != active_id_f:
            return 0

    return 1


class FastTables:
    __slots__ = (
        "has_proc",
        "has_tri",
        "proc_count",
        "proc_item_ids",
        "proc_blocked",
        "proc_passive",
        "tri_count",
        "tri_raw",
        "tri_ok",
        "tri_shr",
        "tri_shl",
        "tri_fin",
    )

    def __init__(self) -> None:
        self.has_proc = False
        self.has_tri = False
        self.proc_count = 0
        self.proc_item_ids = np.zeros(1, dtype=np.int32)
        self.proc_blocked = np.zeros(1, dtype=np.uint8)
        self.proc_passive = np.zeros(1, dtype=np.uint8)
        self.tri_count = 0
        self.tri_raw = np.zeros(1, dtype=np.int32)
        self.tri_ok = np.zeros(1, dtype=np.uint8)
        self.tri_shr = 1
        self.tri_shl = 5
        self.tri_fin = 19


class FastMatchPack:
    __slots__ = (
        "enabled",
        "red_t",
        "soul_t",
        "dmg_t",
        "spd_t",
        "tears_t",
        "rng_t",
        "shot_t",
        "luck_t",
        "check_stats",
        "check_pocket",
        "check_items",
        "pocket_kind_f",
        "trinket_id_f",
        "pocket_id_f",
        "passive_id_f",
        "active_id_f",
        "tables",
    )

    def __init__(self) -> None:
        self.enabled = False
        self.red_t = _FILTER_OFF
        self.soul_t = _FILTER_OFF
        self.dmg_t = _FILTER_OFF
        self.spd_t = _FILTER_OFF
        self.tears_t = _FILTER_OFF
        self.rng_t = _FILTER_OFF
        self.shot_t = _FILTER_OFF
        self.luck_t = _FILTER_OFF
        self.check_stats = 0
        self.check_pocket = 0
        self.check_items = 0
        self.pocket_kind_f = _FILTER_I_OFF
        self.trinket_id_f = _FILTER_I_OFF
        self.pocket_id_f = _FILTER_I_OFF
        self.passive_id_f = _FILTER_I_OFF
        self.active_id_f = _FILTER_I_OFF
        self.tables = FastTables()


def numba_available() -> bool:
    return _NUMBA_OK


def pack_tables(proc_table: Any | None, trinket_pool_path: str | Path | None) -> FastTables:
    ft = FastTables()
    if proc_table is not None and proc_table.count > 0:
        n = proc_table.count
        item_ids = np.zeros(n, dtype=np.int32)
        blocked = np.zeros(n, dtype=np.uint8)
        passive = np.zeros(n, dtype=np.uint8)
        for i in range(n):
            ent = proc_table.get(i)
            if ent is not None:
                item_ids[i] = int(ent.item_id)
                blocked[i] = 1 if ent.blocked else 0
                passive[i] = 1 if ent.is_passive_slot else 0
        ft.proc_item_ids = item_ids
        ft.proc_blocked = blocked
        ft.proc_passive = passive
        ft.proc_count = n
        ft.has_proc = True

    path = Path(trinket_pool_path) if trinket_pool_path else None
    if path is not None and path.is_file():
        from tools.trinket_eden import load_trinket_pool

        pool = load_trinket_pool(path)
        n = pool.count
        if n > 0:
            ft.tri_raw = np.array([int(e.raw) & 32767 for e in pool.entries], dtype=np.int32)
            ft.tri_ok = np.array(
                [1 if e.flag4 and e.flag5 else 0 for e in pool.entries],
                dtype=np.uint8,
            )
            ft.tri_count = n
            ft.tri_shr = int(pool.rng_shr)
            ft.tri_shl = int(pool.rng_shl)
            ft.tri_fin = int(pool.rng_fin)
            ft.has_tri = True
    return ft


def pack_criteria(criteria: Any, tables: FastTables | None = None) -> FastMatchPack:
    pack = FastMatchPack()
    if not _NUMBA_OK or not criteria.has_match_filters():
        return pack
    if tables is not None:
        pack.tables = tables

    if criteria.red is not None:
        pack.red_t = float(criteria.red)
    if criteria.soul is not None:
        pack.soul_t = float(criteria.soul)
    pack.check_stats = 1 if any(
        getattr(criteria, k) is not None
        for k in ("damage", "speed", "tears", "range_display", "shot_speed", "luck")
    ) else 0
    if criteria.damage is not None:
        pack.dmg_t = float(criteria.damage)
    if criteria.speed is not None:
        pack.spd_t = float(criteria.speed)
    if criteria.tears is not None:
        pack.tears_t = float(criteria.tears)
    if criteria.range_display is not None:
        pack.rng_t = float(criteria.range_display)
    if criteria.shot_speed is not None:
        pack.shot_t = float(criteria.shot_speed)
    if criteria.luck is not None:
        pack.luck_t = float(criteria.luck)

    need_pocket = any(
        x is not None for x in (criteria.pocket_kind, criteria.trinket_id, criteria.pocket_id)
    )
    need_items = criteria.passive_id is not None or criteria.active_id is not None
    pack.check_pocket = 1 if need_pocket else 0
    pack.check_items = 1 if need_items else 0

    if criteria.pocket_kind is not None:
        pack.pocket_kind_f = _POCKET_KIND.get(str(criteria.pocket_kind).lower(), _FILTER_I_OFF)
    if criteria.trinket_id is not None:
        pack.trinket_id_f = int(criteria.trinket_id)
    if criteria.pocket_id is not None:
        pack.pocket_id_f = int(criteria.pocket_id)
    if criteria.passive_id is not None:
        pack.passive_id_f = int(criteria.passive_id)
    if criteria.active_id is not None:
        pack.active_id_f = int(criteria.active_id)

    pack.enabled = True
    return pack


def can_use_fast(plan: Any, pack: FastMatchPack) -> bool:
    if not _NUMBA_OK or not pack.enabled or not plan.need_match:
        return False
    t = pack.tables
    if plan.need_items and not t.has_proc:
        return False
    if pack.trinket_id_f >= 0 and not t.has_tri:
        return False
    return True


def fast_match_seed(u32: int, pack: FastMatchPack) -> bool:
    t = pack.tables
    return bool(
        fast_match_u32(
            u32 & 0xFFFFFFFF,
            pack.red_t,
            pack.soul_t,
            pack.dmg_t,
            pack.spd_t,
            pack.tears_t,
            pack.rng_t,
            pack.shot_t,
            pack.luck_t,
            pack.check_stats,
            pack.check_pocket,
            pack.check_items,
            pack.pocket_kind_f,
            pack.trinket_id_f,
            pack.pocket_id_f,
            pack.passive_id_f,
            pack.active_id_f,
            t.proc_item_ids,
            t.proc_blocked,
            t.proc_passive,
            t.proc_count,
            1 if t.has_proc else 0,
            t.tri_raw,
            t.tri_ok,
            t.tri_count,
            t.tri_shr,
            t.tri_shl,
            t.tri_fin,
            1 if t.has_tri else 0,
        )
    )


def verify_against_python(u32: int, criteria: Any, proc_table: Any | None, trinket_path: str | None) -> bool:
    from tools.eden_j460 import eden_starting_items
    from tools.eden_stats import eden_7bbbd0_base_panel, eden_7bbbd0_rolls, wiki_deltas_dict
    from tools.game_rng import eden_7bc740_pocket, p988_from_start_seed

    tables = pack_tables(proc_table, trinket_path)
    pack = pack_criteria(criteria, tables)
    jit_ok = fast_match_seed(u32, pack)

    py_ok = True
    p988 = p988_from_start_seed(u32)
    if pack.check_stats:
        rolls = eden_7bbbd0_rolls(p988)
        wiki = wiki_deltas_dict(rolls)
        if criteria.red is not None and abs(rolls.red1232 / 2.0 - criteria.red) > HEART_EPS:
            py_ok = False
        if criteria.soul is not None and abs(rolls.soul1235 / 2.0 - criteria.soul) > HEART_EPS:
            py_ok = False
        if criteria.damage is not None and abs(wiki["damage"] - criteria.damage) > STAT_EPS:
            py_ok = False
        if criteria.speed is not None and abs(wiki["speed"] - criteria.speed) > STAT_EPS:
            py_ok = False
        if criteria.tears is not None and abs(wiki["tears"] - criteria.tears) > STAT_EPS:
            py_ok = False
        if criteria.range_display is not None:
            post = wiki.get("rangeGame", 0.0) + TPL_RANGE
            if abs(post - criteria.range_display) > STAT_EPS:
                py_ok = False
        if criteria.shot_speed is not None and abs(wiki["shotSpeed"] - criteria.shot_speed) > STAT_EPS:
            py_ok = False
        if criteria.luck is not None and abs(wiki["luck"] - criteria.luck) > STAT_EPS:
            py_ok = False
    elif criteria.red is not None or criteria.soul is not None:
        panel = eden_7bbbd0_base_panel(p988)
        if criteria.red is not None and abs(panel.red1232 / 2.0 - criteria.red) > HEART_EPS:
            py_ok = False
        if criteria.soul is not None and abs(panel.soul1235 / 2.0 - criteria.soul) > HEART_EPS:
            py_ok = False

    if py_ok and pack.check_pocket:
        from tools.pocket_lookup import pocket_hud_item_id, pocket_hud_kind

        pocket = eden_7bc740_pocket(p988, trinket_pool_path=trinket_path, start_seed=u32)
        if criteria.pocket_kind is not None and pocket_hud_kind(pocket) != criteria.pocket_kind:
            py_ok = False
        if criteria.trinket_id is not None:
            if pocket_hud_kind(pocket) != "trinket" or pocket.trinket_id != criteria.trinket_id:
                py_ok = False
        if criteria.pocket_id is not None:
            if pocket_hud_item_id(pocket) != criteria.pocket_id:
                py_ok = False

    if py_ok and pack.check_items and proc_table is not None:
        j = eden_starting_items(u32, table=proc_table, trinket_pool_path=trinket_path)
        if criteria.passive_id is not None and j["passive_id"] != criteria.passive_id:
            py_ok = False
        if criteria.active_id is not None and j["active_id"] != criteria.active_id:
            py_ok = False

    return jit_ok == py_ok
