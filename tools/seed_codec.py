from __future__ import annotations

from collections.abc import Iterator

ALPHABET = "A" + "BCDEFGHJKLMNPQRSTWXYZ01234V6789"
XOR_CONST = 0xFEF7FFD
_VALID = set(ALPHABET)
_INV_ALPHABET = {c: i for i, c in enumerate(ALPHABET)}
# data char bit shifts in x = seed ^ XOR_CONST (pos 7/8 are checksum)
_PREFIX_BIT_SHIFTS = {0: 27, 1: 22, 2: 17, 3: 12, 5: 7, 6: 2}

# sub_9E9DB0 easter eggs (matched in sub_94D040 before normal start)
_SPECIAL_SEED_LABELS = frozenset(
    {
        "B911 99AC",
        "CAMO K1DD",
        "CAMO F0ES",
        "FART SNDS",
        "B00B T00B",
        "BRWN SNKE",
        "BASE MENT",
    }
)


def normalize_seed_string(s: str) -> str:
    s = s.strip().upper().replace("\u00a0", " ")
    s = s.translate(str.maketrans({"I": "1", "O": "0", "U": "V", "5": "V"}))
    s = "".join(c for c in s if c in _VALID or c == " ")
    if len(s) > 4 and s[4] != " ":
        s = s[:4] + " " + s[4:]
    return s[:9]


def suggest_canonical_seed(s: str) -> str | None:
    norm = normalize_seed_string(s)
    if len(norm) != 9 or norm[4] != " ":
        return None
    prefix = norm[:7]
    for a in ALPHABET:
        for b in ALPHABET:
            label = prefix + a + b
            u32 = decode_seed_string(label)
            if u32 is None:
                continue
            canon = custom_start_seed_label(u32)
            if canon:
                return canon
    return None


def custom_start_seed_label(seed: int) -> str | None:
    seed &= 0xFFFFFFFF
    if seed == 0:
        return None
    label = enterable_seed_label(seed)
    if label is None or label in _SPECIAL_SEED_LABELS:
        return None
    return label


def quick_custom_seed_ok(u32: int) -> bool:
    u32 &= 0xFFFFFFFF
    if u32 == 0:
        return False
    label = seed_to_string(u32)
    return label not in _SPECIAL_SEED_LABELS


def prefix_needs_label_verify(prefix: str) -> bool:
    return len(normalize_seed_string(prefix)) >= 8


def seed_string_error(s: str) -> str | None:
    raw = s.strip().upper()
    if not raw:
        return "请输入种子"
    bad = sorted({c for c in raw if c != " " and c not in _VALID})
    if not bad:
        norm = normalize_seed_string(raw)
        if len(norm) != 9 or norm[4] != " ":
            return "格式应为 XXXX XXXX（9 个字符，中间空格）"
        u32 = decode_seed_string(norm)
        if u32 is None:
            msg = "种子校验失败（后两位为校验位，改一位就会变整局 RNG）"
            hint = suggest_canonical_seed(norm)
            if hint and hint != norm:
                msg += f"；按当前前缀，游戏规范写法应为：{hint}"
            return msg
        canon = custom_start_seed_label(u32)
        if canon is None:
            enc = enterable_seed_label(u32)
            if u32 == 0:
                return "Start Seed 为 0：游戏不会采用（sub_9EB880 会改随机种子），Tab 里等于没设种子"
            if enc in _SPECIAL_SEED_LABELS:
                return f"「{enc}」是特殊种子（彩蛋），不是 Tab 自定义开局种子，不能用来预测伊甸局"
            if enc and enc != norm:
                return f"请使用游戏可输入的写法：{enc}"
            return "无法作为自定义开局种子"
        if canon != norm:
            return f"请使用游戏可输入的写法：{canon}"
        return None
    parts = [f"非法字符: {''.join(bad)}"]
    if "5" in bad:
        parts.append("数字 5 应写成 V")
    if "I" in bad:
        parts.append("字母 I 应写成 1")
    if "O" in bad:
        parts.append("字母 O 应写成 0")
    if "U" in bad:
        parts.append("字母 U 应写成 V")
    return "；".join(parts)


def checksum(seed: int) -> int:
    return _checksum_loop(seed)


def pack_indices(idxs: list[int]) -> int:
    v13, v14, v15, v16, v17, v18, v19 = idxs[:7]
    inner = v13
    for v in (v14, v15, v16, v17, v18):
        inner = v | (32 * inner)
    return ((v19 >> 3) | (4 * inner)) & 0xFFFFFFFF


def _checksum_loop(seed: int) -> int:
    chk = 0
    v3 = seed & 0xFFFFFFFF
    while v3:
        v4 = (v3 + chk) & 0xFF
        chk = ((v4 >> 7) + 2 * v4) & 0xFF
        v3 >>= 5
    return chk


def _pack_chars(indices: list[int]) -> int:
    v13, v14, v15, v16, v17, v18, v19, _v20 = indices
    return pack_indices([v13, v14, v15, v16, v17, v18, v19])


def is_enterable_seed_string(s: str) -> bool:
    return string_to_custom_start_seed(s) is not None


def decode_seed_string(s: str) -> int | None:
    inv = {c: i for i, c in enumerate(ALPHABET)}
    s = normalize_seed_string(s)
    if len(s) != 9 or s[4] != " ":
        return None
    try:
        indices = [inv[s[i]] for i in range(9) if i != 4]
    except KeyError:
        return None
    packed = _pack_chars(indices)
    seed = (packed ^ XOR_CONST) & 0xFFFFFFFF
    # sub_9EB6B0: v19 @ pos7, v20 @ pos8 → chk == (v20 | (32 * v19)) & 0xFF
    if _checksum_loop(seed) != ((indices[7] | (32 * indices[6])) & 0xFF):
        return None
    return seed


