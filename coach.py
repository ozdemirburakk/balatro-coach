"""Local Balatro shop companion. Python 3.10+, standard library only."""
from __future__ import annotations

import json
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CATALOG = json.loads((ROOT / "catalog.json").read_text(encoding="utf-8"))["items"]
BY_NAME = {item["name"].casefold(): item for item in CATALOG}
HANDS = (
    "High Card", "Pair", "Two Pair", "Three of a Kind", "Straight", "Flush",
    "Full House", "Four of a Kind", "Straight Flush", "Five of a Kind",
    "Flush House", "Flush Five",
)
TAG_LABELS = {
    "chips": "chip", "mult": "+Mult", "xmult": "XMult",
    "scaling": "zamanla büyüme", "economy": "ekonomi",
    "discard": "discard", "suit": "suit", "face": "yüz kartı",
    "consumable": "tüketilebilir kart", "hand-size": "eldeki kart",
    "joker-synergy": "Joker etkileşimi", "card-enhancement": "kart geliştirme",
    "blind": "blind",
}


def interest(money: int) -> int:
    return min(5, max(0, money) // 5)


def evaluate(payload: dict) -> dict:
    money = int(payload["money"])
    ante = int(payload["ante"])
    hand = str(payload["hand"])
    if money < 0 or not 1 <= ante <= 100 or hand not in HANDS:
        raise ValueError("Para, ante veya ana el geçersiz.")
    owned = {s.strip().casefold() for s in str(payload.get("jokers", "")).split(",") if s.strip()}
    results = []
    for row in payload.get("items", []):
        name = str(row.get("name", "")).strip()
        if not name:
            continue
        price = int(row.get("price", 0))
        if not 0 <= price <= 999:
            raise ValueError("Ürün fiyatı 0–999 arasında olmalı.")
        card = BY_NAME.get(name.casefold())
        after = money - price
        loss = interest(money) - interest(after) if after >= 0 else 0
        label = "BİLİNMİYOR"
        notes = []
        if after < 0:
            label, notes = "ALINAMAZ", ["Para yetmiyor."]
        elif not card:
            notes = ["Katalogda yok; tooltip adını kontrol et. Etkiyi uydurmayacağım."]
        elif card["category"] == "Planet":
            target = card["hand"]
            if target == hand:
                label, notes = "DEĞERLENDİR", [f"Ana elin {target} seviyesini artırır."]
            else:
                label, notes = "DÜŞÜK ÖNCELİK", [f"{target} seviyesini artırır; seçtiğin ana el {hand}. Plan değişecekse değerlendir."]
        elif card["category"] == "Joker":
            tags = card.get("tags", [])
            label = "DURUMA BAĞLI"
            if card["name"].casefold() in owned:
                notes.append("Bu Joker sende de var; ikinci kopyanın değeri slota ve etkiye bağlı.")
            if card.get("hand"):
                required = card["hand"]
                if required == hand:
                    label = "DEĞERLENDİR"
                    notes.append(f"{required} ile uyumlu.")
                else:
                    label = "DÜŞÜK ÖNCELİK"
                    notes.append(f"{required} gerektirir; ana elin {hand}. El planı değişirse tekrar değerlendir.")
            if tags:
                notes.append("Katalog ipuçları: " + ", ".join(TAG_LABELS[t] for t in tags) + ".")
            notes.append("Kart etkisini, Joker sırasını ve mevcut skorunu oyundaki tooltip ile doğrula.")
        elif card["category"] == "Voucher":
            label = "DEĞERLENDİR"
            if card["name"] in ("Overstock", "Overstock Plus"):
                notes.append("Sonraki shop'larda ek ürün verir; kalan shop sayısı önemli.")
            elif card["name"] in ("Clearance Sale", "Liquidation"):
                notes.append("Gelecek alışverişlerde indirim sağlar; kalan bütçene ve shop sayısına bak.")
            else:
                label = "DURUMA BAĞLI"
                notes.append("Voucher etkisini tooltip üzerinden kontrol et; ihtiyaçlarına göre seç.")
        else:
            label = "DURUMA BAĞLI"
            notes.append(f"{card['category']} kartı; deste, boş slot ve mevcut plan bilgisi gerekir.")
        if after >= 0:
            notes.append(f"Satın alınca ${after} kalır; tahmini faiz farkı ${loss}.")
        results.append({"name": name, "category": card["category"] if card else "?", "label": label, "notes": notes})
    return {"money": money, "interest": interest(money), "results": results}


def capture_text() -> dict:
    if sys.platform != "darwin":
        raise RuntimeError("Gecikmeli ekran OCR şu anda macOS için hazır. Kart adını elle girebilirsin.")
    if not shutil.which("tesseract"):
        raise RuntimeError("OCR için önce 'brew install tesseract' çalıştır.")
    # A short delay gives the player time to return to the game and hover a card.
    time.sleep(3)
    with tempfile.TemporaryDirectory(prefix="balatro-coach-") as temp:
        image = str(Path(temp) / "screen.png")
        subprocess.run(["screencapture", "-x", image], check=True, timeout=15)
        text = subprocess.run(
            ["tesseract", image, "stdout", "-l", "eng", "--psm", "11"],
            check=True, capture_output=True, text=True, timeout=20,
        ).stdout
    normalized = re.sub(r"\s+", " ", text).casefold()
    matches = [card["name"] for card in CATALOG if card["name"].casefold() in normalized]
    return {"raw": text, "matches": matches[:30]}


class Handler(BaseHTTPRequestHandler):
    token = ""

    def log_message(self, format: str, *args: object) -> None:
        return

    def _send(self, code: int, body: bytes, content_type: str) -> None:
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        if self.path == "/":
            page = (ROOT / "index.html").read_text(encoding="utf-8").replace("__TOKEN__", self.token)
            self._send(200, page.encode(), "text/html; charset=utf-8")
        elif self.path == "/catalog":
            body = json.dumps({"items": CATALOG, "hands": HANDS}, ensure_ascii=False).encode()
            self._send(200, body, "application/json; charset=utf-8")
        elif self.path == "/state":
            from run_coach import read_live_state
            body = json.dumps(read_live_state(), ensure_ascii=False).encode()
            self._send(200, body, "application/json; charset=utf-8")
        else:
            self._send(404, b"Not found", "text/plain")

    def do_POST(self) -> None:
        # Do not allow unrelated websites to start screen capture through localhost.
        if self.headers.get("X-Coach-Token") != self.token:
            self._send(403, b"Forbidden", "text/plain")
            return
        if not self.headers.get("Content-Type", "").startswith("application/json"):
            self._send(415, b"JSON required", "text/plain")
            return
        try:
            length = int(self.headers.get("Content-Length", "0"))
            if not 0 <= length <= 65536:
                raise ValueError("İstek çok büyük.")
            payload = json.loads(self.rfile.read(length))
            if self.path == "/evaluate":
                result = evaluate(payload)
            elif self.path == "/ocr":
                result = capture_text()
            else:
                self._send(404, b"Not found", "text/plain")
                return
            code = 200
        except (ValueError, KeyError, RuntimeError, subprocess.SubprocessError, OSError) as exc:
            result, code = {"error": str(exc)}, 400
        self._send(code, json.dumps(result, ensure_ascii=False).encode(), "application/json; charset=utf-8")


def main() -> None:
    Handler.token = secrets.token_urlsafe(32)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"Balatro Coach: {url}", flush=True)
    print("Kapatmak için terminalde Ctrl+C.", flush=True)
    threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
