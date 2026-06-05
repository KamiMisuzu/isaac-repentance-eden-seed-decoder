from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
PROFILES_DIR = ROOT / "data" / "profiles"
DEFAULT_PROFILE_NAME = "default"


def profiles_root() -> Path:
    PROFILES_DIR.mkdir(parents=True, exist_ok=True)
    return PROFILES_DIR


def list_profile_dirs() -> list[Path]:
    root = profiles_root()
    return sorted(
        (p for p in root.iterdir() if p.is_dir()),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )


def pick_write_profile(name: str | None = None) -> Path:
    root = profiles_root()
    if name:
        d = root / name.strip()
        d.mkdir(parents=True, exist_ok=True)
        return d
    dirs = list_profile_dirs()
    if dirs:
        return dirs[0]
    d = root / DEFAULT_PROFILE_NAME
    d.mkdir(parents=True, exist_ok=True)
    return d


def profile_status() -> dict[str, Any]:
    root = profiles_root()
    rel = root.relative_to(ROOT).as_posix()
    entries = []
    for d in list_profile_dirs():
        tri = d / "trinket_pool.json"
        proc = d / "proc.json"
        entries.append(
            {
                "id": d.name,
                "path": d.relative_to(ROOT).as_posix(),
                "trinket_pool": tri.is_file(),
                "proc": proc.is_file(),
                "mtime": d.stat().st_mtime,
            }
        )
    active = resolve_active_profile()
    return {
        "root": rel,
        "absolute": str(root.resolve()),
        "profiles": entries,
        "active": active,
    }


def resolve_active_profile() -> dict[str, str | None]:
    best_tri: Path | None = None
    best_proc: Path | None = None
    best_dir: Path | None = None
    for d in list_profile_dirs():
        tri = d / "trinket_pool.json"
        proc = d / "proc.json"
        if tri.is_file() and proc.is_file():
            return {
                "id": d.name,
                "dir": d.relative_to(ROOT).as_posix(),
                "trinket_pool": tri.relative_to(ROOT).as_posix(),
                "proc": proc.relative_to(ROOT).as_posix(),
            }
        if tri.is_file() and best_tri is None:
            best_tri, best_dir = tri, d
        if proc.is_file() and best_proc is None:
            best_proc = d if best_dir is None else best_dir
            if best_dir is None:
                best_dir = d
    if best_dir:
        return {
            "id": best_dir.name,
            "dir": best_dir.relative_to(ROOT).as_posix(),
            "trinket_pool": str((best_dir / "trinket_pool.json").relative_to(ROOT))
            if (best_dir / "trinket_pool.json").is_file()
            else None,
            "proc": str((best_dir / "proc.json").relative_to(ROOT))
            if (best_dir / "proc.json").is_file()
            else None,
        }
    return {"id": None, "dir": None, "trinket_pool": None, "proc": None}


def resolve_trinket_pool_path(explicit: Path | str | None = None) -> Path | None:
    if explicit is not None:
        p = Path(explicit)
        return p if p.is_file() else None
    act = resolve_active_profile()
    if act.get("trinket_pool"):
        p = ROOT / act["trinket_pool"]
        if p.is_file():
            return p
    return None


def resolve_proc_table_path(explicit: Path | str | None = None) -> Path | None:
    if explicit is not None:
        p = Path(explicit)
        return p if p.is_file() else None
    act = resolve_active_profile()
    if act.get("proc"):
        p = ROOT / act["proc"]
        if p.is_file():
            return p
    return None


def run_memory_extract(
    *,
    profile: str | None = None,
    exe: str = "isaac-ng.exe",
    pid: int | None = None,
    min_trinket_score: int = 70,
    min_proc_score: int = 75,
) -> dict[str, Any]:
    from tools.memory_fingerprint import (
        find_proc_table,
        find_trinket_pool,
        guess_start_seed,
        read_proc_table,
        read_trinket_pool,
    )
    from tools.trinket_eden import TrinketPoolSnapshot, save_trinket_pool
    from tools.win_process_mem import open_process

    t0 = time.perf_counter()
    out_dir = pick_write_profile(profile)
    trinket_out = out_dir / "trinket_pool.json"
    proc_out = out_dir / "proc.json"

    pm = open_process(exe, pid=pid or None)
    try:
        hit = find_trinket_pool(pm, min_score=min_trinket_score)
        if hit is None:
            raise RuntimeError("trinket pool not found")
        seed = guess_start_seed(pm, hit.address)
        tri = read_trinket_pool(pm, hit.address, start_seed=seed)
        snap = TrinketPoolSnapshot.from_json(tri)
        save_trinket_pool(snap, trinket_out)

        proc_data = None
        proc_hit, v_start, v_end = find_proc_table(pm, min_score=min_proc_score)
        if proc_hit is not None:
            proc_data = read_proc_table(pm, v_start, v_end)
            proc_out.write_text(json.dumps(proc_data, indent=2), encoding="utf-8")

        elapsed = time.perf_counter() - t0
        return {
            "ok": True,
            "profile_id": out_dir.name,
            "profile_dir": out_dir.relative_to(ROOT).as_posix(),
            "trinket_pool": trinket_out.relative_to(ROOT).as_posix(),
            "proc": proc_out.relative_to(ROOT).as_posix() if proc_data else None,
            "trinket_count": snap.count,
            "rng409": snap.rng409,
            "start_seed": seed,
            "proc_count": proc_data.get("count") if proc_data else None,
            "elapsed_sec": round(elapsed, 1),
            "method": (hit.extra or {}).get("method", "?"),
            "warnings": [] if proc_data else ["proc table not found"],
        }
    finally:
        pm.close()
