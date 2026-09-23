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
PACK_STAGES = {
    "PLANET_PACK": "Celestial", "TAROT_PACK": "Arcana",
    "SPECTRAL_PACK": "Spectral", "BUFFOON_PACK": "Buffoon",
    "STANDARD_PACK": "Standard", "SMODS_BOOSTER_OPENED": "Unknown",
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


def _joker_value(card: dict, state: dict, by_id: dict, main_hand: str | None) -> tuple[int, str]:
    known = by_id.get(card.get("key"), {})
    owned = state.get("jokers") or []
    limit = int(state.get("joker_slots") or 0)
    if limit and len(owned) >= limit:
        return -100, "Joker slotu dolu; önce mevcut Joker'lardan biri için ayrı karar gerekir."
    if card.get("key") in {item.get("key") for item in owned}:
        return 3, "Bu Joker zaten sende; ikinci kopyanın değeri etkisine bağlı."
    tags = set(known.get("tags") or [])
    owned_tags = [set(by_id.get(item.get("key"), {}).get("tags") or []) for item in owned]
    score = 5
    reasons = []
    if main_hand and known.get("hand") == main_hand:
        score += 5; reasons.append(f"{HAND_LABELS[main_hand]} elini destekliyor")
    elif main_hand and known.get("hand"):
        score -= 3; reasons.append("mevcut el eğilimiyle uyuşmuyor")
    if "mult" in tags and not any("mult" in role for role in owned_tags):
        score += 4; reasons.append("Mult ihtiyacını karşılayabilir")
    if "chips" in tags and not any("chips" in role for role in owned_tags):
        score += 3; reasons.append("chip desteği verebilir")
    if "xmult" in tags and any("mult" in role for role in owned_tags):
        score += 3; reasons.append("mevcut Mult ile çarpan uyumu")
    if "scaling" in tags and int(state.get("ante") or 1) <= 3:
        score += 2; reasons.append("erken aşamada büyüyebilir")
    return score, ", ".join(reasons) if reasons else "Joker etkisini oyun tooltip'inden doğrula."


def _card_targets(cards: list[dict], count: int, strongest: bool = False,
                  allowed: set[int] | None = None) -> str:
    def value(card: dict) -> int:
        return (RANK_CHIPS.get(card.get("rank"), 0) + 12 * bool(card.get("seal"))
                + 10 * bool(card.get("edition"))
                + 6 * (card.get("enhancement") not in (None, "", "Default Base", "Base Card")))
    indexed = sorted(((i, card) for i, card in enumerate(cards) if allowed is None or i in allowed),
                     key=lambda pair: value(pair[1]), reverse=strongest)
    chosen = indexed[:count]
    return ", ".join(f"{i + 1}. {_card_label(card)}" for i, card in chosen)


def _pack_option(card: dict, state: dict, by_id: dict, main_hand: str | None) -> tuple[int, str, str]:
    """Return a relative score, a concise reason and any follow-up card target."""
    key = card.get("key", "")
    known = by_id.get(key, {})
    kind = known.get("category") or card.get("set")
    hands = state.get("hands") or {}
    money = int(state.get("money") or 0)
    free_joker = not state.get("joker_slots") or len(state.get("jokers") or []) < int(state["joker_slots"])
    playing = state.get("hand_cards") or []
    if kind == "Planet":
        hand = known.get("hand")
        if not hand:
            return -10, "Bu gezegenin geliştirdiği el bilinmiyor.", ""
        data = hands.get(hand) or {}
        level = int(data.get("level") or 1)
        played = int(data.get("played") or 0)
        score = 4 + min(8, played * 2) + min(8, (level - 1) * 4)
        if hand == main_hand:
            score += 10
        if not main_hand and not played:
            score += {"Pair": 3, "High Card": 2, "Two Pair": 1}.get(hand, -1)
        reason = f"{HAND_LABELS[hand]} elini seviye {level + 1} yapar"
        if not main_hand and not played:
            reason += "; kalıcı bir el hedefi belirlenmiş değil"
        return score, reason, ""
    if kind == "Joker":
        score, reason = _joker_value(card, state, by_id, main_hand)
        return score, reason, ""
    if kind == "Tarot":
        if key == "c_hermit":
            gain = min(20, money)
            return (5 + gain // 4 if gain else -10), f"yaklaşık ${gain} kazandırır", ""
        if key == "c_temperance":
            gain = min(50, sum(int(c.get("sell_cost") or 0) for c in state.get("jokers") or []))
            return (5 + gain // 5 if gain else -10), f"mevcut Joker satış değerlerinden ${gain} kazandırır", ""
        if key == "c_high_priestess":
            return 8, "iki gezegen kartı verir; hangi eller geldiği rastgeledir", ""
        if key == "c_emperor":
            return 7, "iki Tarot kartı verir; etkileri açılınca görünür", ""
        if key == "c_judgement":
            return (8 if free_joker else -100), "rastgele Joker verir" if free_joker else "Joker slotun dolu", ""
        if key == "c_fool":
            last = state.get("last_tarot_planet")
            return (8 if last and last != "c_fool" else -10), "son kullanılan Tarot/gezegeni tekrar verir" if last else "tekrarlanacak kart bilgisi yok", ""
        if key == "c_hanged_man" and len(playing) >= 2:
            safe = {i for i, c in enumerate(playing) if RANK_CHIPS.get(c.get("rank"), 10) <= 8
                    and not c.get("seal") and not c.get("edition")
                    and c.get("enhancement") in (None, "", "Default Base", "Base Card")}
            if len(safe) >= 2:
                return 7, "zayıf iki kartı desteden çıkarır", _card_targets(playing, 2, allowed=safe)
            return -10, "Güvenle yok edilecek iki zayıf kart görünmüyor.", ""
        # These effects need a target playing card after taking the Tarot.
        targets = {"c_chariot": (1, False), "c_devil": (1, False),
                   "c_empress": (2, True), "c_heirophant": (2, True),
                   "c_lovers": (1, False), "c_magician": (2, True),
                   "c_star": (3, False), "c_moon": (3, False),
                   "c_sun": (3, False), "c_world": (3, False),
                   "c_strength": (2, False)}
        if key in targets and playing:
            count, strong = targets[key]
            return 4, "oyun kartını geliştirir; hedef seçimini oyundaki etkiye göre doğrula", _card_targets(playing, min(count, len(playing)), strong)
        return -10, "Hedef/etkiyi güvenle değerlendirmek için yeterli veri yok.", ""
    if kind == "Spectral":
        if key == "c_soul":
            return (20 if free_joker else -100), "efsanevi Joker verir" if free_joker else "Joker slotun dolu", ""
        if key == "c_black_hole":
            return 16, "tüm poker ellerini bir seviye yükseltir", ""
        if key == "c_ankh":
            count = len(state.get("jokers") or [])
            return (9 if count == 1 else -10), "tek Joker'ını kopyalar" if count == 1 else "rastgele bir Joker'ı kopyalarken diğerlerini yok edebilir", ""
        if key in ("c_cryptid", "c_aura", "c_deja_vu", "c_medium", "c_trance", "c_talisman") and playing:
            return 7, "oyun kartına kopya, edition veya seal uygular", _card_targets(playing, 1, True)
        return -10, "Etkisi deste veya Joker'ları değiştirebilir; güvenilir seçim yapamıyorum.", ""
    if kind in ("Default", "Enhanced", "Playing Card") or card.get("rank"):
        if card.get("seal"):
            return 8, f"{card['seal']} seal taşıyan kartı desteye ekler", ""
        if card.get("edition"):
            return 7, "edition taşıyan kartı desteye ekler", ""
        if card.get("enhancement") and card["enhancement"] not in ("Default Base", "Base Card"):
            return 6, "geliştirilmiş kartı desteye ekler", ""
        return -1, "normal kartı eklemek desteyi büyütür", ""
    return -10, "Bu kartın etkisi henüz tanınmıyor.", ""


def _pack_guidance(state: dict, base: dict, by_id: dict, main_hand: str | None) -> None:
    pack = state.get("pack_cards") or []
    if not pack:
        base["next"] = "Paket kartları açılıyor; seçenekler görünmesini bekle."
        base["detail"] = "Kartlar oyunda görünür görünmez seçimi güncelleyeceğim."
        return
    options = []
    for index, card in enumerate(pack, 1):
        score, reason, target = _pack_option(card, state, by_id, main_hand)
        label = _card_label(card) if card.get("rank") else _name(card, by_id)
        options.append({"index": index, "name": label, "value": score,
                        "reason": reason, "target": target})
    options.sort(key=lambda item: item["value"], reverse=True)
    base["pack_options"] = options
    best = options[0]
    if best["value"] < 0:
        base["next"] = "Paketi 'Skip' ile geç."
        base["detail"] = "Görünen seçeneklerden güvenle önerebileceğim bir kart yok. " + best["reason"]
        return
    base["next"] = f"Pakette {best['index']}. {best['name']} kartını seç."
    if best["target"]:
        base["next"] += f" Sonraki seçimde {best['target']} kartını hedefle."
    base["detail"] = best["reason"] + (" Birden fazla seçim varsa ilkinden sonra seçenekleri yeniden değerlendireceğim."
                                      if int(state.get("pack_choices") or 0) > 1 else "")


def _ready_consumable(state: dict, by_id: dict, main_hand: str | None) -> tuple[str, str] | None:
    for index, card in enumerate(state.get("consumables") or [], 1):
        key = card.get("key")
        known = by_id.get(key, {})
        if known.get("category") == "Planet" and main_hand and known.get("hand") == main_hand:
            return f"Tüketilebilirlerde {index}. {_name(card, by_id)} kartını kullan.", f"{HAND_LABELS[main_hand]} elini güçlendirir."
        if key in ("c_hermit", "c_temperance", "c_black_hole"):
            value, reason, _ = _pack_option(card, state, by_id, main_hand)
            if value >= 6:
                return f"Tüketilebilirlerde {index}. {_name(card, by_id)} kartını kullan.", reason
    return None


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
            "shop": [], "pack_options": [], "next": "", "detail": "", "score": None,
            "chips_scored": state.get("chips_scored", 0)}
    if stage in PACK_STAGES:
        _pack_guidance(state, base, by_id, main_hand)
    elif stage == "SHOP":
        cards = state.get("shop_cards", []) + state.get("shop_vouchers", [])
        candidates = []
        for card in cards:
            known = by_id.get(card.get("key", ""), {})
            name = _name(card, by_id)
            price = int(card.get("cost") or 0)
            score = 0
            reasons = []
            if price > money:
                reasons.append("Para yetmiyor.")
                score = -1000
            elif known.get("category") == "Joker":
                score, reason = _joker_value(card, state, by_id, main_hand)
                reasons.append(reason)
            elif known.get("category") == "Planet":
                score = 9 if main_hand and known.get("hand") == main_hand else 2
                reasons.append(f"{HAND_LABELS.get(known.get('hand'), '?')} elinin seviyesini artırır")
            elif known.get("category") == "Voucher":
                score = 8 if name in ("Overstock", "Overstock Plus") and int(state.get("ante") or 1) <= 4 else 3
                reasons.append("voucher etkisini oyunda doğrula")
            elif known.get("category") in ("Tarot", "Spectral"):
                score, reason, _ = _pack_option(card, state, by_id, main_hand)
                reasons.append(reason)
            else:
                reasons.append("etki veya içerik bilgisi eksik")
            if money - price < 0:
                pass
            elif money >= 15 and interest(money - price) < interest(money):
                score -= 2
                reasons.append("faiz eşiği düşer")
            candidates.append({"name": name, "price": price, "score": score, "reasons": reasons})
        for card in state.get("shop_boosters") or []:
            name = card.get("name") or "Booster Pack"
            price = int(card.get("cost") or 0)
            kind = card.get("kind") or ""
            if price > money:
                score, reasons = -1000, ["Para yetmiyor."]
            elif kind == "Buffoon":
                slots = int(state.get("joker_slots") or 0)
                has_room = not slots or len(state.get("jokers") or []) < slots
                score = 8 if has_room and len(state.get("jokers") or []) < 3 else (5 if has_room else -100)
                reasons = ["Açınca Joker seçeneklerine bakacağım." if has_room else "Joker slotu dolu."]
            elif kind == "Celestial":
                score = 9 if main_hand or money - price >= 20 else 4
                reasons = ["Gezegenler açılınca hangi elin gelişeceğini göreceğim."]
            elif kind == "Arcana":
                score, reasons = 5, ["Tarot seçenekleri açılınca etkilerine bakacağım."]
            elif kind == "Spectral":
                score, reasons = 4, ["Etkiler riskli olabilir; açılınca kartları değerlendireceğim."]
            elif kind == "Standard":
                score, reasons = 2, ["İçindeki kartlar bilinmiyor; desteyi büyütmenin maliyeti var."]
            else:
                score, reasons = -5, ["Paket türü henüz tanınmıyor."]
            if score > 0 and money >= 15 and interest(money - price) < interest(money):
                score -= 2
                reasons.append("Satın alınca faiz eşiği düşer.")
            candidates.append({"name": name, "price": price, "score": score,
                               "reasons": reasons, "kind": "pack"})
        candidates.sort(key=lambda c: c["score"], reverse=True)
        base["shop"] = candidates
        chosen = next((c for c in candidates if c["score"] >= 7), None)
        if chosen:
            if chosen.get("kind") == "pack":
                base["next"] = f"{chosen['name']} için ${chosen['price']} ödeyip paketi aç."
                base["detail"] = "Paket içeriği açılınca hangi kartı seçeceğini ayrıca söyleyeceğim. " + " ".join(chosen["reasons"])
            else:
                base["next"] = f"{chosen['name']} kartını ${chosen['price']} ödeyip satın al."
                base["detail"] = " ".join(chosen["reasons"]) or "Kart etkisini oyunda doğrula."
        else:
            reroll = int(state.get("reroll_cost") or 0)
            if reroll > 0 and money - reroll >= 15 and candidates:
                base["next"] = f"Shop'ta ${reroll} ödeyip bir kez Reroll yap."
                base["detail"] = "Görünen ürünler şu an güçlü görünmüyor; yeni ürünler gelince yeniden bakacağım."
            else:
                base["next"] = "Shop'tan çık ve sonraki blind'a ilerle."
                base["detail"] = "Bu bütçeyle görünen ürünlerden güçlü bir satın alma önerisi çıkaramıyorum."
    elif stage == "BLIND_SELECT":
        base["next"] = "Sıradaki blind'ı seç ve oyna."
        base["detail"] = "Skip ödülünün değerini henüz hesaplayamıyorum; bir sonraki ekranda kartları okuyacağım."
    elif stage == "ROUND_EVAL":
        base["next"] = "Cash Out düğmesine bas; ardından shop ürünlerine birlikte bakacağız."
        base["detail"] = "Ödül ve faiz tutarını oyundaki ekranda kontrol et."
    elif stage == "GAME_OVER":
        base["next"] = "Koşu bitti; yeni koşu başlat."
        base["detail"] = "Yeni deck ve Joker'ları gördüğümde öneriyi sıfırdan oluşturacağım."
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
    if stage in ("SHOP", "BLIND_SELECT"):
        ready = _ready_consumable(state, by_id, main_hand)
        if ready:
            base["next"], base["detail"] = ready
    return base
