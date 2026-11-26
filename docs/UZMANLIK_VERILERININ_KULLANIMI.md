# Uzmanlık kaynaklarının saklanması ve aranması

## Son 150 kayıt — resmî belge karşılaştırması tamamlandı

Son aktarılmış 150 kaydın kullanılan dar açıklamaları kamuya açık üretici belgeleriyle karşılaştırıldı. 137 kayıt `partially_supported_scoped`, 13 kayıt `insufficient_support` durumundadır. İkinci grup resmî olarak doğrulanmış sayılmaz; kullanıcının önceki açık kaynak-incelemesi aktarım onayıyla, yalnız atıflı vaka/açıklama olarak kalır. Bunlarda genel işlem/komut tavsiyesi verilmez.

150 kayıt/chunk yeniden embedding ile güncellendi, özgün kaynaklar ve diğer 296 kayıt korundu. Toplam 446 kayıt değişmedi. Resmî kaynak karşılaştırması bütün cevabın doğruluğu veya ürün ortamında bağımsız başarı testi değildir. Rapor/makbuz: `outputs_local/expertise_official_comparison_150_20261106`.

Aşağıdaki kaynak-incelemesi aktarımı bölümü bu karşılaştırmadan önceki tarihsel durumu açıklar.

## Önceki aktarım durumu — 314 uzmanlık adayının incelemesi tamamlandı

Bilgi tabanı 446 kayıt/chunk içerir: 191 Mendeley ticketı, 156 Windows Server ve 99 Oracle soru–cevabı. 314 uzmanlık adayının tamamı kaynak incelemesinden geçti; 255 kullanımda, 59 dışarıda. İncelenmemiş uzmanlık adayı yoktur.

Son aktarımda 150 kaynak incelemeli kayıt kullanıcının açık onayıyla eklendi: 113 ön değerlendirmede uygun, 37 Sol incelemesinde dar kapsamla uygun bulunmuş kayıt. Bunların `official_verification_status` değeri `not_checked`, `official_sources` listesi boştur. Resmî teknik doğrulama yapılmış gibi işaretlenmediler. Önceki 296 kaydın içerik hash'leri korundu. Makbuz: `outputs_local/expertise_activation_20261106_source_review_161021/import_receipt.json`.

`database.import_expertise --allow-unverified` yalnız açık onay alanı bulunan kaynak incelemeli dosyalara izin verir; bayrak olmadan resmî kontrolü eksik dosyaları reddeder. Kaynak prosedür olarak sınıflanmışsa yalnız açıklama özeti indekslenir; özgün sınıf `source_review_scope` içinde tutulur. Tam cevap ve kaynak komutlar onaylanmış işlem tarifi sayılmaz.

Son 150 kayıtta 1024 boyutlu embedding, approved/ready durumu ve kendi vektörüyle ilk üçte bulunma kontrol edildi. Bu, doğal dil sorularıyla yanıt kalitesi değerlendirmesi değildir. Aktarım aracı için mevcut altı entegrasyon sınırı testi ve açık onay bayrağı kontrolleri geçti.

## Önceki durum — üçüncü parti tamamlandı

Bilgi tabanı 292 kayıt/chunk içerir: 191 Mendeley ticketı + 65 Windows Server + 36 Oracle soru–cevabı. Son 90 adayın 68’i sınırlı kapsamla uygulamada, 22’si dışarıda. Resmî kontrol bekleyen son 63 adayın 57’si kapsamı daraltılarak aktarıldı, 6’sına indeks onayı verilmedi. Bu partide Sol veya belge kontrolü bekleyen kayıt yok.

Uzmanlık adaylarından toplam 130’u incelendi: 101 kullanımda, 29 dışarıda; diğer 184 henüz incelenmedi. Güncel birleşik kararlar: `outputs_local/expertise_qa_official_review_20261106_batch03/reviewed_results_final.json`. Son aktarım makbuzu: `outputs_local/expertise_activation_20261106_batch03_verified02/import_receipt.json`. Eski aktarım bölümleri tarihsel ölçümleri korur.

6 Kasım 2026 ikinci aktarımı sonrasında yerel bilgi tabanı 224 kayıt/chunk içerir: 191 Mendeley ticketı, 22 Windows Server ve 11 Oracle soru–cevabı. Toplam 40 uzmanlık adayı incelendi: 33 kayıt sınırlı açıklama/teşhis kapsamıyla eklendi, 7 kayıt dışarıda bırakıldı. Henüz incelenmemiş 274 aday vardır. Resmî belge karşılaştırması bağımsız ürün ortamı testi değildir.

## Ortak veritabanı, kaydı belli kaynaklar

