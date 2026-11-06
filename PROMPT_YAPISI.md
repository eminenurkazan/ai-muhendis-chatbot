# Uzmanlık yönergeleri ve kaynak sınırı

Son güncelleme: 6 Kasım 2026 · Güncel prompt sürümü: `2026-11-06-v3`. Uzmanlık modları ilk kez 22 Ekim `2026-10-22-v1` sürümünde eklendi.

Prompt, modele her soru için verilen çalışma yönergesidir. Bu adımda Terra modeli değiştirilmedi veya yeniden eğitilmedi. Aynı modele seçilen alana göre ek yönerge gönderilir. Tanımlanan rolün işe yararlığı, kaynakların kalitesi ve gerçek yanıt testleriyle ayrıca ölçülmelidir.

## API seçimi

`POST /ask` gövdesindeki isteğe bağlı `expertise_mode` alanı şu değerleri kabul eder:

| Değer | Odak |
|---|---|
| `service_desk` | Mevcut genel servis masası yönergesi; alan gönderilmezse bu kullanılır. |
| `windows_server` | Windows Server sürümü, sunucu rolü, ortam, yetki ve değişiklik etkisi. |
| `oracle_db` | Oracle sürümü, ortam ve yetki; SQL/PLSQL, RMAN ve sequence/cache ayrıntılarının kaynakla sınırlandırılması. |

```json
{"question":"Sorunuz", "expertise_mode":"oracle_db"}
```

Yanıt, önceki alanlarına ek olarak `expertise_mode` ve `prompt_version` döndürür. Geçersiz mod HTTP 422 ile reddedilir. Terminal pilotu varsayılan servis masası modunu kullanır.

## Kaynakla çalışma

Üç mod aynı ortak kuralları kullanır: yalnızca ilgili kaynaklara dayan, kaynakta olmayan komut/değer/sürüm üretme, müşteri onayını destek beyanından ayır, geçici çözümü kalıcı çözüm sayma ve kaynak yoksa `insufficient_context=true` döndür.

Güncel havuz 191 Mendeley ticketı ve 33 incelenmiş uzmanlık QA’sı içerir (toplam 224 kayıt). Genel mod bütün havuzu, Windows modu genel + Windows, Oracle modu genel + Oracle alanlarını arar. QA’nın kabul edilmiş cevabı bağımsız başarı teyidi sayılmaz. `official_context`, topluluk cevabından ayrı resmî belge notudur; yalnız incelenmiş kapsam kullanılmalıdır. Bu 33 kayıt bütün Windows Server ve Oracle uzmanlığını kapsamaz; her kayıt yalnız incelenmiş sınırıyla kullanılabilir.

Uygulama yönergeleri Responses API'nin `instructions` alanındadır. Kullanıcı sorusu ve ticket metinleri JSON olarak `input` içinde kalır; yönerge metnine doğrudan eklenmez. Ticket içindeki talimatlar güvenilmeyen veri sayılır. Bu ayrım tek başına prompt saldırılarına karşı tam koruma garantisi değildir; gerçek örneklerle sınanmalıdır.

## Kaynakta olmayan ihtimaller

5 Kasım V2 düzeltmesi bütün uzmanlık modlarının ortak yönergesini güçlendirir. Model, bir sorunun nedenini kaynak açıklamıyorsa kendi teknik bilgisinden bir ihtimal eklememelidir. “Olabilir” gibi ihtiyatlı bir söz kullanılması bunu kaynak destekli hâle getirmez.

Aynı tickettaki ayrı sorunlar da birbirine bağlanmamalıdır. Bir alt sorun için doğrulanan neden veya uygulanan çözüm, kaynak açıkça ilişki kurmadıkça daha sonraki başka bir hataya taşınamaz. Kaynağın kendi ihtimalleri ise ilgili yazar/alt sorun ve belirsizlik korunarak aktarılabilir. Modelden, yanıtını vermeden önce eklediği neden-sonuç ifadelerinin dayanağını kontrol etmesi istenir.

Bu kural genel bir kaynak kullanma kuralıdır; belirli ticket kimliği veya test yanıtı yönergeye eklenmedi. Gerçek yanıt davranışı hedefli API kontrolleriyle ayrıca ölçülür.

## Kodun izlediği yol

