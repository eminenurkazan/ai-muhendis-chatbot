# Test Raporu: Akıllı Servis Masası ve Sistem Uzmanı Chatbot

**Proje:** PRJIC20260201 · **Test tarihi:** 26 Kasım 2026 · **Soru seti:** V3 (23 soru)

Bu rapor, proje isterlerindeki tamamlanma kriterini karşılamak için hazırlanmıştır: *en az 10 servis masası senaryosu, 5 Windows Server sorunu ve 5 Oracle DB optimizasyon sorusu ile yapılan testlerin sonuçları.* Bu kapsama ek olarak, bilgi tabanında karşılığı olmayan 3 soruyla sistemin yanıt uydurmadığı sınanmıştır.

## 1. Özet

| Grup | Soru | Beklenen kaynak 1. sırada | Beklenen kaynak yanıtta kullanıldı | Elle inceleme: uygun / kısmen / uygunsuz | Ort. süre |
|---|---|---|---|---|---|
| Servis masası | 10 | 10/10 | 10/10 | 9 / 1 / 0 | 6,7 sn |
| Windows Server | 5 | 5/5 | 5/5 | 5 / 0 / 0 | 10,2 sn |
| Oracle DB optimizasyon | 5 | 5/5 | 5/5 | 5 / 0 / 0 | 10,8 sn |
| Kaynak dışı (olumsuz test) | 3 | — | Doğru ret: 3/3 | 3 / 0 / 0 | 5,3 sn |
| **Toplam** | **23** | **20/20** | **20/20** | **22 / 1 / 0** | **8,2 sn** |

- 23 isteğin hepsi hatasız tamamlandı: zaman aşımı ve yeniden deneme olmadı.
- 23 yanıtın hepsinde kullanılan kaynak kimlikleri arama adaylarının içindeydi; uydurma kaynak kimliği yoktu.
- Hiçbir yanıtta sorunun "iddia edilmemesi gerekenler" listesindeki bir ifade görülmedi.
- "Kısmen uygun" bulunan tek yanıt SD03'tür. Kaynakla çelişmiyor, ancak kayıttaki bir öneriyi yapılan işlemle birleştiriyor (bkz. Bölüm 5).
- **Tekrarlı ölçüm:** Set aynı sistemle iki kez daha çalıştırıldı (toplam 3 çalıştırma, 69 yanıt; bkz. Bölüm 4.1). Otomatik ölçümler üç çalıştırmada da birebir aynı çıktı: arama sonuçları ve kullanılan kaynaklar değişmedi. Elle incelemede çalıştırmalar 22/1/0, 23/0/0 ve 22/1/0 sonuç verdi. Kısmen uygun yanıt iki çalıştırmada da SD03'tü. Ortalama süre 8,2 / 9,4 / 9,2 saniye oldu; gecikmenin tamamı model aşamasından geliyor.
- **Çok turlu sohbet (isterdeki "önceki mesajları hatırlama"):** 5 senaryo, 12 tur (bkz. Bölüm 4.2). Bağlama dayanan 7 takip turunun 7'sinde bot önceki mesajı doğru yorumladı: "evet", "bu çözüm", "bu komut", "bunu" ve konu değişimi. 12 yanıtın 12'si kaynağa bağlıydı. Bir turda arama beklenen rehberi ilk 3'e getiremedi (5. sıra); bot bu durumda yanıt uydurmadı.

> **Düzeltme (26 Kasım 2026):** Raporun ilk sürümünde SD06 ve SD07 de "kısmen uygun" sayılmıştı. Gerekçe, "geçici çözüm" nitelendirmesinin kaynakta olmamasıydı. Bu yanlıştı. İnceleme yalnızca chunk metnine bakmıştı. Model ise kaydın bütün alanlarını alır ve iki kaydın `solution_scope` alanı `workaround` değerindedir. Prompt da workaround'u "geçici iyileştirme" olarak sunmayı ister. Bu iki yanıt uygun olarak düzeltildi. Toplam sonuç 20/3/0'dan 22/1/0'a değişti.

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
| Çalıştırmalar | 26.11.2026 (+03:00): 1) 13:21:41–13:24:51 · 2) 14:44:52–14:48:33 · 3) 14:48:35–14:52:11. Üçünde de aynı kod, prompt ve bilgi tabanı kullanıldı. |

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
2. Modele bağlam olarak verilen kayıt alanlarının tamamı: problem, çözüm, sonuç, `resolution_confirmed`, `solution_scope`, `limitations` ve ortam/ön koşul gibi metadata alanları.

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
| SD06 | service_desk | 1004444.0 | 1 | 5,7 | Uygun (kapsam kısmi) | "Geçici önlem" nitelendirmesi kaydın `workaround` kapsamına dayanıyor |
| SD07 | service_desk | 1010324.0 | 1 | 7,0 | Uygun (kapsam kısmi) | Tek öğe teyidi 12 öğeye genellenmedi |
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

