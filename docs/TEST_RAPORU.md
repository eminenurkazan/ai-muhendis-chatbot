# Test Raporu: Akıllı Servis Masası ve Sistem Uzmanı Chatbot

**Proje:** PRJIC20260201 · **Test tarihi:** 26 Kasım 2026 · **Soru seti:** V3 (23 soru)

Bu rapor, proje isterlerindeki tamamlanma kriterini karşılamak için hazırlanmıştır: *en az 10 servis masası senaryosu, 5 Windows Server sorunu ve 5 Oracle DB optimizasyon sorusu ile yapılan testlerin sonuçları.* Bu kapsama ek olarak, bilgi tabanında karşılığı olmayan 3 soruyla sistemin yanıt uydurmadığı sınanmıştır.

## 1. Özet

| Grup | Soru | Beklenen kaynak 1. sırada | Beklenen kaynak yanıtta kullanıldı | Elle inceleme: uygun / kısmen / uygunsuz | Ort. süre |
|---|---|---|---|---|---|
| Servis masası | 10 | 10/10 | 10/10 | 7 / 3 / 0 | 6,7 sn |
| Windows Server | 5 | 5/5 | 5/5 | 5 / 0 / 0 | 10,2 sn |
| Oracle DB optimizasyon | 5 | 5/5 | 5/5 | 5 / 0 / 0 | 10,8 sn |
| Kaynak dışı (olumsuz test) | 3 | — | Doğru ret: 3/3 | 3 / 0 / 0 | 5,3 sn |
| **Toplam** | **23** | **20/20** | **20/20** | **20 / 3 / 0** | **8,2 sn** |

- 23 isteğin hepsi hatasız tamamlandı: zaman aşımı ve yeniden deneme olmadı.
- 23 yanıtın hepsinde kullanılan kaynak kimlikleri arama adaylarının içindeydi; uydurma kaynak kimliği yoktu.
- Hiçbir yanıtta sorunun "iddia edilmemesi gerekenler" listesindeki bir ifade görülmedi.
- "Kısmen uygun" bulunan 3 yanıtın tamamı servis masası grubundadır. Bu yanıtlar kaynakla çelişmiyor, ancak kaynakta yazmayan küçük bir nitelendirme ekliyor (bkz. Bölüm 5).

## 2. Test ortamı

| Bileşen | Değer |
|---|---|
| Uygulama | FastAPI (yerel, `127.0.0.1:8000`), asenkron uçlar |
| Test edilen akış | Arayüzle aynı yol: her soru için `POST /chats` (sorunun uzmanlık moduyla), ardından `POST /chats/{id}/ask`. Soru–yanıt MSSQL'e kaydedildi. |
| Kimlik doğrulama | Ayrı bir test kullanıcısı ile JWT oturumu (`role=user`) |
| Bilgi tabanı | PostgreSQL 16 + pgvector 0.8.7; 458 kayıt / 458 chunk, hepsi `approved/ready` |
| Bilgi tabanı dağılımı | 191 servis masası ticket'ı · 156 Windows ve 99 Oracle topluluk soru–cevabı · 5 Microsoft ve 7 Oracle resmî rehber kaydı |
| Embedding | Cloudflare Workers AI `@cf/baai/bge-m3` (1024 boyut) |
| Yanıt modeli | `gpt-5.6-terra` |
| Prompt sürümü | `2026-11-12-guide-v1` |
| Arama | Uzmanlık moduna göre alan filtresi, cosine benzerliğiyle ilk 3 aday |
| İlişkisel veritabanı | SQL Server 2022 Express, ODBC Driver 17 |
| Çalıştırma | 26.11.2026 13:21:41 – 13:24:51 (+03:00), tek çalıştırma |

## 3. Yöntem

### 3.1 Soru setinin hazırlanması

Soru seti [evaluation/evaluation_questions_v3.json](../evaluation/evaluation_questions_v3.json) dosyasındadır. Sorular ve beklenen kaynaklar **çalıştırmadan önce** sabitlendi. Seçim sırasında bilgi tabanında arama denemesi yapılmadı, çalıştırmadan sonra da soru veya ölçüt değiştirilmedi. Çalıştırılan dosyanın SHA-256 değeri sonuç dosyasında kayıtlıdır (`7e94e700…a32def`) ve depodaki dosyayla aynıdır.

