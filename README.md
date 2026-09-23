# Balatro Coach

Balatro koşusunu izleyen Türkçe, yerel yardımcı. Deck, ante, para, mevcut Joker'lar, shop ve eldeki kartları **oyundan** okur; oyun aşaması değiştikçe öneriyi yeniler. Oyun adına tıklamaz veya hamle yapmaz. Python arayüzü tarayıcıda açılır; **Tkinter ve pip kurulumu gerekmez**.

> Katalog Balatro 1.0 için 150 Joker, 32 Voucher, 12 Planet, 22 Tarot, 18 Spectral ve 15 Deck adı içerir. Tam oyun simülasyonu değildir: Joker'ların bütün koşulları, enhancement, olasılıklar, gerçek skor, boss etkileri, paket içeriği ve skip tag değeri henüz hesaplanmaz. Katalog adı tanımak ile kartın değerini kusursuz değerlendirmek farklı şeylerdir. Belirsiz önerileri oyundaki tooltip'e göre doğrula.

## Mac kurulumu (Steam sürümü)

Steam'deki Balatro'nun indirilmesi bitince Terminal'de:

```bash
cd ~/Developer/balatro-coach
git pull
python3 setup_steam_mac.py
```

Bu komut resmî Lovely ve Steamodded sürümlerini GitHub'dan indirip Mac'teki Steam Balatro'ya ve mod klasörüne yerleştirir; Coach köprüsünü de kurar. Mevcut Lovely/Steamodded kurulumuna dokunmaz. Oyun başka Steam kitaplığındaysa `python3 setup_steam_mac.py --game-dir "/oyunun/Balatro/klasörü"` çalıştır. Sorun yaşarsan [Steamodded'ın Mac kurulum rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20mac/) bak.

Balatro'yu **Steam'deki Oyna düğmesiyle değil**, Finder'da Steam > Balatro > Yönet > Yerel dosyalara göz at yoluyla açılan oyun klasöründeki `run_lovely_macos.sh` dosyasını Terminal'e sürükleyip Enter'a basarak aç. Bu, Mac'te modlu oyun için gereken yöntemdir. Bir koşu başlat. Ayrı bir Terminal penceresinde:

```bash
cd ~/Developer/balatro-coach
python3 coach.py
```

Tarayıcıda açılan sayfanın üstündeki **Canlı koşu** bölümü deck ve oyun durumunu gösterir. Tarayıcı açılmazsa terminalde yazan `http://127.0.0.1:...` adresine git. Terminal açık kalmalı; kapatmak için Ctrl+C. Durum dosyasını denetlemek için: `ls -l "$HOME/Library/Application Support/Balatro/balatro_coach_state.json"`.

Zaten Lovely + Steamodded kuruluysa `python3 install_mod.py` yalnızca Coach köprüsünü kopyalar.

## Windows

[Steamodded'ın Windows rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20windows/) göre Lovely ve Steamodded'ı kur. Sonra `py install_mod.py` ve `py coach.py` çalıştır. Oyun modunu yüklemek için Balatro'yu yeniden aç.

## Nasıl çalışır?

`mod/` içindeki küçük Steamodded eklentisi durumu yalnızca yerel `balatro_coach_state.json` dosyasına yazar. Python bu dosyayı okur ve yalnızca `127.0.0.1` üzerinde bir sayfa açar. Oyuna komut göndermez. Canlı okuma çalışmadığında elle shop değerlendirmesi ve Mac'te isteğe bağlı tooltip OCR kullanılabilir; OCR için ayrıca `brew install tesseract` gerekir.

Öneriler şu anda shop'ta temel el uyumu, chip/Mult ihtiyacı ve faiz eşiğini; el sırasında yaklaşık poker elini; blind seçimi sırasında temel ekonomi yaklaşımını kullanır. **Win garantisi ve kesin skor hesabı yoktur.** Kapsamlı strateji motoru için Joker tetiklerinin, boss kurallarının ve oynanacak elin gerçek skorunun modellenmesi gerekir.

Katalog kart adları ve sınıflandırma işaretleri [oyun yerelleştirme verisinin bir aynasındaki](https://github.com/Jofr3/balatro-source/blob/main/localization/en-us.lua) adlardan türetildi. Mod yapısı için [Steamodded dokümantasyonu](https://docs.smods.dev/Guides/G/) kullanıldı.