Bu tablo 1. çalıştırmanın sonuçlarıdır.

### 4.1 Tekrarlı ölçüm (3 çalıştırma)

Yanıtların çalıştırmadan çalıştırmaya ne kadar değiştiğini görmek için set, kodda, prompt'ta veya bilgi tabanında değişiklik yapılmadan iki kez daha çalıştırıldı.

| Ölçüm | Çalıştırma 1 | Çalıştırma 2 | Çalıştırma 3 |
|---|---|---|---|
| Tamamlanan / hata | 23 / 0 | 23 / 0 | 23 / 0 |
| Beklenen kaynak 1. sırada | 20/20 | 20/20 | 20/20 |
| Beklenen kaynak kullanıldı | 20/20 | 20/20 | 20/20 |
| Kaynak dışı doğru ret | 3/3 | 3/3 | 3/3 |
| Uydurma kaynak kimliği | 0 | 0 | 0 |
| Elle inceleme (uygun / kısmen / uygunsuz) | 22 / 1 / 0 | 23 / 0 / 0 | 22 / 1 / 0 |
| Kısmen uygun soru | SD03 | — | SD03 |
| Ortalama / en uzun süre | 8,2 / 13,8 sn | 9,4 / 16,1 sn | 9,2 / 14,9 sn |

- **Arama tamamen kararlı.** 23 sorunun her birinde üç çalıştırmada da aynı 3 aday aynı sırada geldi, model aynı kaynakları kullandı. OR02'de iki kaynak (erişim yolları + istatistik) üçünde de birlikte kullanıldı.
- **Yanıt metni değişiyor, içerik değişmiyor.** Yanıtların uzunluğu ve cümleleri farklı, ama ana olgular ve kaynak sınırları üç çalıştırmada da korundu. 69 yanıtın hiçbirinde "iddia edilmemesi gerekenler" listesindeki bir ifade görülmedi.
- **SD03 aralıklı bir zayıflık.** Öneri ile yapılan işlemin birleştirilmesi 3 çalıştırmanın 2'sinde görüldü; 2. çalıştırmada yanıt "HQ DB sunucusuna script ve job" bilgisini doğru verdi. Tutarlı ama aralıklı bir sorun olarak izlenmeli (bkz. Bölüm 9).
- **Eksik ayrıntılar da aralıklı.** WS04'te aracın ayrıca indirilmesi gerektiği üç çalıştırmanın hiçbirinde söylenmedi. Olay kimliklerinin eski sürüm uyarısı 3. çalıştırmada yoktu. OR03'teki otomatik istatistik görevi 2. ve 3. çalıştırmada yanıtta yer aldı.
- **Küçük üslup notları:** NS02'nin iki yanıtı, getirilen ilgisiz kayıtların konusunu (yedekleme, recovery catalog) kısaca anıyor. Prompt ilgisiz kayıtları anlatmamayı ister, ama bu kayıtlar dayanak yapılmadı. NS01'in bir yanıtında DHCP failover'ı tanımlayan, sorunun yeniden ifadesi niteliğinde kaynak dışı bir cümle var.

**Süre dağılımı (69 istek):**

| Grup | Ortalama | En kısa | En uzun |
|---|---|---|---|
| Servis masası | 7,5 sn | 5,7 sn | 10,1 sn |
| Windows Server | 10,3 sn | 8,3 sn | 12,4 sn |
| Oracle DB | 11,2 sn | 8,7 sn | 15,7 sn |
| Kaynak dışı | 7,9 sn | 4,4 sn | 16,1 sn |
| **Toplam** | **8,9 sn** (medyan 8,7) | 4,4 sn | 16,1 sn |

Uygulama günlüğündeki aşama süreleri (`app_logs`, `chat.ask_completed`, aynı gün 69 olay) gecikmenin kaynağını gösteriyor:

| Aşama | Medyan | En uzun |
|---|---|---|
| Embedding | 0,29 sn | 1,1 sn |
| Arama | 0,06 sn | 0,17 sn |
| Model | 8,1 sn | 15,0 sn |

