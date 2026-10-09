# Yerel RAG API'si ve ilk düzenli değerlendirme

Tarih: 9 Ekim 2026. Bu belge, `RAG_Akisi.md` içindeki ilk 10 kayıtlık pilotun ardından gelen mevcut durumu anlatır.

## Mevcut bilgi tabanı

PostgreSQL + pgvector içinde 20 onaylı kısa ticket bulunur: ilk pilotun 10 kaydı ve ayrıca incelenmiş 10 kayıt. Her kısa kaydın problem ve çözümü birlikte tutulmuş, kayıt başına bir arama chunk'ı ve BGE-M3 ile üretilmiş 1024 boyutlu bir embedding aktarılmıştır. Uzun belgeler için çoklu chunk stratejisi henüz sınanmadı.

Yeni kayıtlar `tickets_reviewed_extra.csv` dosyasındadır. `source_comment_seq`, çözümün dayandığı özgün yorum sıralarını; `limitations`, kayıtta doğrulanmayan ayrıntıları belirtir. Yeni kayıtlar için `database.import_reviewed` komutları `check`, `embed` ve `import` sırasıyla çalıştırılmıştır. Her aşama başarılı olmuş, veritabanında toplam 20 aranabilir kayıt ve 20 chunk doğrulanmıştır.

## API'yi yerel bilgisayarda çalıştırma

Önce Docker Desktop ve PostgreSQL konteyneri çalışıyor olmalı. Yeni bir PowerShell oturumunda `DATABASE_URL` değerini `DATABASE.md` belgesindeki geliştirme veritabanı adresine ayarla. Ardından:

```powershell
Set-Location -LiteralPath "D:\ai-muhendis-chatbot"
.\.venv\Scripts\python.exe -m pip install -r .\requirements.txt
.\.venv\Scripts\python.exe -m uvicorn api:app --host 127.0.0.1 --port 8000
```

`127.0.0.1`, bu ilk sürümü yalnızca aynı bilgisayara açar. API'de kullanıcı yetkilendirmesi, kota ve üretim güvenlik önlemleri henüz yoktur; internete veya şirket ağına açılmamalıdır. Cloudflare ve ChatGPT girişleri daha önce `rag_ticket_pilotu.py` ile terminalde yapılıp Windows hesabına bağlı korumalı kayda alınmış olmalıdır. API isteği kendi kendine tarayıcıda giriş başlatmaz; kayıtlı oturum yoksa açıklayıcı hata döndürür.

Tek endpoint `POST http://127.0.0.1:8000/ask` adresidir. JSON gövdesi `{"question":"Sorunuz"}` biçimindedir. Yanıt alanları:

| Alan | Anlamı |
|---|---|
| `answer` | Ticket'lara dayalı Türkçe yanıt |
| `used_ticket_ids` | Yanıtta gerçekten kullanılan kaynak kimlikleri |
| `insufficient_context` | `true` ise ilgili kaynak yoktur; teknik çözüm uydurulmaz |
| `retrieved_ticket_ids` | Aramada gelen ilk üç adayın sırası |
| `elapsed_ms` | Embedding, arama ve yanıt üretiminin toplam süresi |

Örnek istek (sunucu ayrı pencerede açıkken):

```powershell
$body = @{ question = "Chrome normal penceresinde açılmayan URL, gizli pencerede açılıyor. Kaynakta ne denenmiş?" } | ConvertTo-Json
Invoke-RestMethod -Uri "http://127.0.0.1:8000/ask" -Method Post -ContentType "application/json; charset=utf-8" -Body ([System.Text.Encoding]::UTF8.GetBytes($body)) | Format-List
```

`rag_service.ask_question()` aynı akışı yeniden kullanılabilir bir Python fonksiyonu olarak sunar. API bu fonksiyonu çağırır. Soru 2000 karakteri geçemez. Hatalı soru `422`, hazır olmayan kayıtlı giriş `503`, diğer yanıt üretim hatası `502` durum koduyla döner. Ham token veya veritabanı bağlantı bilgisi hata yanıtına konmaz.

## Değerlendirme yöntemi

`evaluation_questions_v1.json` dosyasında 8 ilgili ve 2 kaynakta karşılığı olmayan soru vardır. İlgili soruların beklenen ticket kimlikleri arama sonuçlarına bakılmadan önce yazılmıştır. `evaluate_api.py` bu soruları sırayla API'ye gönderir ve ayrıntılı sonucu Git'e alınmayan `outputs_local/evaluation_results_v1_*.json` dosyasına kaydeder.

`İlk 3`, beklenen kaynağın ilk üç arama sonucunda bulunmasıdır. `Kaynak uyumu`, yanıtın onaylı ticket özetindeki problem, çözüm, sonuç ve sınırlamalarla elle karşılaştırılmasıdır; yalnızca kimliğin yanıt metninde geçmesi yeterli sayılmadı. Bu turda özgün yorumlara ikinci bir tam denetim yapılmadı; özetlerin daha önceki manuel incelemesi temel alındı.

| Soru | Beklenen kaynak | Sıra / kapsam dışı sonuç | Kullanılan kaynak | Süre (ms) | Kaynak uyumu |
|---|---|---|---|---:|---|
| Q01 | `1005127.0` | 1. sıra | `1005127.0` | 9332 | Uygun |
| Q02 | `1007295.0` | 1. sıra | `1007295.0` | 10738 | Uygun |
| Q03 | `1010047.0` | 1. sıra | `1010047.0` | 12023 | Uygun; müşteri onayı yok sınırı korunmuş |
| Q04 | `1005816.0` | 1. sıra | `1005816.0` | 9517 | Uygun; üretim sonucu kesinleştirilmemiş |
| Q05 | `1010541.0` | 1. sıra | `1010541.0` | 9761 | Uygun |
| Q06 | `1005097.0` | 1. sıra | `1005097.0` | 10800 | Uygun; gizli parametre değeri uydurulmamış |
| Q07 | `1007444.0` | 1. sıra | `1007444.0` | 9300 | Uygun; UAT ve üretim ayrılmış |
| Q08 | `1006536.0` | 1. sıra | `1006536.0` | 9064 | Uygun; manuel işlemin tamamlandığı iddia edilmemiş |
| Q09 | Kaynak yok | İlgisiz adayları reddetti | Yok | 11312 | Uygun; BitLocker adımı uydurulmamış |
| Q10 | Kaynak yok | İlgisiz adayları reddetti | Yok | 9045 | Uygun; RMAN komutu uydurulmamış |

Özet: ilgili sorularda beklenen kaynak ilk üçte **8/8**, hatta ilk sırada **8/8**; kaynakta karşılığı olmayan sorularda doğru çekimserlik **2/2**. On yanıtın ortalama süresi **10089 ms** (yaklaşık 10,1 saniye). Elle karşılaştırmada bu 10 yanıt için kaynak dışı teknik talimat tespit edilmedi.

Bu sonuçlar yalnızca önceden seçilmiş 10 soruyu ve mevcut 20 kısa kaydı kapsar. Genel doğruluk, farklı kurum verisi veya üretim yükü için başarı garantisi değildir. Sonraki ölçümde daha uzun kayıtlar, farklı ifade edilmiş sorular, çoklu chunk ve daha büyük değerlendirme seti gerekir.
