"""Read-only live run summary and conservative next-action guidance."""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


# Vanilla hand values; the mod supplies the actual level's chips and Mult when available.
HAND_BASE = {
    "High Card": (5, 1, 10, 1), "Pair": (10, 2, 15, 1),
    "Two Pair": (20, 2, 20, 1), "Three of a Kind": (30, 3, 20, 2),
    "Straight": (30, 4, 30, 3), "Flush": (35, 4, 15, 2),
    "Full House": (40, 4, 25, 2), "Four of a Kind": (60, 7, 30, 3),
    "Straight Flush": (100, 8, 40, 4), "Five of a Kind": (120, 12, 35, 3),
    "Flush House": (140, 14, 40, 4), "Flush Five": (160, 16, 50, 3),
}
RANK_CHIPS = {**{str(n): n for n in range(2, 11)},
              "Jack": 10, "Queen": 10, "King": 10, "Ace": 11}
RANK_LABELS = {"Jack": "J", "Queen": "Q", "King": "K", "Ace": "A"}
SUIT_LABELS = {"Spades": "♠", "Hearts": "♥", "Clubs": "♣", "Diamonds": "♦"}
HAND_LABELS = {
    "High Card": "Yüksek kart", "Pair": "Çift", "Two Pair": "İki çift",
    "Three of a Kind": "Üçlü", "Straight": "Kent", "Flush": "Renk",
    "Full House": "Ful", "Four of a Kind": "Kare", "Straight Flush": "Sıralı renk",
    "Five of a Kind": "Beşli", "Flush House": "Renkli ful", "Flush Five": "Renkli beşli",
}


def default_state_file() -> Path:
    if custom := os.getenv("BALATRO_COACH_STATE"):
        return Path(custom).expanduser()
    if sys.platform == "darwin":
        return Path.home() / "Library/Application Support/Balatro/balatro_coach_state.json"
    if sys.platform == "win32":
        return Path(os.getenv("APPDATA", str(Path.home()))) / "Balatro/balatro_coach_state.json"
    return Path(os.getenv("XDG_DATA_HOME", str(Path.home() / ".local/share"))) / "Balatro/balatro_coach_state.json"


def read_live_state(path: Path | None = None) -> dict:
    path = path or default_state_file()
    if not path.is_file():
        mods = path.parent / "Mods"
        has_loader = mods.is_dir() and any(
            child.is_dir() and ("smods" in child.name.casefold() or "steamodded" in child.name.casefold())
            for child in mods.iterdir()
        )
        if not has_loader:
            message = "Steamodded kurulu görünmüyor. Mac kurulum rehberindeki Lovely + Steamodded adımlarını tamamla, ardından python3 install_mod.py çalıştır."
        elif not (mods / "balatro_coach_bridge/main.lua").is_file():
            message = "Oyun köprüsü eksik. Bu repo klasöründe python3 install_mod.py çalıştır; sonra Balatro'yu modlu biçimde yeniden aç."
        else:
            message = "Köprü kurulu, fakat oyun durum dosyası yok. Balatro'yu run_lovely_macos.sh ile modlu aç ve bir koşu başlat."
        return {"connected": False, "message": message, "path": str(path)}
    try:
        state = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {"connected": False, "message": "Oyun durum dosyası henüz tamamlanmadı; tekrar deneniyor.", "path": str(path)}
    if state.get("schema") != 1:
        return {"connected": False, "message": "Oyun köprüsünün şeması desteklenmiyor.", "path": str(path)}
    age = time.time() - path.stat().st_mtime
    if age > 8:
        return {"connected": False, "message": "Durum dosyası güncellenmiyor; oyun kapalı veya mod durmuş olabilir.", "path": str(path)}
    return {"connected": True, "state": state, "guidance": guide(state)}


def _name(card: dict, by_id: dict) -> str:
    item = by_id.get(card.get("key", ""))
    return item["name"] if item else card.get("name") or card.get("key", "Bilinmiyor")


