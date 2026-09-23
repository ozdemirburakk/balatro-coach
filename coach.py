"""Balatro shop companion. Does not control or modify the game."""
from __future__ import annotations

import math
import re
import tkinter as tk
from tkinter import messagebox, scrolledtext, ttk

HANDS = ('High Card', 'Pair', 'Two Pair', 'Three of a Kind', 'Straight', 'Flush', 'Full House', 'Four of a Kind')
PLANETS = {'Pluto': 'High Card', 'Mercury': 'Pair', 'Uranus': 'Two Pair', 'Venus': 'Three of a Kind', 'Saturn': 'Straight', 'Jupiter': 'Flush', 'Earth': 'Full House', 'Mars': 'Four of a Kind'}
# Small, explicit catalogue. Unknown entries are never silently identified.
JOKERS = {
    'wily joker': ('Three of a Kind', 'chips'),
    'jolly joker': ('Pair', 'mult'),
    'sly joker': ('Pair', 'chips'),
    'clever joker': ('Two Pair', 'chips'),
    'zany joker': ('Three of a Kind', 'mult'),
    'scary face': ('face cards', 'chips'),
    'mr. bones': ('emergency', 'safety'),
}

def interest(money: int) -> int:
    return min(5, max(0, money) // 5)

def advise(name: str, price: int, money: int, ante: int, hand: str, jokers: str) -> str:
    key = name.strip().lower()
    after = money - price
    if not key:
        return 'Ürün adı girilmeli.'
    if price > money:
        return 'ALMA — para yetmiyor.'
    cost = interest(money) - interest(after)
    owned = jokers.lower()
    if key in JOKERS:
        required, kind = JOKERS[key]
        if key in owned:
            return 'ALMA — bu Joker zaten mevcut; ikinci kopyayı ayrıca değerlendirmek gerekir.'
        if kind == 'safety':
            return 'BEKLE — Mr. Bones yalnızca kaybı bir kez önler; mevcut skor durumuna göre karar ver.'
        if required == hand:
            return f'DEĞERLENDİR — {hand} ile uyumlu {kind} verir; alışveriş sonrası ${after}, faiz kaybı ${cost}.'
        if required == 'face cards':
            return f'DEĞERLENDİR — yüz kartları skorlanıyorsa yararlı; alışveriş sonrası ${after}, faiz kaybı ${cost}.'
        return f'GENELLİKLE ALMA — {required} ister, seçili ana el {hand}; ihtiyaç varsa geçici güç olarak düşünülebilir.'
    if key in (p.lower() for p in PLANETS):
        matched = next(p for p in PLANETS if p.lower() == key)
        target = PLANETS[matched]
        if target == hand:
            return f'DEĞERLENDİR — {target} seviyesini artırır; alışveriş sonrası ${after}, faiz kaybı ${cost}.'
        return f'ALMA — {target} geliştirir; ana el {hand}.'
    if key in ('overstock', 'overstock plus'):
        return f'DEĞERLENDİR — sonraki shop’larda ek ürün gösterir; ${price} maliyet için yeterli shop kalmalı (ante {ante}).'
    if key == 'clearance sale':
        return f'DEĞERLENDİR — shop indiriminden sonraki alışverişlerde faydalanırsın; alışveriş sonrası ${after}.'
    return f'BİLİNMEYEN ÜRÜN — otomatik AL kararı yok. Tooltip’i kontrol et; alışveriş sonrası ${after}, faiz kaybı ${cost}.'

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('Balatro Coach — Shop Advisor')
        self.geometry('750x680')
        self.minsize(600, 560)
        form = ttk.Frame(self, padding=14)
        form.pack(fill='both', expand=True)
        ttk.Label(form, text='Shop Advisor', font=('Arial', 18, 'bold')).pack(anchor='w')
        ttk.Label(form, text='Oyundaki ürüne fareyi getir; tooltip adını buraya yaz. Tanınmayan ürün için öneri verilmez.').pack(anchor='w', pady=(2, 14))
        row = ttk.Frame(form)
        row.pack(fill='x')
        self.money = self.field(row, 'Para ($)', '16')
        self.ante = self.field(row, 'Ante', '1')
        ttk.Label(row, text='Ana el').pack(side='left', padx=(14, 4))
        self.hand = ttk.Combobox(row, values=HANDS, state='readonly', width=17)
        self.hand.set('Three of a Kind')
        self.hand.pack(side='left')
        ttk.Label(form, text='Mevcut Joker’lar (virgülle ayır)').pack(anchor='w', pady=(15, 2))
        self.jokers = ttk.Entry(form)
        self.jokers.insert(0, 'Wily Joker')
        self.jokers.pack(fill='x')
        ttk.Label(form, text='Shop ürünleri (her satıra “ad, fiyat”; örn. Venus, 3)').pack(anchor='w', pady=(15, 2))
        self.items = scrolledtext.ScrolledText(form, height=9, wrap='word')
        self.items.insert('1.0', 'Venus, 3\nUranus, 3\nOverstock, 10')
        self.items.pack(fill='both', expand=True)
        buttons = ttk.Frame(form)
        buttons.pack(fill='x', pady=12)
        ttk.Button(buttons, text='Önerileri hesapla', command=self.calculate).pack(side='left')
        ttk.Button(buttons, text='Ekran görüntüsü al', command=self.screenshot).pack(side='left', padx=8)
        ttk.Button(buttons, text='Tooltip OCR', command=self.ocr).pack(side='left')
        ttk.Label(form, text='Sonuç').pack(anchor='w')
        self.output = scrolledtext.ScrolledText(form, height=10, wrap='word', state='disabled')
        self.output.pack(fill='both', expand=True)
        self.calculate()

    def field(self, parent, label, default):
        ttk.Label(parent, text=label).pack(side='left', padx=(0, 4))
        entry = ttk.Entry(parent, width=7)
        entry.insert(0, default)
        entry.pack(side='left', padx=(0, 12))
        return entry

    def calculate(self):
        try:
            money, ante = int(self.money.get()), int(self.ante.get())
            if money < 0 or ante < 1:
                raise ValueError
        except ValueError:
            messagebox.showerror('Hata', 'Para sıfır veya üstü, ante en az 1 olmalı.')
            return
        lines = [f'Para: ${money} | Bu shop öncesi faiz: ${interest(money)}', '']
        for item in self.items.get('1.0', 'end').splitlines():
            if not item.strip():
                continue
            match = re.fullmatch(r'\s*(.+?)\s*[,;]\s*\$?(\d+)\s*', item)
            if not match:
                lines.append(f'{item.strip()}: format “ad, fiyat” olmalı.')
                continue
            name, price = match.group(1), int(match.group(2))
            lines.append(f'{name} (${price}): {advise(name, price, money, ante, self.hand.get(), self.jokers.get())}')
        lines += ['', 'Bu öneriler garanti değildir. Joker etkisini ve kalan blind gücünü oyunda doğrula.']
        self.output.configure(state='normal')
        self.output.delete('1.0', 'end')
        self.output.insert('1.0', '\n'.join(lines))
        self.output.configure(state='disabled')

    def screenshot(self):
        try:
            import pyautogui
            from pathlib import Path
            from datetime import datetime
            filename = Path.home() / f'balatro-coach-{datetime.now():%Y%m%d-%H%M%S}.png'
            pyautogui.screenshot().save(filename)
            messagebox.showinfo('Kaydedildi', str(filename))
        except Exception as exc:
            messagebox.showerror('Ekran görüntüsü alınamadı', f'{exc}\nİşletim sistemi ekran kayıt izni gerekebilir.')

    def ocr(self):
        try:
            import pyautogui
            import pytesseract
            # OCR reads the full screen; user reviews recognition before use.
            raw = pytesseract.image_to_string(pyautogui.screenshot(), config='--psm 11')
            window = tk.Toplevel(self)
            window.title('OCR metni — adı doğrulayarak shop listesine kopyala')
            window.geometry('650x450')
            ttk.Label(window, text='OCR ham çıktısı; Joker adını ve fiyatı oyundan doğrula.').pack(padx=12, pady=8)
            box = scrolledtext.ScrolledText(window, wrap='word')
            box.insert('1.0', raw or '(Metin okunamadı. Tooltip açıkken tekrar dene.)')
            box.pack(fill='both', expand=True, padx=12, pady=8)
        except Exception as exc:
            messagebox.showerror('OCR çalışmadı', f'{exc}\nTesseract OCR kurulu ve PATH üzerinde olmalı.')

if __name__ == '__main__':
    App().mainloop()
