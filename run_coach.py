"""Read-only live run summary and conservative next-action guidance."""
from __future__ import annotations

import itertools
import json
import os
import sys
import time
from collections import Counter
from pathlib import Path


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
        return {"connected": False, "message": "Canlı durum bulunamadı. Steamodded ve mod/balatro_coach_bridge kurulu olmalı.", "path": str(path)}
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


def _main_hand(state: dict) -> str:
    hands = state.get("hands") or {}
    if not hands:
        return state.get("most_played_hand") or "Pair"
    scoring = {name: 2 * (data.get("level", 1) - 1) + data.get("played", 0)
               for name, data in hands.items() if isinstance(data, dict)}
    ranked = sorted(scoring, key=scoring.get, reverse=True)
    if ranked and scoring[ranked[0]] > 0:
        return ranked[0]
    joker_keys = {c.get("key") for c in state.get("jokers", [])}
    if "j_wily" in joker_keys or "j_zany" in joker_keys:
        return "Three of a Kind"
    if "j_jolly" in joker_keys or "j_sly" in joker_keys:
        return "Pair"
    return "Pair"


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
    return f"{card.get('rank') or '?'} {card.get('suit') or '?'}"


def _choose_hand(state: dict, main_hand: str) -> dict | None:
    cards = state.get("hand_cards") or []
    if not cards:
        return None
    if len(cards) > 20:
        return {"note": "Eldeki kart sayısı çok yüksek; el seçimini oyunda yap."}
    weights = {"High Card": 2, "Pair": 5, "Two Pair": 9, "Three of a Kind": 13,
               "Straight": 16, "Flush": 16, "Full House": 22, "Four of a Kind": 28,
               "Straight Flush": 38, "Five of a Kind": 40, "Flush House": 44, "Flush Five": 48}
    best = None
    owned = {card.get("key") for card in state.get("jokers", [])}
    for size in range(1, min(5, len(cards)) + 1):
        for indices in itertools.combinations(range(len(cards)), size):
            selected = [cards[i] for i in indices]
            hand = _hand_type(selected)
            level = (state.get("hands") or {}).get(hand, {}).get("level", 1)
            bonus = 7 if hand == main_hand else 0
            if hand == "Three of a Kind" and ("j_wily" in owned or "j_zany" in owned):
                bonus += 9
            if hand == "Pair" and ("j_jolly" in owned or "j_sly" in owned):
                bonus += 5
            score = weights[hand] + 3 * (level - 1) + bonus - max(0, size - 2) * 0.15
            if any(c.get("debuffed") for c in selected):
                score -= 4
            if best is None or score > best[0]:
                best = (score, hand, indices)
    assert best is not None
    _, hand, indices = best
    selection = [{"index": i + 1, "card": _card_label(cards[i])} for i in indices]
    return {"hand": hand, "selection": selection,
            "note": "Bu seçim yaklaşık el gücüne dayanır; Joker tetiklerini, enhancement ve gerçek skoru hesaplamaz."}


def guide(state: dict) -> dict:
    from coach import BY_NAME, interest
    by_id = {item["id"]: item for item in BY_NAME.values()}
    stage = state.get("stage", "")
    deck = by_id.get(state.get("deck", ""), {}).get("name", state.get("deck", "Bilinmiyor"))
    main_hand = _main_hand(state)
    money = int(state.get("money", 0))
    jokers = [_name(card, by_id) for card in state.get("jokers", [])]
    base = {"deck": deck, "stage": stage, "ante": state.get("ante"), "money": money,
            "blind": state.get("blind") or {}, "hands_left": state.get("hands_left", 0),
            "discards_left": state.get("discards_left", 0), "jokers": jokers,
            "main_hand": main_hand, "shop": [], "next": "", "detail": ""}
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
                if known.get("hand") == main_hand:
                    score += 4; reasons.append(f"{main_hand} ile uyumlu")
                elif known.get("hand"):
                    score -= 5; reasons.append(f"{known['hand']} gerektirir")
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
                score = 6 if known.get("hand") == main_hand else 0
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
            chosen = ", ".join(f"{c['index']}: {c['card']}" for c in candidate["selection"])
            base["next"] = f"{candidate['hand']} için {chosen} kartlarını seç."
            base["detail"] = candidate["note"]
        else:
            base["next"] = "Eldeki kartlar bekleniyor."
    else:
        base["next"] = "Oyun aşaması değişiyor veya paket açık; sonraki kararı bekle."
        base["detail"] = "Bu aşama için güvenilir otomatik eylem hesaplanmıyor."
    return base
