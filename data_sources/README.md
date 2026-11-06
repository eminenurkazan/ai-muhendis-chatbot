# Uzmanlık veri seti hazırlığı

`stackexchange_dataset.py`, Stack Exchange'in resmî API'sinden Windows Server ve Oracle için gerçek soru–cevap çiftleri toplar. İndirme, embedding ve veritabanına aktarımdan ayrıdır.

## Kaynaklar

- Server Fault: Active Directory, IIS, Windows Event Log ve Windows Server sürüm etiketleri.
- Database Administrators: Oracle; performans, tablespace, backup/RMAN ve genel Oracle soruları.

Her soru yalnız kendi kabul edilmiş cevabıyla eşleştirilir. Soru kimliği ve cevaptaki soru kimliği birlikte denetlenir. Cevabın en az 1 oy puanı olması, yeterli metin ve yazar/lisans bilgisi bulunması gerekir. Aynı soru birden fazla sorguda görünürse tek kayıt tutulur. Konular dönüşümlü seçilir; arama sonuçları rastgele tek bir başlık altında biriktirilmez.

Bu kurallar teknik doğruluğu kanıtlamaz. Kabul edilmiş cevap, soruyu soran kişinin işaretlediği cevaptır; bağımsız ortam testi veya üretim garantisi değildir. Kayıtlar `review_status=pending` ve `index_status=pending` olarak hazırlanır. `resolution_confirmed` alanı boş bırakılır. İnceleme sırasında uygun olmayan, eski veya bağlamı eksik cevaplar elenir; gerekiyorsa resmî belgelerle karşılaştırılır.

## Çalıştırma

```powershell
Set-Location -LiteralPath "D:\ai-muhendis-chatbot"
.\.venv\Scripts\python.exe -X utf8 -m data_sources.stackexchange_dataset --per-topic 60 --per-domain 200
```

`per-topic`, bir API sorgusunda istenen üst sınırdır; `per-domain`, kalite süzgecinden sonra seçilen kayıt üst sınırıdır. Daha az uygun cevap varsa bu sayıya ulaşmak için boş veya yapay kayıt üretilmez. Sorgular 2018 ve sonrasında açılmış, kapalı olmayan, kabul edilmiş cevabı bulunan soruları ister. Ürün sürümleri farklıdır; hedef sürüm uygunluğu ayrıca incelenmelidir.

Sonuçlar `outputs_local/expertise_qa/<UTC-tarih>/` altında saklanır:

| Dosya | İçeriği |
|---|---|
| `raw/request_*.json` | Değiştirilmemiş API yanıtı, istek URL'si ve alınma tarihi |
| `candidates.jsonl` | Soru–cevap, konu, etiket, yazar, lisans, kaynak URL'leri ve inceleme işaretleri |
| `manifest.json` | Sorgular, eleme nedenleri, konu dağılımı, API kotası ve indirme durumu |
| `ATTRIBUTION.md` | Her soru ve cevap için ayrı yazar, bağlantı ve lisans bilgisi |

Kod bloklarının sınırları HTML'den dönüştürülürken korunur; kaynak HTML ham yanıtlarda saklanır. Resim içeren veya eski ürün sürümü etiketli kayıtlar ayrıca işaretlenir. Cevaplar LLM ile üretilmez veya özetlenmez. Tam kodun doğru çevrildiği ve resimde kalan önemli bağlam olmadığı incelemede kontrol edilmelidir.

API yanıtları 24 saat yerel önbellekte tutulur. API'nin bekleme talimatı uygulanır; 30 saniyeyi aşan bekleme isteğinde işlem durdurulur. İndirme yarıda kalırsa `manifest.json` içinde `incomplete` yazılır. API anahtarı veya hesap girişi gerekmez. Veriler `outputs_local/` altında Git dışında kalır; yayınlanacak bir veri paketi ayrıca hazırlanmalıdır.

## Atıf ve lisans

Lisans her soru ve cevap için API'deki `content_license` alanından korunur; bütün kayıtlara tek bir lisans varsayılmaz. HTML biçiminin dönüştürüldüğü kayıt üzerinde belirtilir. Kaynak metinlerin yeniden dağıtımında ilgili atıf ve paylaşım koşulları korunmalıdır; indirilmiş olması bütün kullanım koşullarının tamamlandığı anlamına gelmez.

- [Resmî gelişmiş arama API'si](https://api.stackexchange.com/docs/advanced-search)
- [Cevap alanları ve content_license](https://api.stackexchange.com/docs/types/answer)
- [Stack Exchange içerik lisansları](https://stackoverflow.com/help/licensing)

## Test

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -p test_expertise_dataset.py -v
```

Testler yanlış cevap eşleştirmesini, eksik lisans/yazar bilgisini, kod bloklarını ve kabul edilmiş cevabın otomatik olarak onaylı çözüm sayılmamasını kontrol eder. Ağ veya model çağrısı yapmaz.

## 6 Kasım 2026: ilk onaylı aktarım

314 adaydan ilk 10 incelendi; 7 sınırlı kapsamda uygun bulundu (4 Windows, 3 Oracle), 3 elendi. Özgün candidates.jsonl pending ve salt okunur kalır. Uygulamaya alınan ayrı incelenmiş kopyalar approved/ready durumundadır. Aktarım aracı `database.import_expertise`, aynı pgvector havuzunu kaynak/alan/atıf bilgileriyle kullanır; ham cevaplar indekslenmez. [Saklama ve arama ayrıntıları](../UZMANLIK_VERILERININ_KULLANIMI.md).


## 6 Kasım 2026: ikinci aktarım

Ek 30 aday için son inceleme tamamlandı: 26 sınırlı açıklama/teşhis kaydı eklendi (18 Windows Server, 8 Oracle); 4 kayıt elendi. İlk partiyle birlikte 40 aday incelendi, 33 QA uygulamadadır, 7 aday elenmiştir. Henüz incelenmemiş 274 aday vardır. Aktarım makbuzu `outputs_local/expertise_activation_20261106_batch02/import_receipt.json`, son kararlar `outputs_local/expertise_qa_review_20261106_all_remaining/reviewed_results_final.json` dosyasındadır. Özgün aday dosyası pending olarak korunmuştur.