def _hand_plan(state: dict) -> tuple[str | None, str]:
    hands = {name: data for name, data in (state.get("hands") or {}).items()
             if name in HAND_BASE and isinstance(data, dict)}
    leveled = [(name, data) for name, data in hands.items() if int(data.get("level") or 1) > 1]
    if leveled:
        name, data = max(leveled, key=lambda pair: (int(pair[1].get("level") or 1), int(pair[1].get("played") or 0)))
        return name, f"{HAND_LABELS[name]} eli seviye {data['level']} olduğu için öne çıkıyor."
    joker_keys = {c.get("key") for c in state.get("jokers", [])}
    if "j_wily" in joker_keys or "j_zany" in joker_keys:
        return "Three of a Kind", "Üçlüye bonus veren Joker'ın var; bu bir oyun planı önerisi."
    if "j_jolly" in joker_keys or "j_sly" in joker_keys:
        return "Pair", "Çifte bonus veren Joker'ın var; bu bir oyun planı önerisi."
    played = sorted(((name, int(data.get("played") or 0)) for name, data in hands.items()),
                    key=lambda pair: pair[1], reverse=True)
    if played and played[0][1] >= 3 and (len(played) == 1 or played[0][1] >= played[1][1] + 2):
        name, count = played[0]
        return name, f"{HAND_LABELS[name]} elini {count} kez oynadığın için öne çıkıyor."
    return None, "Henüz belirlenmedi. İlk elde otomatik olarak çift hedefi seçilmiyor."


def _hand_type(cards: list[dict]) -> str:
    ranks = [c.get("rank", "") for c in cards]
    suits = [c.get("suit", "") for c in cards]
    counts = sorted(Counter(ranks).values(), reverse=True)
    flush = len(cards) == 5 and len(set(suits)) == 1 and bool(suits[0])
    values = {"2": 2, "3": 3, "4": 4, "5": 5, "6": 6, "7": 7, "8": 8,
              "9": 9, "10": 10, "Jack": 11, "Queen": 12, "King": 13, "Ace": 14}
    sequence = sorted({values.get(rank, -100) for rank in ranks})
    straight = len(cards) == 5 and len(sequence) == 5 and (
        sequence[-1] - sequence[0] == 4 or sequence == [2, 3, 4, 5, 14]
    )
    if flush and counts == [5]: return "Flush Five"
    if flush and counts == [3, 2]: return "Flush House"
    if flush and straight: return "Straight Flush"
    if counts == [5]: return "Five of a Kind"
    if counts == [4, 1] or counts == [4]: return "Four of a Kind"
    if counts == [3, 2]: return "Full House"
    if flush: return "Flush"
    if straight: return "Straight"
    if counts[0] >= 3: return "Three of a Kind"
    if counts.count(2) >= 2: return "Two Pair"
    if counts[0] == 2: return "Pair"
    return "High Card"


def _card_label(card: dict) -> str:
    rank = card.get("rank") or "?"
    suit = card.get("suit") or "?"
    return f"{RANK_LABELS.get(rank, rank)}{SUIT_LABELS.get(suit, suit)}"


def _scoring_cards(cards: list[dict], hand: str) -> list[dict]:
    counts = Counter(card.get("rank") for card in cards)
    if hand == "High Card":
        return [max(cards, key=lambda c: RANK_CHIPS.get(c.get("rank"), 0))]
    if hand == "Pair":
        return [c for c in cards if counts[c.get("rank")] >= 2][:2]
    if hand == "Two Pair":
        return [c for c in cards if counts[c.get("rank")] >= 2][:4]
    if hand == "Three of a Kind":
        return [c for c in cards if counts[c.get("rank")] >= 3][:3]
    if hand == "Four of a Kind":
        return [c for c in cards if counts[c.get("rank")] >= 4][:4]
    return cards


def _base_score(cards: list[dict], hand: str, hands: dict) -> dict:
    chips, mult, chips_per_level, mult_per_level = HAND_BASE[hand]
    data = hands.get(hand) or {}
    level = max(1, int(data.get("level") or 1))
    chips = data.get("chips") if isinstance(data.get("chips"), (int, float)) else chips + (level - 1) * chips_per_level
    mult = data.get("mult") if isinstance(data.get("mult"), (int, float)) else mult + (level - 1) * mult_per_level
    chips += sum(RANK_CHIPS.get(card.get("rank"), 0) for card in _scoring_cards(cards, hand))
    return {"chips": chips, "mult": mult, "score": int(chips * mult)}