| Grup | Soru kimliği | Kaynak |
|---|---|---|
| Servis masası | SD01–SD08 | 5 Kasım V2 setindeki 8 ilgili soru; metin ve ölçütler aynen alındı (karşılaştırma için) |
| | SD09–SD10 | Daha önce test edilmemiş iki ticket (Tomcat süreç çakışması, süresi dolmuş Tomcat sertifikası) |
| Windows Server | WS01–WS05 | Active Directory yönetimi (çoğaltma raporu, etki alanına katılma, hesap kilitlenmesi), IIS yapılandırması (403.14), Event Log analizi (WAS 5013, kilitlenme olayları) |
| Oracle DB | OR01–OR05 | SQL optimizasyonu: EXPLAIN PLAN, erişim yolları, optimizer istatistikleri, sorgu dönüşümleri, Real-Time SQL Monitoring |
| Kaynak dışı | NS01–NS03 | DHCP failover kurulumu, Data Guard ile standby'ı devreye alma, WSUS istemci komutları |

Kaynak dışı soruların seçiminde bilgi tabanı anahtar kelimeyle tarandı:
- **WSUS** hiç geçmiyor.
- **DHCP** ve **Data Guard** için ilgili ama soruyu yanıtlamayan topluluk kayıtları var: DHCP lease/DNS ve Data Guard yedekleme. Bu nedenle NS01 ve NS02, "yakın ama yetersiz kaynak" karşısındaki davranışı ölçen daha zor testlerdir.

Her soruda iki liste bulunur. `required_points` listesi yanıtta olması gerekenleri, `must_not_claim` listesi iddia edilmemesi gerekenleri tanımlar. Servis masası soruları için V2 ölçütleri aynen kullanıldı. Windows ve Oracle ölçütleri bilgi tabanındaki kayıt içeriğiyle karşılaştırılarak yazıldı. Bu karşılaştırmada bir ölçütteki hata düzeltildi: WS03 ölçütünde kayıtta olmayan bir IIS sürüm sınırı yazıyordu.

### 3.2 Otomatik ölçümler

Çalıştırma [evaluate_api.py](../evaluate_api.py) ile yapıldı. Beklenen kaynaklar ve ölçütler API'ye gönderilmez.

| Ölçüm | Tanım |
|---|---|
| İlk 3 / 1. sıra | Beklenen kaynak, aramanın döndürdüğü ilk 3 aday içinde / ilk sırada mı |
| Beklenen kaynak kullanıldı | Model, beklenen kaynağı `used_ticket_ids` içinde bildirdi mi |
| Kaynak kimliği geçerliliği | Kullanılan kimlikler arama adaylarının alt kümesi mi (uydurma kimlik yok) |
| Doğru ret | Kaynak dışı soruda `insufficient_context=true` ve kullanılan kaynak yok |
| Süre | API'nin ölçtüğü `elapsed_ms`: embedding + arama + model. Uçtan uca HTTP süresini ve MSSQL kaydını içermez. |

### 3.3 Elle inceleme

Her yanıt iki şeyle karşılaştırıldı:
1. Sorunun `required_points` ve `must_not_claim` listeleri.
2. Modele bağlam olarak verilen chunk metninin tamamı. Buna kaydın ortam/ön koşul alanı da dahildir.

Değerlendirme ölçüsü V2 ile aynıdır:
- **Uygun:** Yanıttaki her olgu kaynakta var; kaynağın sınırları (doğrulanmamış sonuç, müşteri teyidi yok vb.) korunuyor.
- **Kısmen uygun:** Kaynakla çelişmiyor, ancak kaynakta yazmayan bir nitelendirme ekliyor ya da iki ayrı bilgiyi birleştiriyor.
- **Uygunsuz:** Kaynakla çelişen, uydurma veya `must_not_claim` listesindeki bir iddia içeriyor.

Eksik ayrıntı ile yanlış bilgi ayrı tutuldu. Kaynaktaki bir ayrıntının yanıtta olmaması "kapsam kısmi" olarak not edildi; tek başına "kısmen uygun" sayılmadı.

> **İnceleyen:** Elle inceleme Claude (yapay zekâ asistanı) tarafından yapılmıştır ve insan onayı beklemektedir. Gerekçeler aşağıda ve inceleme dosyasında soru bazında yazılıdır.

## 4. Soru bazında sonuçlar