Süredeki dalgalanmanın tamamı bulut model aşamasındadır. Windows/Oracle yanıtları daha uzun ve kod bloklu olduğu için daha uzun sürüyor. 15 saniyeyi aşan iki istekte (NS01 ve NS03) model aşaması tek başına 13,9–15,0 saniye sürdü. Arama ve veritabanı süreleri ihmal edilebilir düzeyde.

### 4.2 Çok turlu sohbet testi

İsterlerdeki *"Bot, önceki mesajları hatırlayarak konuşma bağlamını sürdürebilmelidir"* maddesi için 5 senaryo hazırlandı: [evaluation/evaluation_conversations_v1.json](../evaluation/evaluation_conversations_v1.json). Toplam 12 tur var. Senaryolar ve beklentiler çalıştırmadan önce sabitlendi. Her senaryo tek bir sohbette, arayüzle aynı akışla çalıştırıldı ([evaluate_conversations.py](../evaluate_conversations.py)). İstemci geçmiş göndermez; API sohbetin son 3 soru–yanıt çiftini MSSQL'den okur. Çalıştırma 26 Kasım 2026 15:19'da, aynı kod, prompt ve bilgi tabanıyla yapıldı.

| Senaryo | Mod | Ne sınanıyor | Sonuç |
|---|---|---|---|
| MT01 | service_desk | 3 tur: sorun anlatılır → "Evet, gizli pencerede açılıyor" → "Bu çözümün işe yaradığını müşteri doğrulamış mı?" | Kısa yanıt ve "bu çözüm" doğru bağlandı; doğrulamanın bildiren kullanıcıya ait olduğu doğru |
| MT02 | service_desk | 2 tur: Tomcat vakası → "Peki sonucu kim bildirmiş?" | Konu belirtilmeyen soru önceki vakaya bağlandı; müşteri teyidi olmadığı korundu |
| MT03 | windows_server | 3 tur: repadmin raporu → "Bu komut hatayı düzeltir mi?" → "Hangi yetkiyle çalıştırmalıyım?" | "Bu komut" ve "bunu" önceki komuta bağlandı; onarım komutu uydurulmadı; yetki raporlama adımına özgü verildi |
| MT04 | oracle_db | 2 tur: istatistik sorusu → "Başka bir konu: …plan adımında zaman" | Konu değişimi doğru izlendi. **1. turda arama beklenen rehberi kaçırdı** (aşağıda). |
| MT05 | windows_server | 2 tur: IIS 403.14 → WSUS sorusu (kaynak dışı) | Önceki konunun rehberi dayanak yapılmadı; kaynak yok dedi, komut vermedi |

| Ölçüm | Sonuç |
|---|---|
| Tamamlanan tur | 12/12 (hata yok) |
| Bağlama dayanan takip turlarında doğru yorum | 7/7 |
| Beklenen kaynak kullanıldı | 10/11 (MT04 tur 1 hariç) |
| Kaynak dışı turda doğru ret | 1/1 |
| Uydurma kaynak kimliği / yasaklı iddia | 0 / 0 |
| Kaynağa bağlılık (elle inceleme) | 12/12 uygun |
| Ortalama süre | 7,1 sn (4,8–11,8) |

**Bulgu 1: Kısa soruda arama kaçırması (MT04 tur 1).** "İstatistiklerin bayat olup olmadığını nasıl anlarım?" sorusunda beklenen rehber 5. sıradaydı. Benzerlik skorları: rehber 0,583, birinci aday 0,620. Model yalnız ilk 3 adayı gördüğü için rehber dışarıda kaldı. Aynı rehber, tekli testteki daha ayrıntılı OR03 sorusunda ("optimizer istatistikleri… nasıl güncellerim") 0,679 skorla birinci sıradaydı. Model bu durumda doğru davrandı: `STALE_STATS` gibi komutları uydurmadı, "bu aramada prosedür yok" dedi ve sürüm sordu. Ancak kullanıcı yardım alamadı. Adaylar arasındaki skor farkları küçük (0,58–0,62); kısa ve anahtar kelimesi az sorularda doğru kaynak ilk 3'ün dışında kalabiliyor. Bu, aday sınırının bilinen ve kabul edilmiş bir sonucudur (bkz. Bölüm 9, madde 5).

**Bulgu 2: Konu değişiminde önceki konunun kaynağı aramaya giriyor (MT05 tur 2, MT04 tur 2).** Arama metni, kısa takip sorularını anlamlandırmak için son soru–yanıt çiftini de içeriyor. Bu yüzden WSUS sorusunda IIS 403.14 rehberi 1. sırada, MT04'ün 2. turunda istatistik rehberi 2. sırada geldi. Her iki durumda da model önceki konunun kaynağını yeni soruya dayanak yapmadı. Yani koruma prompt düzeyinde çalışıyor, ama arama tarafında bir aday yerini boşa harcıyor.

