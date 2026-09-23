# Balatro Coach — Shop Advisor (ilk sürüm)

Balatro shop'unda Joker/Planet/Voucher alışverişi için Türkçe masaüstü yardımcısı. Oyun dosyalarını değiştirmez, tıklama yapmaz. **Kartı kendi kendine kesin olarak tanımaz:** tooltip adını ve fiyatını girersin; isteğe bağlı OCR yalnızca kontrol edilecek ham metni gösterir. Yanlış Joker adını özgüvenle söylememesi için bilinmeyen ürünlerde karar üretmez.

## Kurulum

Python 3.10+ ile Windows PowerShell:

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python coach.py
```

macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.txt
python coach.py
```

Linux'ta `python3-tk` paketini kurman gerekebilir. Ekran görüntüsü için işletim sisteminin ekran kayıt iznini ver. **OCR** düğmesi için ayrıca [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) uygulamasını yükleyip PATH'e ekle; uygulamanın diğer bölümleri Tesseract olmadan çalışır. OCR İngilizce oyun arayüzü için tasarlanmıştır.

## Kullanım

1. Para, ante, oynadığın ana el ve mevcut Joker'ları gir.
2. Her ürün için tooltip'teki **doğru adı** ve fiyatı `Venus, 3` biçiminde yeni satıra yaz.
3. **Önerileri hesapla** düğmesine bas. Sonuçları oyundaki etki, blind ve kalan bütçeyle karşılaştır.
4. İstersen fareyi kartta tutup **Tooltip OCR** ile ekrandaki ham metni aç; adı ve fiyatı **kendin doğrula**. **Ekran görüntüsü al** düğmesi bir PNG'yi ev klasörüne kaydeder.

Varsayılan alanlar önceki Yellow Deck koşusundaki Wily Joker / $16 durumuna örnektir; yeni koşuda değiştir.

## Sınırlar

Öneriler basit kurallara dayanır ve desteklenen küçük katalog dışındaki ürünleri tanımaz. Kart sürümü, edition, stake, blind, oynanmış el seviyesi, deste ve gerçek skor hesaplanmaz. Bu sürüm otomatik oyun durumu okuma, güvenilir görüntü eşleştirme veya otomatik alışveriş vaat etmez. Desteklenen ürünler `coach.py` içindeki `JOKERS`, `PLANETS` ve iki voucher'dır.