| Soru | Mod | Beklenen kaynak | Sıra | Süre (sn) | Elle inceleme | Not |
|---|---|---|---|---|---|---|
| SD01 | service_desk | 1008656.0 | 1 | 6,2 | Uygun | Neden, işlem ve bildirimi yapanın destek ekibi olduğu doğru |
| SD02 | service_desk | 1009846.0 | 1 | 6,4 | Uygun | V2'deki "ek ihtimal" sorunu görülmedi |
| SD03 | service_desk | 1006956.0 | 1 | 8,0 | **Kısmen uygun** | Öneri ile yapılan işlem birleştirilmiş |
| SD04 | service_desk | 1008137.0 | 1 | 7,3 | Uygun | Resetin kanıtlanmadığı doğru belirtildi |
| SD05 | service_desk | 1007291.0 | 1 | 6,7 | Uygun | UAT teyidi ile production aktarımı doğru ayrıldı |
| SD06 | service_desk | 1004444.0 | 1 | 5,7 | **Kısmen uygun** | Kaynakta olmayan "geçici önlem" nitelendirmesi |
| SD07 | service_desk | 1010324.0 | 1 | 7,0 | **Kısmen uygun** | Kaynakta olmayan "geçici çözüm" nitelendirmesi |
| SD08 | service_desk | 1006259.0 | 1 | 7,2 | Uygun | Önerinin uygulanmadığı doğru belirtildi |
| SD09 | service_desk | 1005689.0 | 1 | 6,5 | Uygun | Başarıyı destek ekibinin bildirdiği doğru |
| SD10 | service_desk | 1007932.0 | 1 | 6,5 | Uygun | Yük dengeleyici adımı koşullu olarak sunuldu |
| WS01 | windows_server | microsoft:kb2498185 | 1 | 10,9 | Uygun | Komut yalnız raporlar, onarmaz |
| WS02 | windows_server | microsoft:kb4341920 | 1 | 9,6 | Uygun | `nltest /dsgetdc`, DNS adı, NetSetup.log |
| WS03 | windows_server | microsoft:kb942062 | 1 | 8,3 | Uygun | Kullanıcının isteğine uygun yöntem seçildi |
| WS04 | windows_server | microsoft:kb824209 | 1 | 12,4 | Uygun (kapsam kısmi) | Aracın ayrıca indirilmesi gerektiği söylenmedi |
| WS05 | windows_server | microsoft:kb2634635 | 1 | 9,7 | Uygun | IIS 7.0/7.5 kapsamını belirtip sürüm sordu |
| OR01 | oracle_db | oracle:…:explain-plan-basic | 1 | 9,0 | Uygun | Tahmini planın gerçek çalışmayla aynı olmadığı belirtildi |
| OR02 | oracle_db | oracle:…:optimizer-access-paths | 1 | 11,8 | Uygun | İkinci kaynak (istatistik rehberi) yerinde kullanıldı |
| OR03 | oracle_db | oracle:…:gathering-optimizer-statistics | 1 | 10,7 | Uygun (kapsam kısmi) | Otomatik istatistik toplama görevi geçmiyor |
| OR04 | oracle_db | oracle:…:query-transformations | 1 | 8,7 | Uygun | İpucu adı uydurulmadı |
| OR05 | oracle_db | oracle:…:real-time-sql-monitoring | 1 | 13,8 | Uygun | Tuning Pack lisans uyarısı verildi |
| NS01 | windows_server | — | — | 4,4 | Uygun (doğru ret) | Komut uydurmadı, sürüm ve kapsam sordu |
| NS02 | oracle_db | — | — | 6,8 | Uygun (doğru ret) | Yakın Data Guard kayıtlarını dayanak yapmadı |
| NS03 | windows_server | — | — | 4,7 | Uygun (doğru ret) | Komut uydurmadı, hata kodu sordu |

## 5. Bulgular

### 5.1 Kısmen uygun bulunan yanıtlar