def _choose_hand(state: dict, main_hand: str | None) -> dict | None:
    cards = state.get("hand_cards") or []
    if not cards:
        return None
    if len(cards) > 20:
        return {"note": "Eldeki kart sayısı çok yüksek; el seçimini oyunda yap."}
    best = None
    hands = state.get("hands") or {}
    for size in range(1, min(5, len(cards)) + 1):
        for indices in itertools.combinations(range(len(cards)), size):
            selected = [cards[i] for i in indices]
            hand = _hand_type(selected)
            estimate = _base_score(selected, hand, hands)
            # A small preference for the leveled/planned hand when two base scores are close.
            priority = estimate["score"] * (1.06 if hand == main_hand else 1)
            if any(c.get("debuffed") for c in selected):
                priority *= 0.5
            if best is None or priority > best[0]:
                best = (priority, hand, indices, estimate)
    assert best is not None
    _, hand, indices, estimate = best
    selection = [{"index": i + 1, "card": _card_label(cards[i])} for i in indices]
    return {"hand": hand, "selection": selection, **estimate}


def _discard_plan(state: dict, main_hand: str | None, candidate: dict) -> list[dict]:
    cards = state.get("hand_cards") or []
    if not cards or int(state.get("discards_left") or 0) < 1:
        return []
    # Preserve a ready scoring hand. If the blind needs more points, draw toward
    # high pairs or the planned flush instead of throwing away every non-Ace.
    blind_left = max(0, int((state.get("blind") or {}).get("chips") or 0) - int(state.get("chips_scored") or 0))
    if blind_left and candidate["score"] >= blind_left:
        return []
    if candidate["hand"] not in ("High Card", "Pair", "Two Pair"):
        return []
    ranks = Counter(c.get("rank") for c in cards)
    suits = Counter(c.get("suit") for c in cards)
    if main_hand in ("Flush", "Straight Flush") and max(suits.values()) >= 3:
        target = max(suits, key=suits.get)
        keep = [i for i, c in enumerate(cards) if c.get("suit") == target]
    elif max(ranks.values()) >= 2:
        target = max(ranks, key=lambda rank: (ranks[rank], str(rank)))
        keep = [i for i, c in enumerate(cards) if c.get("rank") == target]
        if len(keep) < 3 and len(cards) >= 6:
            other = [i for i in range(len(cards)) if i not in keep]
            keep.append(max(other, key=lambda i: RANK_CHIPS.get(cards[i].get("rank"), 0)))
    else:
        keep = sorted(range(len(cards)), key=lambda i: RANK_CHIPS.get(cards[i].get("rank"), 0), reverse=True)[:3]
    return [{"index": i + 1, "card": _card_label(cards[i])}
            for i in range(len(cards)) if i not in keep][:5]