Aynı PostgreSQL/pgvector tabloları kullanılır; ayrı sunucu veya model gerekmez:

| Katman | Tutulan bilgi |
|---|---|
| knowledge_sources | Mendeley, Server Fault ve Database Administrators kaynak kimlikleri ve sürümü |
| knowledge_records | Kaynak kimliği, ticket/qa türü, general_it/windows_server/oracle_db alanı, incelenmiş problem/cevap ve sınırlar |
| knowledge_records.raw_text | QA’nın özgün soru-cevap ve atıf bilgileri; model bağlamına alınmaz |
| knowledge_records.metadata | Soru/cevap bağlantıları, ayrı yazar/lisanslar, kanıt, resmî doğrulama notları ve dönüşüm açıklaması |
| knowledge_chunks | İncelenmiş kısa metin ve mevcut BGE-M3 modelinin 1024 boyutlu embedding’i |

Örnek kimlikler: Mendeley için `1007444.0`, Server Fault için `serverfault:q893315:a893804`, Oracle sorusu için `dba:q278547:a278555`. Bunlar birbirinin yerine geçirilmez. QA için Mendeley yorum numarası üretilmez; `source_comment_seq=NULL` ve `resolution_confirmed=NULL` korunur. Kabul edilmiş cevap başarı garantisi sayılmaz.

## Arama kapsamı

| expertise_mode | Aranabilen alanlar | Bugünkü kayıt sayısı |
|---|---|---:|
| service_desk (varsayılan) | general_it + windows_server + oracle_db | 446 |
| windows_server | general_it + windows_server | 347 |
| oracle_db | general_it + oracle_db | 290 |

191 genel ticket uzmanlık modlarında da aranabilir; bazıları Windows/Oracle sorusuna ilgili vaka olabilir. Windows ve Oracle QA’ları karşı modda aranmaz. Soru metnine bakarak otomatik mod seçimi yapılmaz; istemci `expertise_mode` gönderir. Alan uygunluğu tek başına konu ilgisini kanıtlamaz; model ilk üç adayın soruyla ilişkisini ayrıca değerlendirmelidir.

SQL, onaylı/ready ve aynı embedding modeliyle oluşturulmuş, içerik hash’i eşleşen chunk’ları seçer. Alan filtresi sıralamadan önce uygulanır; sonra cosine benzerliğiyle ilk üç sonuç döner. QA kayıtlarına zorunlu öncelik verilmez. Benzerlik doğruluk yüzdesi değildir.

## İlk aktarımda neler eklendi?

IIS yönlendirme yaklaşımı, Windows olay loglarını sorgulama, OpenSSH hata/güncelleme geçmişi, Robocopy/dedup bozulma riski, CLOB/VARCHAR2 koşullu seçimi, Oracle PDB/local user ayrımı ve RMAN backupset açıklaması.

Yedi kaydın hepsi açıklama veya teşhis kapsamındadır. Ham cevapların XML/SQL/ACL blokları doğrudan indekslenmedi; resmî belge notu topluluk cevabından ayrı etiketlendi. Özgün soru/cevaplar değiştirilmeden yerelde ve raw_text içinde korunur. Kaynakta başarı anlatımı varsa yazara ve ortama atfedilir; null doğrulama alanı true yapılmaz.

## API kaynak alanları

`POST /ask` artık `used_source_ids`, `retrieved_source_ids` ve yalnız kullanılan kayıtların atıflarını içeren `sources` alanını döndürür. `sources` içinde QA kayıtları için soru/cevap URL’leri, yazarlar, ayrı lisanslar ve resmî kontrol bağlantıları bulunur. Atıfları model üretmez; kullanılan kimliklerle eşleşen veritabanı kaydından uygulama ekler.

Eski istemciler için `used_ticket_ids` ve `retrieved_ticket_ids` korunmuştur; bu eski adlara rağmen QA kimlikleri de içerebilirler. Yeni istemciler genel `*_source_ids` alanlarını kullanmalıdır. Model çıktı JSON biçimi bu uyumluluk için korunmuştur. Prompt sürümü `2026-11-06-v3`, API sürümü `0.3.0`.

Örnek istek:

```json
{"question":"Oracle 18c XE’de local user oluştururken PDB bağlantısında neye dikkat etmeliyim?","expertise_mode":"oracle_db"}
```

## Yerel hazırlama ve aktarım

`database.import_expertise` mevcut korumalı Cloudflare erişimini kullanır. `check`, `embed`, `import`, `verify` eylemleri vardır. Her eylem açık bir `--records` yolu ister. Önceki ticket CSV aktarım araçları değiştirilmemiştir.