- **SD03 (otomatik yedekleme):** Kayıtta "Windows üzerinden zamanlama" bir **öneri** olarak, "HQ DB sunucusuna script ve günlük job eklenmesi" ise **yapılan işlem** olarak ayrı yazılıdır. Yanıt bu ikisini birleştirip "Windows üzerinde job eklendiği bildirilmiş" diyor. Haftalık tam yedeğin ve geri yüklemenin doğrulanmadığını ise doğru aktarıyor.
- **SD06 (tarama tarihi):** Uygulanan önlemi "geçici bir önlem olarak ele alınmış" diye nitelendiriyor. Kayıtta bu nitelendirme yok; kayıt yalnızca önlemin tarihleri düzelttiği anlamına gelmediğini söylüyor.
- **SD07 (12 öğe):** "Bu yaklaşım geçici çözüm kapsamındadır" diyor; kayıtta bu ifade yok. Tek öğe teyidinin 12 öğeye genellenemeyeceğini ise doğru söylüyor.

**Ortak örüntü:** Model, kaynağın sınırlama notlarını ("tarihleri düzelttiği anlamına gelmez", "kök neden incelemesi isteniyor") kendi "geçici çözüm" yorumuna çeviriyor. Bu, V2'de görülen "kaynakta olmayan nedensel yorum" sorununun daha hafif bir türüdür. Kullanıcıyı yanlış yönlendirecek bir eylem önerisi içermiyor, ancak kaynağa dayanmayan bir değerlendirmeyi kaynak bilgisi gibi sunuyor.

### 5.2 Eksik ayrıntılar (yanlış bilgi değil)

- **WS04:** EventCombMT'nin ayrıca indirilmesi gerektiği kayıtta var, yanıtta yok. Bu eksik 12 Kasım kontrolünde de görülmüştü.
- **OR03:** Oracle'ın otomatik istatistik toplama görevi kayıtta var, yanıtta yok.
- **SD03, SD06, SD07:** Bazı arka plan ayrıntıları eksik: HQ sunucusu, uygulama iznini kimin verdiği, önceki başarısız denemeler.

### 5.3 Olumlu gözlemler

- **Kaynak sınırlarının korunması:** Yanıtlar, kaynakta sonucu kimin doğruladığını ayırdı (müşteri teyidi mi, destek ekibi bildirimi mi). Doğrulanmamış sonuçları başarı olarak sunmadı (SD01, SD04, SD05, SD07, SD08).
- **Sürüm ve yetki sınırları:**
  - WS04, olay kimliklerinin eski Windows sürümlerine ait olduğunu belirtti; bu uyarı 12 Kasım kontrolünde eksikti.
  - WS05, rehberin IIS 7.0/7.5 kapsamını belirtip kullanıcının sürümünü sordu.
  - OR05, Tuning Pack lisans gereksinimini belirtti.
- **Yakın ama yetersiz kaynakta doğru ret:** NS02'de arama iki Data Guard yedekleme kaydı getirdi. Model bunları failover sorusuna dayanak yapmadı ve kesinti/veri kaybı riskini gerekçe göstererek komut vermedi.
- **Markdown ve kod blokları:** Windows (`cmd`, `console`) ve Oracle (`sql`) yanıtlarında komutlar kod bloğu içinde verildi. İsterlerdeki biçim gereği karşılandı.
- **Doğrulanan ifadeler:** OR01, OR03 ve OR05'teki yetki ve lisans parametresi ifadeleri ilk bakışta kaynak dışı göründü. Chunk metninde kontrol edildi; kaydın ortam/ön koşul alanında yer alıyorlar.

## 6. V2 (5 Kasım 2026) ile karşılaştırma

SD01–SD08, V2'deki V2Q01–V2Q08 sorularıyla aynı metne sahiptir.

| | V2 (5 Kasım) | V3 (26 Kasım), SD01–SD08 |
|---|---|---|
| Bilgi tabanı | 191 kayıt (yalnız ticket) | 458 kayıt (ticket + QA + rehber) |
| Prompt sürümü | `2026-10-22-v1` | `2026-11-12-guide-v1` |
| Akış | `/ask` (kayıtsız) | `/chats/{id}/ask` (kalıcı sohbet) |
| Beklenen kaynak 1. sırada | 8/8 | 8/8 |
| Ortalama süre | 9,3 sn | 6,8 sn |
| Elle inceleme | 7 uygun, 1 kısmen (V2Q02) | 5 uygun, 3 kısmen (SD03, SD06, SD07) |