## 5. Bulgular

### 5.1 Kısmen uygun bulunan yanıt

- **SD03 (otomatik yedekleme):** Kayıtta "Windows üzerinden zamanlama" bir **öneri** olarak, "HQ DB sunucusuna script ve günlük job eklenmesi" ise **yapılan işlem** olarak ayrı yazılıdır. Yanıt bu ikisini birleştirip "Windows üzerinde job eklendiği bildirilmiş" diyor. Haftalık tam yedeğin ve geri yüklemenin doğrulanmadığını ise doğru aktarıyor.
Bu, V2'de görülen "kaynakta ayrı duran bilgileri birleştirme" sorununun hafif bir türüdür. Kullanıcıyı yanlış yönlendirecek bir eylem önerisi içermiyor. Tek bir örnek olduğu için prompt değişikliği gerektiren bir örüntü olarak değerlendirilmedi.

SD06 ve SD07 ilk sürümde bu bölümdeydi; neden çıkarıldıkları Bölüm 1'deki düzeltme notunda yazıyor.

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
| Elle inceleme | 7 uygun, 1 kısmen (V2Q02) | 7 uygun, 1 kısmen (SD03) |

- Bilgi tabanı 191 kayıttan 458'e büyüdüğü ve aynı havuzda Windows/Oracle kayıtları bulunduğu halde servis masası sorularında arama doğruluğu korundu.
- V2Q02'deki ek ihtimal sorunu bu çalıştırmada görülmedi.
- Her iki çalıştırmada da 8 sorudan 7'si uygun, 1'i kısmen uygun bulundu, ama kısmen uygun olan soru farklı: V2'de V2Q02, V3'te SD03. Model çıktısı her çalıştırmada değişebilir ve iki değerlendirmeyi farklı kişiler yaptı. Bu nedenle tek bir çalıştırmayla soru bazında kalıcı bir iyileşme ya da gerileme olduğu söylenemez.

## 7. Sınırlılıklar

1. **Az sayıda tekrar:** Her soru 3 kez soruldu. Bu, arama ve kaynak kullanımının kararlı olduğunu, yanıt içeriğinin ise küçük farklarla değiştiğini göstermeye yeter. Ancak 3 tekrar, soru bazında güvenilir bir başarı oranı hesaplamaya yetmez.
2. **İyimser kaynak seçimi:** Windows ve Oracle soruları, isterlerdeki konular için önceden bilgi tabanına eklenmiş resmî rehberlere dayanır. Rehberler test konularına göre seçildiği için bu gruplardaki 5/5 arama başarısı iyimserdir. Rehber kapsamı dışındaki Windows/Oracle sorularında, örneğin 255 topluluk kaydına dayanan sorularda, başarı ayrıca ölçülmemiştir.
3. **Komutlar gerçek ortamda çalıştırılmadı:** Yanıtlardaki repadmin, nltest, EventCombMT, EXPLAIN PLAN, DBMS_STATS vb. komutlar gerçek Active Directory, IIS veya Oracle ortamında denenmedi. Değerlendirme, yanıtın kaynağa bağlılığını ölçer; komutun hedef ortamda başarılı olacağını kanıtlamaz.
4. **Kaynak doğruluğu:** Değerlendirme kaynağı doğru kabul eder. Ticket kayıtlarındaki çözümlerin ya da rehber özetlerinin kendisi bu testte bağımsız olarak doğrulanmadı.
5. **Elle inceleme tek kişiliktir:** İncelemeyi Claude yaptı; ikinci bir insan incelemesi yapılmadı.
6. **Süre ölçümü:** `elapsed_ms` API içi süredir. Tarayıcı, ağ ve MSSQL'e kayıt süresini içermez. Bulut model süresi çalıştırmalar arasında dalgalanır; 12 Kasım'da tek bir zaman aşımı gözlenmişti, bu çalıştırmada gözlenmedi.
7. **Kapsam dışı yetenekler:** Yanıt puanlama, admin raporu ve kullanıcı yönetimi bu testin konusu değildir; bu özellikler aşağıdaki yazılım testleriyle sınanmıştır. Konuşma bağlamının sürdürülmesi 5 senaryo ve 12 turla sınandı (Bölüm 4.2). Bu az sayıdadır ve en çok 3 turluk sohbetleri kapsar; daha uzun sohbetlerde yalnız son 3 soru–yanıt çifti bağlam olarak kullanılır.

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