def enterable_seed_label(seed: int) -> str | None:
    seed &= 0xFFFFFFFF
    label = seed_to_string(seed)
    if decode_seed_string(label) == seed:
        return label
    return None


def seed_to_string(seed: int) -> str:
    seed &= 0xFFFFFFFF
    x = seed ^ XOR_CONST
    v10 = [
        (x >> 27) & 0x1F,
        (x >> 22) & 0x1F,
        (x >> 17) & 0x1F,
        (x >> 12) & 0x1F,
        (x >> 7) & 0x1F,
        (x >> 2) & 0x1F,
        checksum(seed) & 0x1F,
        ((checksum(seed) | (x << 8)) >> 5) & 0x1F,
    ]
    out = ["?"] * 9
    out[4] = " "
    for j in range(9):
        if j == 4:
            continue
        if j == 7:
            out[j] = ALPHABET[v10[7]]
        elif j == 8:
            out[j] = ALPHABET[v10[6]]
        else:
            k = j if j < 4 else j - 1
            out[j] = ALPHABET[v10[k]]
    return "".join(out)


def string_to_seed(s: str) -> int | None:
    return decode_seed_string(s)


def string_to_custom_start_seed(s: str) -> int | None:
    norm = normalize_seed_string(s)
    u32 = decode_seed_string(norm)
    if u32 is None:
        return None
    if custom_start_seed_label(u32) != norm:
        return None
    return u32


def _popcount32(v: int) -> int:
    return (int(v) & 0xFFFFFFFF).bit_count()


def _embed_bits(val: int, free_mask: int) -> int:
    out = 0
    bit_idx = 0
    mask = free_mask & 0xFFFFFFFF
    for b in range(32):
        if (mask >> b) & 1:
            if (val >> bit_idx) & 1:
                out |= 1 << b
            bit_idx += 1
    return out & 0xFFFFFFFF


def prefix_x_constraints(prefix: str) -> tuple[int, int]:
    prefix = normalize_seed_string(prefix)
    x_mask = 0
    x_fixed = 0
    for i, ch in enumerate(prefix):
        if i == 4:
            if ch != " ":
                return 0xFFFFFFFF, 0xFFFFFFFF
            continue
        if i in (7, 8):
            continue
        shift = _PREFIX_BIT_SHIFTS.get(i)
        if shift is None:
            continue
        idx = _INV_ALPHABET.get(ch)
        if idx is None:
            return 0xFFFFFFFF, 0xFFFFFFFF
        x_mask |= 0x1F << shift
        x_fixed |= idx << shift
    return x_mask, x_fixed


def prefix_data_bits_match(u32: int, prefix: str) -> bool:
    prefix = normalize_seed_string(prefix)
    if not prefix:
        return True
    x_mask, x_fixed = prefix_x_constraints(prefix)
    if x_mask == 0xFFFFFFFF and x_fixed == 0xFFFFFFFF:
        return False
    x = (int(u32) ^ XOR_CONST) & 0xFFFFFFFF
    return (x & x_mask) == x_fixed


def estimate_prefix_candidates(prefix: str) -> int:
    prefix = normalize_seed_string(prefix)
    if not prefix:
        return 1 << 32
    x_mask, x_fixed = prefix_x_constraints(prefix)
    if x_mask == 0xFFFFFFFF and x_fixed == 0xFFFFFFFF:
        return 0
    free_mask = (~x_mask) & 0xFFFFFFFF
    return 1 << _popcount32(free_mask)


def is_valid_seed_prefix(prefix: str) -> bool:
    prefix = normalize_seed_string(prefix)
    if not prefix:
        return False
    data_len = sum(1 for i in range(len(prefix)) if i != 4)
    if data_len < 1:
        return False
    return estimate_prefix_candidates(prefix) > 0


def iter_u32_for_seed_prefix(
    prefix: str,
    *,
    offset: int = 0,
    limit: int | None = None,
) -> Iterator[int]:
    """Enumerate u32 seeds matching a label prefix by candidate index."""
    prefix = normalize_seed_string(prefix)
    if not prefix:
        return

    x_mask, x_fixed = prefix_x_constraints(prefix)
    if x_mask == 0xFFFFFFFF and x_fixed == 0xFFFFFFFF:
        return

    free_mask = (~x_mask) & 0xFFFFFFFF
    total = 1 << _popcount32(free_mask)
    verify_label = prefix_needs_label_verify(prefix)

    start_idx = max(0, int(offset))
    if start_idx >= total:
        return
    end_idx = total if limit is None else min(total, start_idx + max(0, int(limit)))

    for add in range(start_idx, end_idx):
        x = (x_fixed | _embed_bits(add, free_mask)) & 0xFFFFFFFF
        seed = (x ^ XOR_CONST) & 0xFFFFFFFF
        if seed == 0:
            continue
        if verify_label:
            label = custom_start_seed_label(seed)
            if label is not None and label.startswith(prefix):
                yield seed
        elif quick_custom_seed_ok(seed):
            yield seed


if __name__ == "__main__":
    tests = [
        ("BGDM 9DPK", 107593840),
        ("E3GM 9LJ7", 698597460),
        ("4VX0 LYNB", 3641186988),
        ("JPR1 PSTT", 1286605119),
        ("1WMD BTJH", 3011071800),
        ("GPZQ N2X1", 1015388575),
    ]
    for text, num in tests:
        dec = string_to_seed(text)
        enc = enterable_seed_label(num)
        print(f"{text} ({num}) dec_ok={dec == num} enc={enc} enc_ok={enc == text}")