- Bilgi tabanı 191 kayıttan 458'e büyüdüğü ve aynı havuzda Windows/Oracle kayıtları bulunduğu halde servis masası sorularında arama doğruluğu korundu.
- V2Q02'deki ek ihtimal sorunu bu çalıştırmada görülmedi.
- Bu çalıştırmada üç yanıtta yeni küçük nitelendirmeler görüldü. Model çıktısı her çalıştırmada değişebilir. İki değerlendirmeyi farklı kişiler yaptı ve bu incelemede kaynağa bağlılık chunk metni üzerinden daha sıkı kontrol edildi. Bu nedenle farkın bir gerilemeden mi yoksa çalıştırmalar arası değişkenlikten mi kaynaklandığı tek çalıştırmayla belirlenemez.

## 7. Sınırlılıklar

1. **Tek çalıştırma:** Her soru bir kez soruldu. Model çıktısı tekrarlarda değişebilir; sonuçlar istatistiksel bir başarı oranı değildir.
2. **İyimser kaynak seçimi:** Windows ve Oracle soruları, isterlerdeki konular için önceden bilgi tabanına eklenmiş resmî rehberlere dayanır. Rehberler test konularına göre seçildiği için bu gruplardaki 5/5 arama başarısı iyimserdir. Rehber kapsamı dışındaki Windows/Oracle sorularında, örneğin 255 topluluk kaydına dayanan sorularda, başarı ayrıca ölçülmemiştir.
3. **Komutlar gerçek ortamda çalıştırılmadı:** Yanıtlardaki repadmin, nltest, EventCombMT, EXPLAIN PLAN, DBMS_STATS vb. komutlar gerçek Active Directory, IIS veya Oracle ortamında denenmedi. Değerlendirme, yanıtın kaynağa bağlılığını ölçer; komutun hedef ortamda başarılı olacağını kanıtlamaz.
4. **Kaynak doğruluğu:** Değerlendirme kaynağı doğru kabul eder. Ticket kayıtlarındaki çözümlerin ya da rehber özetlerinin kendisi bu testte bağımsız olarak doğrulanmadı.
5. **Elle inceleme tek kişiliktir:** İncelemeyi Claude yaptı; ikinci bir insan incelemesi yapılmadı.
6. **Süre ölçümü:** `elapsed_ms` API içi süredir. Tarayıcı, ağ ve MSSQL'e kayıt süresini içermez. Bulut model süresi çalıştırmalar arasında dalgalanır; 12 Kasım'da tek bir zaman aşımı gözlenmişti, bu çalıştırmada gözlenmedi.
7. **Kapsam dışı yetenekler:** Konuşma bağlamının sürdürülmesi (önceki mesajları hatırlama), yanıt puanlama, admin raporu ve kullanıcı yönetimi bu 23 soruluk testin konusu değildir. Bu özellikler aşağıdaki yazılım testleriyle sınanmıştır.

## 8. Yazılım testleri (aynı gün)

Bulut model çağrısı yapmayan otomatik testler 26 Kasım 2026'da yeni Windows kurulumunda çalıştırıldı:

| Kapsam | Sonuç |
|---|---|
| Tüm birim testleri (`python -m unittest discover -s tests`) | 173 test: 158 geçti, 14 atlandı (veritabanı ayarı gerektiren testler), 1 hata. Hata bir Streamlit arayüz testinin toplu koşuda 20 sn zaman aşımına uğramasıdır; test tek başına iki kez çalıştırıldığında geçti. |
| Gerçek SQL Server ile entegrasyon (kayıt, giriş, sohbet geçmişi, kalıcı sohbet, geri bildirim, admin raporu, uygulama günlüğü) | 88/88 geçti; ayrıca `verify_repository.ps1` 6/6 |
| Gerçek PostgreSQL ile Bilgi Merkezi, RAG akışı ve uzmanlık testleri | 29/29 geçti; kayıt sayısı 458 olarak kaldı |
| Değerlendirme aracı (`tests/test_evaluate_api.py`) | 13/13 geçti |

Entegrasyon testlerinin eklediği kayıtlar transaction ile geri alındı.

## 9. Öneriler

