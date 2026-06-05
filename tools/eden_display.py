from __future__ import annotations

from tools.eden_predict import EdenPredictResult
from tools.pocket_lookup import HUD_SLOT_CARD, HUD_SLOT_PILL, pocket_hud_item_id


def _fmt_delta(v: float, digits: int = 2) -> str:
    if abs(v) < 0.0005:
        return "±0"
    return f"{v:+.{digits}f}"


def _pocket_display(pk: dict) -> dict[str, str]:
    kind = pk.get("kind") or ""
    out = {"trinket_id": "", "card_id": "", "pill_id": ""}
    if kind == "trinket":
        tid = pk.get("trinket_id")
        if tid is not None:
            out["trinket_id"] = str(tid)
        return out
    if kind not in ("card", "pill"):
        return out
    pid = pocket_hud_item_id(pk)
    if pid is None:
        return out
    grant = pk.get("grant_mode")
    if grant == HUD_SLOT_PILL:
        out["pill_id"] = str(pid)
    elif grant == HUD_SLOT_CARD:
        out["card_id"] = str(pid)
    elif kind == "card":
        out["card_id"] = str(pid)
    else:
        out["pill_id"] = str(pid)
    return out


def build_display(result: EdenPredictResult) -> dict:
    w = result.wiki_deltas
    h = result.hearts
    pk = result.pocket
    post_range = float(w.get("rangeGame", 0)) + 6.5

    stats = [
        {"key": "damage", "value": _fmt_delta(w.get("damage", 0))},
        {"key": "speed", "value": _fmt_delta(w.get("speed", 0))},
        {"key": "tears", "value": _fmt_delta(w.get("tears", 0))},
        {"key": "range", "value": f"{post_range:.2f}"},
        {"key": "shotSpeed", "value": _fmt_delta(w.get("shotSpeed", 0))},
        {"key": "luck", "value": _fmt_delta(w.get("luck", 0))},
    ]

    pocket = _pocket_display(pk)
    items: list[dict] = []
    if result.items:
        it = result.items
        items.append({"role": "passive", "id": it["passive_id"]})
        items.append({"role": "active", "id": it["active_id"]})

    seed_show = result.seed_label or "—"
    seed_alt = (
        result.encoded_seed
        if result.encoded_seed and result.encoded_seed != result.seed_label
        else None
    )

    return {
        "seed": seed_show,
        "seed_alt": seed_alt,
        "hearts": {
            "red": h.get("red_hud", 0),
            "soul": (h.get("soul1235", 0) or 0) / 2.0,
        },
        "stats": stats,
        "pocket": pocket,
        "items": items,
        "warnings": result.warnings,
        "has_items": bool(items),
    }