Bu partinin aktarım dosyası: `outputs_local/expertise_activation_20261106/approved_import.json`. Önbellek aynı yerde `approved_import.embeddings.json` olarak saklanır. Yeniden aktarımda aynı içerik çoğaltılmaz; aynı kimliğe farklı içerik gelirse üzerine yazmak yerine durur. Yedi kayıt tek transaction içinde eklenir; eski ticket satırları ve chunk hash’leri değişirse işlem geri alınır.

Ham indirme: `outputs_local/expertise_qa/20261105T065002_329245Z`.
Güncel 10 kayıt kararı: `outputs_local/expertise_qa_review_trial_20261105/reviewed_results_final.json`.
Aktarım makbuzu ve hedefli API çıktıları: `outputs_local/expertise_activation_20261106`.

Bu yerel veri/embedding dosyaları Git dışında kalır. Temiz klon 224 kaydı kendiliğinden kurmaz. Soru ve cevapların CC BY-SA sürümleri ayrı korunur; daha sonra bir veri paketi yayımlanırken bu atıf/dönüşüm bilgileri de taşınmalıdır.

## İlk aktarımda yapılan kontroller

- Mevcut 9 RAG/prompt testi ve yeni 6 entegrasyon sınırı testi: 15/15 geçti.
- 7 yeni kayıt approved/ready, her birinde tek 1024 boyutlu chunk; yazar/lisans ve null alanları doğrulandı.
- 191 eski ticket ve chunk’larının içerikleri/satır hash’leri aynı kaldı.
- İkinci aktarım: eklenen 0, zaten bulunan 7.
- Üç elenen kimlik veritabanına alınmadı.
- Her kaydın kendi embedding’iyle ilk üçte bulunması kontrol edildi; bu doğal dil başarımı değildir.
- Karşı alanın vektörüyle yapılan aramada SQL alan filtresinin çalıştığı doğrulandı.
- Yeni API üzerinden IIS, Oracle PDB ve mevcut Mendeley UAT soruları çalıştırıldı. Üçünde de beklenen kaynak ilk üçte ve kullanılan kaynaklarda; yeni atıf alanları doğru. Yanıtlar elle kaynağa bağlılık açısından incelendi; bu üç örnekte dışlanan kod veya desteklenmeyen ek çözüm görülmedi.

Tam V1/V2 değerlendirme seti bu değişiklikten sonra yeniden çalıştırılmadı. Önceki 191 kayıtlık değerlendirme sonuçları tarihsel ölçüm olarak geçerlidir.

- windows_iis: 10503 ms; kullanılan kaynak: serverfault:q893315:a893804.
- oracle_pdb: 10661 ms; kullanılan kaynak: dba:q278547:a278555.
- mendeley_uat: 7833 ms; kullanılan kaynak: 1007444.0.


## İkinci aktarım: 26 yeni kayıt

`outputs_local/expertise_qa_review_20261106_all_remaining/reviewed_results_final.json` bu partide incelenen 30 kaydın son kararlarını içerir. Başlangıçtaki yedi belirsiz kayıttan beşi daraltılmış kapsamda uygun, ikisi uygun değil bulundu. Ön değerlendirmede uygun olan 21 kayıt da önemli iddiaları resmî kaynaklarla karşılaştırılarak daraltıldı. Partinin sonucu 26 uygun, 4 uygun değil, 0 karar bekliyor şeklindedir; kalan 274 aday henüz taranmadı.

Yeni 18 Windows Server ve 8 Oracle kaydının tamamı explanation veya diagnostic_approach kapsamındadır. Registry silme, SYSTEM/telnet hack’i, RMAN silme komutları ve kaynak DDL/PLSQL blokları indekslenmedi. Eski Oracle exp/imp taşıma cevabı destek dışı yöntem, diğer Oracle cevap ise özgün metindeki kod sorunları nedeniyle aktarılmadı.

Aktarım dosyası: `outputs_local/expertise_activation_20261106_batch02/approved_import.json`. Embedding önbelleği aynı klasördedir; 26 kayıt için BGE-M3 ile 1024 boyut üretildi. `import_receipt.json` eski 198 kayıt ve chunk’ının tamamının içerik hash’lerinin korunduğunu, yeni kayıtların approved/ready olduğunu ve dört elenen kimliğin veritabanında bulunmadığını gösterir. Her yeni kaydın kendi vektörüyle ilk üçte bulunması hazırlık kontrolüdür.

Önceden belirlenmiş iki doğal dil sorusunda SNI ve RMAN TAG kaynakları ilk sırada bulundu; alan filtreleri korundu. Bu turda tam V1/V2 seti veya yeni API yanıt üretimi çalıştırılmadı. Kaynaklar mevcut arama yolundan veritabanına her sorguda okunur; kod değişikliği gerektirmedi.