1. **Prompt düzeltmesi:** Prompt'a "kaynak açıkça 'geçici' veya 'workaround' demiyorsa çözümü öyle nitelendirme; öneriyi yapılan işlemle birleştirme" kuralı eklenmeli. Ardından SD03, SD06 ve SD07 hedefli olarak yeniden denenmeli. Prompt sürümü değişeceği için tam set de tekrar çalıştırılmalı.
2. **Tekrarlı ölçüm:** Değişkenliği görmek için set en az 3 kez çalıştırılıp sonuçlar soru bazında karşılaştırılmalı.
3. **Rehber dışı sorular:** Windows ve Oracle için topluluk kayıtlarına dayanan, rehberlerden bağımsız 5'er ek soru hazırlanmalı. Böylece Bölüm 7'deki iyimserlik ölçülebilir.
4. **Eksik içerik:** EventCombMT rehber kaydına "araç ayrıca indirilir" bilgisi daha belirgin biçimde, örneğin çözüm adımlarının başına, eklenebilir.
5. **Çok turlu test:** "Önceki mesajları hatırlama" isteri için 2–3 adımlı birkaç sohbet senaryosu değerlendirme setine eklenmeli.

## 10. Tekrar çalıştırma

API açık ve hesap erişimleri hazırken (bulut çağrısı yapar, 23 model isteği):

```powershell
Set-Location -LiteralPath "D:\ai-muhendis-chatbot"
$env:APP_ACCESS_TOKEN = "<girişten alınan token>"
.\.venv\Scripts\python.exe evaluate_api.py --questions evaluation\evaluation_questions_v3.json --output-dir outputs_local\evaluation_set_v3\runs
```

Bu çalıştırmada kullanılan `evaluate_api.py` sürümünün SHA-256 değeri sonuç dosyasında kayıtlıdır (`66bcc78a…07bc`). Depodaki güncel sürüm, sonradan yapılan klasör düzenlemesi (`4d88e70`) nedeniyle yalnızca varsayılan dosya yollarında farklıdır.

## 11. Kanıt dosyaları

Aşağıdaki dosyalar yerelde Git dışında tutulur (`outputs_local/`):

| Dosya | İçerik |
|---|---|
| `outputs_local/evaluation_set_v3/runs/evaluation_results_v3_20261126_132141_860039.json` | 23 sorunun ham sonucu: yanıt metni, kaynak kimlikleri, kaynak görüntüleri, süreler |
| `…_860039.meta.json` | Çalıştırma bilgileri: başlangıç/bitiş, soru ve araç hash'leri, kategori özetleri |
| `…_860039_manual_review.json` | Soru bazında elle inceleme kararı, gerekçe ve bulunan sorunlar |

Test sohbetleri ayrıca MSSQL `ServisMasasiApp` veritabanında test kullanıcısının sohbetleri olarak kayıtlıdır.

## Ek A: Test soruları

**Servis masası**
- **SD01:** Sürüm yükseltmesinden sonra kullanıcı denetim kayıtlarını gösteren rapor sayfası açılmıyor. Benzer olayda sorun neye bağlanmış, ne yapılmış ve sonucu kim bildirmiş?
- **SD02:** Yeni sunucudan bağlantı kurarken unknown host hatası alıyoruz. IP adresiyle erişim var ama sunucu adıyla yok. Benzer kayıtta ne kontrol edilmiş; bağlantının açılması tüm uygulama sorunlarının da çözüldüğünü gösteriyor mu?
- **SD03:** Veritabanı için otomatik yedek alınmıyor. Benzer kayıtta günlük yedekleme nasıl zamanlanmış? Haftalık tam yedeğin ve geri yüklemenin de çalıştığını söyleyebilir miyiz?
- **SD04:** Üç ONUS inward öğesi initial posting aşamasında takılmış. Kaynak vakada nasıl bir neden bulunmuş, kalan öğe için ne önerilmiş ve bu işlemin gerçekten tamamlandığı doğrulanmış mı?
- **SD05:** Arayüzden kullanıcı rolü veya hesap bitiş tarihi değiştirilirken object is locked or not exists hatası geliyor; sorun yeni kullanıcılarda da var. Kaynakta hangi geçici yaklaşım uygulanmış, UAT ve production için kim neyi doğrulamış?
- **SD06:** Yükseltmeden sonra bazı öğelerin tarama tarihi sistem tarihiyle uyuşmuyor. Benzer ticketta son olarak hangi önlem uygulanmış? Bu, tarihlerin düzeldiğinin kanıtı mı?
- **SD07:** Daha önce iade edilen 12 öğeyi yeniden sunarken aynı alanlara sahip kayıt zaten var hatası alıyoruz; yerel repository temizliği de işe yaramıyor. Benzer vakadaki son denemede ne doğrulanmış? Bunu 12 öğenin tamamı için başarı sayabilir miyiz?
- **SD08:** Servis veya kuyruk takıldığında yüzlerce işlemi elle kontrol etmek yerine e-posta uyarısı almak istiyoruz. Benzer ticketta nasıl bir izleme yaklaşımı önerilmiş ve bu sistemin kurulduğu doğrulanmış mı?
- **SD09:** Entegrasyon sunucusunda gelen dosyalar içeri alınmıyor. Süreç listesinde aynı Tomcat'in iki kopyası görünüyor; biri root, diğeri başka bir kullanıcıyla çalışıyor. Benzer vakada ne yapılmış, dosyaları elle yeniden yüklemek gerekmiş mi ve sonucu kim bildirmiş?
- **SD10:** Uygulama sunucusunda Tomcat'in sunduğu SSL sertifikasının süresi dolmuş, kullanıcılar sertifika uyarısı alıyor. Benzer kayıtta sertifika nasıl yenilenmiş? Önümüzdeki yük dengeleyicide de bir şey yapmamız gerekir mi?

