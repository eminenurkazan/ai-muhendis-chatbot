# Kaynak dışı ihtimal ekleme düzeltmesi

Ortak prompt `2026-10-22-v1` sürümünden `2026-11-05-v2` sürümüne güncellendi. Amaç, modelin kaynağın ilişkilendirmediği iki alt sorun arasında olası neden eklemesini azaltmaktır.

## Yapılan değişiklik

- Kaynakta olmayan neden, teşhis veya çözüm ihtimali eklenmemesi açıkça belirtildi. “Olabilir” veya “muhtemelen” demek dayanak gereğini kaldırmaz.
- Aynı ticketın farklı alt sorunlarına ait neden/çözüm bilgisinin, kaynak açıkça bağlamadıkça birbirine taşınmaması istendi.
- Kaynak yazarının zaten belirttiği bir ihtimalin aktarılmasına izin verilir; yazar, alt sorun ve belirsizlik korunur.
- Yanıt öncesi neden-sonuç ifadelerinin kaynakla kontrol edilmesi istendi.

Kural ortak yönergede olduğu için üç uzmanlık moduna da taşınır. Prompta ticket kimliği, beklenen test yanıtı veya belirli bir SQL/ayar eklenmedi. Yanıt modeli, kaynaklar ve arama akışı değiştirilmedi.

## Hedefli gerçek API kontrolleri

Önceki V2Q02 DNS sorusu iki kez, V2Q05 UAT/reporter teyidi sorusu bir kez çalıştırıldı. Sorular aynı kaldı; beklenenler çağrılardan önce `plan.json` içine kaydedildi. Yerel API yeniden başlatıldı ve bütün yanıtlarda yeni prompt sürümü doğrulandı.

| Kontrol | Beklenen kaynak | Aynı adaylar mı? | Yeni prompt | Süre (sn) | Elle inceleme |
|---|---|---|---|---|---|
| DNS_A | 1009846.0 | Evet | 2026-11-05-v2 | 11.191 | Uygun |
| DNS_B | 1009846.0 | Evet | 2026-11-05-v2 | 10.060 | Uygun |
| UAT_CONTROL | 1007291.0 | Evet | 2026-11-05-v2 | 8.922 | Uygun |

İki DNS yanıtında da önceki “ekran hataları tablespace/schema izinleriyle ilgili olabilir” tahmini tekrarlanmadı. Model bağlantı düzeltmesini diğer sorunlardan ayırdı ve bütün uygulamanın düzeldiğini iddia etmedi. Kaynakta geçen ayrı konuları anmak, onları yeni neden olarak önermekten ayrıdır.

İlk düzeltme sonrası DNS yanıtı:

> Benzer kayıtta IP ve hostname ile erişim karşılaştırılmış; hostname ile bağlanamayan ikinci makine için DNS ayarının düzeltilmesi ele alınmış. Network/sys ekibi DNS/erişim üzerinde çalıştığını ve ardından kurulum ile bağlantıların açıldığını bildirmiştir (ticket 1009846.0). Ancak bu, müşteri tarafından ayrıca doğrulanmış bir sonuç değildir (resolution_confirmed=false). Ayrıca bağlantının açılması, tüm uygulama sorunlarının çözüldüğünü göstermez: aynı kayıtta sonraki ekran hatalarının sürdüğü, tablespace/schema izinleri ve uygulama ekranı sorunlarının DNS çözümüne bağlanmadığı belirtilmiştir. Kesin DNS ayarları ve host/IP/port ayrıntıları kaynakta maskelidir.

UAT kontrolünde de ilgili kayda yanıt vermeyi sürdürdü: reporterın test ortamı başarısı ile production uygulaması ve supportun izleme aktarımını ayırdı. Yeni kural, bu kontrolde kaynak destekli cevabı gereksiz yere reddetmeye yol açmadı.

## Yerel kod kontrolleri ve ölçüm sınırı

Mevcut dokuz RAG/prompt testi geçti. Bunlar zincir, kaynak kimliği denetimi, uzmanlık modunun taşınması ve yönerge/veri ayrımını ağ çağrısı olmadan kontrol eder; tek başına modelin dilsel davranışını kanıtlamaz. Gerçek davranış için yukarıdaki üç API yanıtı elle incelendi.

Üç kontrolde beklenen kaynak ilk üçte ve yanıtta kullanıldı. Her çağrıda aday ticket listesi önceki V2 çalıştırmasındakiyle aynıydı. Veri kümesi 191 ticket olarak kaldı; ilk V2 sonuç dosyası korunmuştur.

Bu hedefli kontrollerde yorum taşması görülmedi. Bu, her gelecekteki yanıtta kesin olarak engelleneceği veya tüm V2 setinin yeni promptla tekrar geçtiği anlamına gelmez. Yeni promptla tam V2 çalıştırması ayrıca yapılabilir.

Yapılandırılmış yanıt modeli: `gpt-5.6-terra`. Embedding modeli: `@cf/baai/bge-m3`.

Plan: `D:\ai-muhendis-chatbot\outputs_local\prompt_grounding_v2_regression\plan.json`

Ham API yanıtları: `D:\ai-muhendis-chatbot\outputs_local\prompt_grounding_v2_regression\api_results.json`

Elle inceleme: `D:\ai-muhendis-chatbot\outputs_local\prompt_grounding_v2_regression\manual_review.json`
