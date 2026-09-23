# Balatro Coach

Balatro koşusunu izleyen Türkçe, yerel yardımcı. Deck, ante, para, mevcut Joker'lar, shop ve eldeki kartları **oyundan** okur; oyun aşaması değiştikçe öneriyi yeniler. Oyun adına tıklamaz veya hamle yapmaz. Python arayüzü tarayıcıda açılır; **Tkinter ve pip kurulumu gerekmez**.

> Katalog Balatro 1.0 için 150 Joker, 32 Voucher, 12 Planet, 22 Tarot, 18 Spectral ve 15 Deck adı içerir. Tam oyun simülasyonu değildir: Joker'ların bütün koşulları, enhancement, olasılıklar, gerçek skor, boss etkileri, paket içeriği ve skip tag değeri henüz hesaplanmaz. Katalog adı tanımak ile kartın değerini kusursuz değerlendirmek farklı şeylerdir. Belirsiz önerileri oyundaki tooltip'e göre doğrula.

## Mac kurulumu (Steam sürümü)

1. [Steamodded'ın Mac kurulum rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20mac/) göre **Lovely + Steamodded** kur. Mac'te oyunu rehberdeki `run_lovely_macos.sh` ile başlat. Mod klasörünün yolu `~/Library/Application Support/Balatro/Mods` olmalı.
2. Repo dizininde köprüyü kur:

   ```bash
   cd ~/Developer/balatro-coach
   git pull
   python3 install_mod.py
   ```

3. Balatro'yu modlu biçimde yeniden başlat ve bir koşu aç. Ayrı bir terminalde:

   ```bash
   cd ~/Developer/balatro-coach
   python3 coach.py
   ```

Tarayıcıda açılan sayfanın üstündeki **Canlı koşu** bölümü deck ve oyun durumunu gösterir. Tarayıcı açılmazsa terminalde yazan `http://127.0.0.1:...` adresine git. Terminal açık kalmalı; kapatmak için Ctrl+C.

Steamodded zaten kuruluysa yalnızca 2. ve 3. adımı uygula. Oyun modlu açılmazsa canlı durum görünmez. Dosyanın üretildiğini kontrol etmek için:

```bash
ls -l ~/Library/Application\ Support/Balatro/balatro_coach_state.json
```

## Windows

[Steamodded'ın Windows rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20windows/) göre Lovely ve Steamodded'ı kur. Sonra `py install_mod.py` ve `py coach.py` çalıştır. Oyun modunu yüklemek için Balatro'yu yeniden aç.

## Nasıl çalışır?

`mod/` içindeki küçük Steamodded eklentisi durumu yalnızca yerel `balatro_coach_state.json` dosyasına yazar. Python bu dosyayı okur ve yalnızca `127.0.0.1` üzerinde bir sayfa açar. Oyuna komut göndermez. Canlı okuma çalışmadığında elle shop değerlendirmesi ve Mac'te isteğe bağlı tooltip OCR kullanılabilir; OCR için ayrıca `brew install tesseract` gerekir.

Öneriler şu anda shop'ta temel el uyumu, chip/Mult ihtiyacı ve faiz eşiğini; el sırasında yaklaşık poker elini; blind seçimi sırasında temel ekonomi yaklaşımını kullanır. **Win garantisi ve kesin skor hesabı yoktur.** Kapsamlı strateji motoru için Joker tetiklerinin, boss kurallarının ve oynanacak elin gerçek skorunun modellenmesi gerekir.

Katalog kart adları ve sınıflandırma işaretleri [oyun yerelleştirme verisinin bir aynasındaki](https://github.com/Jofr3/balatro-source/blob/main/localization/en-us.lua) adlardan türetildi. Mod yapısı için [Steamodded dokümantasyonu](https://docs.smods.dev/Guides/G/) kullanıldı.
