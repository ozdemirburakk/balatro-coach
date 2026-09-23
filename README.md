# Balatro Coach

Balatro koşusunu izleyen Türkçe, yerel yardımcı. Deck, ante, para, mevcut Joker'lar, shop ve eldeki kartları **oyundan** okur; oyun aşaması değiştikçe öneriyi yeniler. Oyun adına tıklamaz veya hamle yapmaz. Python arayüzü tarayıcıda açılır; **Tkinter ve pip kurulumu gerekmez**.

> Katalog Balatro 1.0 için 150 Joker, 32 Voucher, 12 Planet, 22 Tarot, 18 Spectral ve 15 Deck adı içerir. Tam oyun simülasyonu değildir: bazı yaygın Joker ve kart etkileri tahmini skora katılır; kalan Joker koşulları, bazı mühürler, boss etkileri, paket içeriği ve skip tag değeri eksiktir. Katalog adı tanımak ile kartın değerini kusursuz değerlendirmek farklı şeylerdir. Belirsiz önerileri oyundaki tooltip'e göre doğrula.

## Mac kurulumu (Steam sürümü)

Steam'deki Balatro'nun indirilmesi bitince Terminal'de:

```bash
cd ~/Developer/balatro-coach
git pull
python3 setup_steam_mac.py
```

Bu komut resmî Lovely ve Steamodded sürümlerini GitHub'dan indirip Mac'teki Steam Balatro'ya ve mod klasörüne yerleştirir; Coach köprüsünü de kurar. Mevcut Lovely/Steamodded kurulumuna dokunmaz. Oyun başka Steam kitaplığındaysa `python3 setup_steam_mac.py --game-dir "/oyunun/Balatro/klasörü"` çalıştır. Sorun yaşarsan [Steamodded'ın Mac kurulum rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20mac/) bak.

Coach güncellendikten sonra köprü dosyası da değiştiyse repo dizininde `python3 install_mod.py` çalıştırıp oyunu yeniden aç. Python sayfasını da kapatıp `python3 coach.py` ile yeniden başlat.

Balatro'yu **Steam'deki Oyna düğmesiyle değil**, Finder'da Steam > Balatro > Yönet > Yerel dosyalara göz at yoluyla açılan oyun klasöründeki `run_lovely_macos.sh` dosyasını Terminal'e sürükleyip Enter'a basarak aç. Bu, Mac'te modlu oyun için gereken yöntemdir. Bir koşu başlat. Ayrı bir Terminal penceresinde:

```bash
cd ~/Developer/balatro-coach
python3 coach.py
```

Tarayıcıda açılan sayfanın üstündeki **Canlı koşu** bölümü deck ve oyun durumunu gösterir. Tarayıcı açılmazsa terminalde yazan `http://127.0.0.1:...` adresine git. Terminal açık kalmalı; kapatmak için Ctrl+C. Durum dosyasını denetlemek için: `ls -l "$HOME/Library/Application Support/Balatro/balatro_coach_state.json"`.

Zaten Lovely + Steamodded kuruluysa `python3 install_mod.py` yalnızca Coach köprüsünü kopyalar.

## Adım adım koçluk

Canlı ekrandaki **Şimdi ne yapayım?** alanı her aşamada bir sonraki eylemi gösterir: shop'tan ürün/paket satın alma veya reroll, açılan Celestial/Arcana/Spectral/Buffoon/Standard paketindeki kartı seçme, blind'ı başlatma, elde oynanacak ya da atılacak kartlar, tur sonunda Cash Out. Paket içeriği **ancak açıldıktan sonra** oyundan okunur; birden fazla kart seçiliyorsa sonraki seçim yeniden hesaplanır. Tüketilebilirlerde güvenle kullanılabilecek kart varsa önce onu söyler.

Eldeki oynama önerisi bazı Joker etkilerini ve eldeki kartların tahmini skorunu kullanır. Discard önerisi kalan desteden örnek çekilişlerle sonuçları karşılaştırır; gösterilen oran yalnızca sıradaki eli blind hedefiyle karşılaştırır. Shop kararı ekonomi ve bilinen Joker rollerine dayanır. Joker tetiklerinin tamamı, Tarot/Spectral hedeflerinin tüm koşulları, boss, paket içeriğinin açılmadan olasılığı ve tam oyun skoru hesaplanmaz. Özellikle Joker satmak veya desteyi kalıcı değiştiren bir kart seçmek gerektiğinde oyun açıklamasını kontrol et. Bağlantı çalışsa da bu kararları henüz gerçek bir Steam koşusunda paket paket doğrulamadık.

## BalatroHQ referansı

[BalatroHQ](https://balatrohq.com/) oyundaki Joker, deck ve kart etkilerini anlatan bir fan sitesidir. [Puan hesaplayıcısı](https://balatrohq.com/tools/score-calculator/) el ve Joker sırasını elle girip karşılaştırmak için kullanılır; Coach ise açık koşunun durumunu oyundan okuyup otomatik hamle önerir. Buradaki [kart geliştirmeleri](https://balatrohq.com/enhancements/), [deck etkileri](https://balatrohq.com/decks/) ve [Joker sırası rehberi](https://balatrohq.com/guides/blueprint-brainstorm-combo/) bazı kararlara referans alındı. Artık Stone/Glass/Steel ve kırmızı mührün bilinen puan etkileri, Plasma Deck puanı, Green Deck faiz kuralı ve yararlı olduğunda kart/Joker sırası önerisi uygulanır. Olasılıklı etkiler ve bütün Joker kombinasyonları hâlâ tam simüle edilmez.

## Windows

[Steamodded'ın Windows rehberine](https://docs.smods.dev/Installation/Installing%20Steamodded%20windows/) göre Lovely ve Steamodded'ı kur. Sonra `py install_mod.py` ve `py coach.py` çalıştır. Oyun modunu yüklemek için Balatro'yu yeniden aç.

## Nasıl çalışır?

`mod/` içindeki küçük Steamodded eklentisi durumu yalnızca yerel `balatro_coach_state.json` dosyasına yazar. Python bu dosyayı okur ve yalnızca `127.0.0.1` üzerinde bir sayfa açar. Oyuna komut göndermez. Canlı okuma çalışmadığında elle shop değerlendirmesi ve Mac'te isteğe bağlı tooltip OCR kullanılabilir; OCR için ayrıca `brew install tesseract` gerekir.

Öneriler shop'ta el uyumu, Joker rollerini ve ekonomiyi; elde poker eli, kart puanları, el seviyesi, desteklenen Joker etkileri ve kalan blind hedefini kullanır. Discard önerisi kalan desteden olası çekilişleri örnekler. Gösterilen **tahmini puan** kesin oyun skoru veya kazanma garantisi değildir; bilinmeyen Joker, bazı mühürler, boss ve tetikleme sırası sonucu değiştirebilir. Kartları oyundaki sıraya göre 1. A♥, 2. J♦ biçiminde gösterir. El eğilimi yalnızca seviye yükseltilmiş eller, belirgin oyun geçmişi veya uygun Joker varsa gösterilir; yeni koşuda otomatik Pair hedefi atanmaz.

Katalog kart adları ve sınıflandırma işaretleri [oyun yerelleştirme verisinin bir aynasındaki](https://github.com/Jofr3/balatro-source/blob/main/localization/en-us.lua) adlardan türetildi. Mod yapısı için [Steamodded dokümantasyonu](https://docs.smods.dev/Guides/G/) kullanıldı.