`api.py` modu doğrular → `rag_service.py` zinciri çağırır → `rag_chain.py` modu hem arama filtresine hem provider'a taşır → `rag_provider.py` mevcut oturumu kullanır → `rag_ticket_pilotu.request_body()` ortak ve alana özel yönergeyi birleştirir. Yönerge metinleri `rag_prompts.py` dosyasındadır. Kaynak kimlikleri mevcut `parse_answer()` denetiminden geçer.

MSSQL sohbet tablosundaki `expertise_mode` ile API alanı aynı adları kullanır; sohbet geçmişi henüz API'ye bağlanmadığından bu değer otomatik olarak veritabanına yazılmaz.

## Doğrulama durumu

22 Ekim'de üç mevcut RAG testi ve altı yeni prompt testi geçti. Varsayılan yönergenin önceki metinle aynı olduğu ayrıca karşılaştırıldı. Yeni testler modun model çağrısına taşınmasını, ortak kuralların korunmasını, kullanıcı/ticket metninin yönergeden ayrılmasını ve geçersiz modun reddedilmesini bulut çağrısı yapmadan kontrol eder. Bunlar modelin gerçek yanıt kalitesini ölçmez.

Sunucu yeniden başlatıldıktan sonra 22 Ekim'de kullanıcı aşağıdaki iki gerçek API kontrolünü çalıştırıp çıktıları paylaştı. İki yanıtta da seçilen mod ve `prompt_version=2026-10-22-v1` doğrulandı:

| Mod | Soru | Gözlenen sonuç | Süre |
|---|---|---|---|
| `windows_server` | Windows Server'da BitLocker kurtarma anahtarını Active Directory'den nasıl bulurum? | Geçti: ilgili kaynak yok; `insufficient_context=true`, kullanılan kaynak listesi boş. İlk üç aday `1007932.0`, `1006218.0`, `1007210.0`; model bunları dayanak saymadı. | 9873 ms |
| `oracle_db` | Oracle sequence değerleri yavaş döndüğü için büyük işlem grupları gecikiyor. Kaynak kayıtta nasıl bir yaklaşım anlatılıyor ve hangi ayrıntılar eksik? | Geçti: `1010047.0` ilk aday ve kullanılan kaynak; `insufficient_context=false`. Yanıt onaylı ticket özetiyle karşılaştırıldı; SQL/cache değeri uydurulmadı, müşteri doğrulaması yok sınırı korundu. | 11674 ms |

Bu iki seçilmiş kontrol, geniş kapsamlı uzmanlık veya prompt saldırılarına dayanıklılık ölçümü değildir. Olumlu Windows Server kaynağı, farklı Oracle soruları ve kasıtlı talimat saldırılarıyla ayrı değerlendirme gerekir. 9 Ekim'deki 10 soruluk set bu adımda yeniden çalıştırılmadı. API kodu veya yönerge değişince sunucu yeniden başlatılmalı ve yanıtın mod/sürüm alanları kontrol edilmelidir.

### 5 Kasım: kaynak dışı ihtimal için takip düzeltmesi

`2026-11-05-v2` sürümüyle mevcut dokuz RAG/prompt testi geçti. Önceki DNS sorusu iki kez ve UAT teyidi sorusu bir kez gerçek API üzerinden yeniden çalıştırıldı. Üç yanıtta da yeni prompt sürümü ve önceki çalıştırmayla aynı aday kaynaklar doğrulandı. İki DNS tekrarında desteklenmeyen yetki/tablespace ihtimali eklenmedi; UAT kontrolünde reporter/support ayrımı korundu. Bu üç kontrol tam V2 setinin yeniden çalıştırılması değildir.

Ayrıntılar: [Kaynak dışı ihtimal düzeltmesi](PROMPT_YORUM_TASMASI_DUZELTMESI.md).

Resmî yönerge: [OpenAI prompt engineering](https://developers.openai.com/api/docs/guides/prompt-engineering).

## 6 Kasım: soru-cevap kaynak desteği

V3, QA türünü ve null doğrulama bilgisini ayırır; kaynak kimliğinin eksiksiz korunmasını, resmî belge notunun topluluk cevabından ayrılmasını ve kapsam dışı kodun yeniden üretilmemesini ister. Eski kaynak-dışı ihtimal kuralları korunmuştur. 15 yerel test ve üç hedefli canlı kontrolde kaynak türü/atıf ve mod bilgisi doğrulandı. Tam V2 seti tekrar edilmedi. Ayrıntılar: [Uzmanlık verileri](UZMANLIK_VERILERININ_KULLANIMI.md).