1. **SD03'teki birleştirme:** Sorun 3 çalıştırmanın 2'sinde görüldü ve başka hiçbir soruda görülmedi. Prompt'a genel bir kural eklemek, prompt sürümünü değiştirip bütün seti yeniden doğrulamayı gerektirir. Bunun yerine kaynak kaydın (1006956.0) "öneri" ve "yapılan işlem" cümleleri daha net ayrılabilir; örneğin "Windows üzerinden zamanlama" önerisi ayrı bir satıra alınabilir. Ardından yalnızca SD03 tekrar ölçülür.
2. **Süre izleme:** Yanıt süresinin tamamı model aşamasında olduğu için, kullanıcıya 15 saniyeyi aşan bekleme durumlarında ilerleme göstergesi korunmalıdır. `app_logs` aşama süreleri bu izleme için yeterlidir.
3. **Rehber dışı sorular:** Windows ve Oracle için topluluk kayıtlarına dayanan, rehberlerden bağımsız 5'er ek soru hazırlanmalı. Böylece Bölüm 7'deki iyimserlik ölçülebilir.
4. **Eksik içerik:** EventCombMT rehber kaydına "araç ayrıca indirilir" bilgisi daha belirgin biçimde, örneğin çözüm adımlarının başına, eklenebilir.
5. **Aday sınırı bilinçli olarak 3'te tutuldu (Bölüm 4.2, Bulgu 1):** Sınırı 5'e çıkarmak sorunu çözmez, yalnızca kaydırır; hangi sayı seçilirse seçilsin bazı sorularda ilgili kayıt sınırın hemen dışında kalabilir. Daha fazla aday ise modele giden bağlamı, yanıt süresini ve model kullanımını artırır, ilgisiz kayıtların yanıta karışma riskini de yükseltir. Kaynakların verimli kullanımı için ilk 3 aday korunmuştur. Sistem bu durumda güvenli davranır: kaynak bulamadığını söyler ve kullanıcıdan ayrıntı ister; kullanıcı soruyu daha ayrıntılı sorduğunda (OR03 örneği) doğru kaynak bulunur.
6. **Konu değişiminde arama metni (Bölüm 4.2, Bulgu 2):** Geçmiş, arama metnine yalnız kısa takip sorularında eklenebilir; örneğin birkaç kelimelik veya "bu/bunu/o" gibi gönderme içeren sorularda. Uzun ve bağımsız bir soruda yalnız güncel soru aranır.

## 10. Tekrar çalıştırma

API açık ve hesap erişimleri hazırken (bulut çağrısı yapar, 23 model isteği):

```powershell
Set-Location -LiteralPath "D:\ai-muhendis-chatbot"
$env:APP_ACCESS_TOKEN = "<girişten alınan token>"
.\.venv\Scripts\python.exe evaluate_api.py --questions evaluation\evaluation_questions_v3.json --output-dir outputs_local\evaluation_set_v3\runs
```

Çok turlu senaryolar (12 model isteği):

```powershell
.\.venv\Scripts\python.exe evaluate_conversations.py --output-dir outputs_local\evaluation_conversations_v1
```

Bu çalıştırmada kullanılan `evaluate_api.py` sürümünün SHA-256 değeri sonuç dosyasında kayıtlıdır (`66bcc78a…07bc`). Depodaki güncel sürüm, sonradan yapılan klasör düzenlemesi (`4d88e70`) nedeniyle yalnızca varsayılan dosya yollarında farklıdır.

## 11. Kanıt dosyaları

Aşağıdaki dosyalar yerelde Git dışında tutulur (`outputs_local/`):

| Dosya | İçerik |
|---|---|
| `outputs_local/evaluation_set_v3/runs/evaluation_results_v3_20261126_132141_860039.json` | 23 sorunun ham sonucu: yanıt metni, kaynak kimlikleri, kaynak görüntüleri, süreler |
| `…_860039.meta.json` | Çalıştırma bilgileri: başlangıç/bitiş, soru ve araç hash'leri, kategori özetleri |
| `…_860039_manual_review.json` | Soru bazında elle inceleme kararı, gerekçe ve bulunan sorunlar |
| `…_20261126_144452_617953*.json`, `…_20261126_144835_222767*.json` | 2. ve 3. çalıştırmanın ham sonucu, meta bilgisi ve elle incelemesi |
| `outputs_local/evaluation_conversations_v1/conversation_results_evaluation_conversations_v1_20261126_151924*.json` | Çok turlu senaryoların ham sonucu, meta bilgisi ve elle incelemesi |

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