def guide(state: dict) -> dict:
    from coach import BY_NAME, interest
    by_id = {item["id"]: item for item in BY_NAME.values()}
    stage = state.get("stage", "")
    deck = by_id.get(state.get("deck", ""), {}).get("name", state.get("deck", "Bilinmiyor"))
    main_hand, plan_reason = _hand_plan(state)
    money = int(state.get("money", 0))
    jokers = [_name(card, by_id) for card in state.get("jokers", [])]
    base = {"deck": deck, "stage": stage, "ante": state.get("ante"), "money": money,
            "blind": state.get("blind") or {}, "hands_left": state.get("hands_left", 0),
            "discards_left": state.get("discards_left", 0), "jokers": jokers,
            "main_hand": main_hand, "plan_reason": plan_reason,
            "shop": [], "next": "", "detail": "", "score": None,
            "chips_scored": state.get("chips_scored", 0)}
    if stage == "SHOP":
        cards = state.get("shop_cards", []) + state.get("shop_vouchers", [])
        roles = [by_id.get(card.get("key", ""), {}).get("tags", []) for card in state.get("jokers", [])]
        have_mult = any("mult" in r for r in roles)
        have_chips = any("chips" in r for r in roles)
        candidates = []
        for card in cards:
            known = by_id.get(card.get("key", ""), {})
            name = _name(card, by_id)
            price = int(card.get("cost") or 0)
            tags = known.get("tags", [])
            score = 0
            reasons = []
            if price > money:
                reasons.append("Para yetmiyor.")
                score = -1000
            elif known.get("category") == "Joker":
                score = 5
                if main_hand and known.get("hand") == main_hand:
                    score += 4; reasons.append(f"{HAND_LABELS[main_hand]} ile uyumlu")
                elif main_hand and known.get("hand"):
                    score -= 5; reasons.append(f"{known['hand']} gerektirir")
                elif known.get("hand"):
                    reasons.append(f"{known['hand']} eline bonus verir; el planı henüz net değil")
                if "mult" in tags and not have_mult:
                    score += 5; reasons.append("+Mult ihtiyacı")
                if "chips" in tags and not have_chips:
                    score += 3; reasons.append("chip ihtiyacı")
                if "scaling" in tags and int(state.get("ante") or 1) <= 3:
                    score += 2; reasons.append("erken büyüme")
                if "xmult" in tags and have_mult:
                    score += 2; reasons.append("mevcut Mult ile çarpan")
                if name in jokers:
                    score -= 2; reasons.append("aynı Joker zaten var")
            elif known.get("category") == "Planet":
                score = 6 if main_hand and known.get("hand") == main_hand else 0
                reasons.append(f"{known.get('hand', '?')} seviyesini artırır")
            elif known.get("category") == "Voucher":
                score = 6 if name in ("Overstock", "Overstock Plus") and int(state.get("ante") or 1) <= 4 else 3
                reasons.append("voucher etkisini oyunda doğrula")
            else:
                reasons.append("etki veya içerik bilgisi eksik")
            if money - price < 0:
                pass
            elif money >= 15 and interest(money - price) < interest(money):
                score -= 2
                reasons.append("faiz eşiği düşer")
            candidates.append({"name": name, "price": price, "score": score, "reasons": reasons})
        candidates.sort(key=lambda c: c["score"], reverse=True)
        base["shop"] = candidates
        chosen = next((c for c in candidates if c["score"] >= 7), None)
        if chosen:
            base["next"] = f"{chosen['name']} için AL seçeneğini değerlendir (${chosen['price']})."
            base["detail"] = "Önce oyun tooltip'ini, Joker slotunu ve bu blind'a yetecek skoru kontrol et."
        else:
            base["next"] = "Shop'u geçip sonraki blind'a ilerlemeyi değerlendir."
            base["detail"] = "Mevcut ürünler için yeterli bağlamsal avantaj bulunamadı; paket içeriği görünmeden kesin öneri veremem."
    elif stage == "BLIND_SELECT":
        base["next"] = "Blind'ı seç ve oynayarak ekonomi kur."
        base["detail"] = "Skip tag ve yaklaşan boss'u ayrıca kontrol et; mevcut durumda skip değerini hesaplayamıyorum."
    elif stage == "SELECTING_HAND":
        candidate = _choose_hand(state, main_hand)
        base["candidate"] = candidate
        if candidate and "selection" in candidate:
            chosen = ", ".join(f"{c['index']}. {c['card']}" for c in candidate["selection"])
            blind_left = max(0, int((state.get("blind") or {}).get("chips") or 0) - int(state.get("chips_scored") or 0))
            base["score"] = {"chips": candidate["chips"], "mult": candidate["mult"],
                             "base": candidate["score"], "remaining": blind_left,
                             "target": (state.get("blind") or {}).get("chips", 0)}
            discard = _discard_plan(state, main_hand, candidate)
            if discard and blind_left > 0:
                selected = ", ".join(f"{c['index']}. {c['card']}" for c in discard)
                base["next"] = f"{selected} kartlarını seç ve 'Discard' düğmesine bas."
                base["detail"] = f"Yüksek kartları/çifti tutup daha güçlü el arıyoruz. Şu anki hazır el: {HAND_LABELS[candidate['hand']]} ({chosen}). Bu tercih kesin skor garantisi vermez."
            else:
                base["next"] = f"{chosen} kartlarını seç ve 'Play Hand' düğmesine bas."
                base["detail"] = f"Hazır el: {HAND_LABELS[candidate['hand']]}. Hesaplanan taban puan yalnızca el seviyesini ve normal kart değerlerini içerir."
            if jokers or any(c.get("edition") or c.get("seal") or c.get("debuffed") or
                             c.get("enhancement") not in ("", "Default Base") for c in state.get("hand_cards", [])):
                base["detail"] += " Joker, kart etkileri veya boss nedeniyle oyundaki gerçek skor farklı olabilir."
        else:
            base["next"] = "Eldeki kartlar bekleniyor."
    else:
        base["next"] = "Oyun aşaması değişiyor veya paket açık; sonraki kararı bekle."
        base["detail"] = "Bu aşama için güvenilir otomatik eylem hesaplanmıyor."
    return base