**Windows Server**
- **WS01:** Bir kullanıcının grup üyeliğini değiştirdim ama başka sitedeki etki alanı denetleyicisinde değişiklik görünmüyor. Ormandaki bütün DC'lerin çoğaltma durumunu tek seferde nasıl dökebilirim ve sonuçta nelere bakmalıyım?
- **WS02:** Yeni kurduğum üye sunucuyu etki alanına katmaya çalışırken etki alanı denetleyicisinin DNS adının çözülemediğini söyleyen bir hata alıyorum. Sunucunun bir DC bulup bulamadığını nasıl sınarım ve ayrıntılı kayda nereden bakarım?
- **WS03:** IIS'te yeni yayınladığım siteye kök adresten girince 403.14 Forbidden hatası çıkıyor. Klasör içeriğinin listelenmesini istemiyorum; IIS'te neyi ayarlamalıyım?
- **WS04:** Bir servis hesabı gün içinde defalarca kilitleniyor. Kilitlenme olaylarını birden fazla etki alanı denetleyicisinin güvenlik günlüğünde tek seferde aramak için hangi aracı nasıl kullanabilirim?
- **WS05:** IIS sunucusunun System olay günlüğünde, bir uygulama havuzuna hizmet veren işlemin kapanırken süre sınırını aştığını söyleyen WAS uyarıları görüyorum. Bu ne anlama geliyor, nasıl incelemeliyim?

**Oracle DB optimizasyon**
- **OR01:** Üretimde çalıştırmadan bir SELECT sorgusu için Oracle'ın seçeceği yürütme planını görmek istiyorum. Planı hangi komutlarla üretip okunabilir biçimde gösteririm; bu plan gerçek çalışmayla aynı mıdır?
- **OR02:** WHERE koşulundaki sütunda indeks olmasına rağmen sorgunun planında TABLE ACCESS FULL görüyorum. Optimizer indeksi neden kullanmamış olabilir, bunu nasıl kontrol ederim?
- **OR03:** Büyük bir toplu veri yüklemesinden sonra bir tablodaki sorgular yavaşladı. Tablonun optimizer istatistiklerinin bayatlayıp bayatlamadığını nasıl anlarım ve nasıl güncellerim?
- **OR04:** Yazdığım sorguda IN içinde bir alt sorgu var ama planda bir join görüyorum; ayrıca kullandığım view'ın ana sorguyla birleştirildiğini fark ettim. Oracle sorgumu neden değiştiriyor, bu bir sorun mu?
- **OR05:** Uzun süren bir rapor sorgusunun zamanının hangi plan adımında harcandığını sorgu çalışırken görmek istiyorum. Oracle'da bunu nasıl izlerim, lisans açısından dikkat etmem gereken bir şey var mı?

**Kaynak dışı**
- **NS01:** Windows Server'da DHCP failover kurup iki sunucu arasında IP dağıtımını yedeklemek için hangi PowerShell komutlarını çalıştırmalıyım?
- **NS02:** Oracle Data Guard'da birincil veritabanı kapanınca standby veritabanını devreye almak için hangi komutları kullanmalıyım?
- **NS03:** WSUS sunucusunda bazı istemciler hiç durum raporu göndermiyor. İstemci tarafında hangi komutlarla algılamayı zorlayıp WSUS'a yeniden rapor vermesini sağlarım?
