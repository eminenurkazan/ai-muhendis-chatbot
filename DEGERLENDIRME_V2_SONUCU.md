# 191 ticket ile V2 değerlendirme sonucu

10 soru yerel `/ask` API’sinde birer kez çalıştırıldı. Sorular ve beklenen kaynaklar sonuçlar görülmeden hazırlanmıştı; çalıştırmadan sonra soru veya yanıt ölçütü değiştirilmedi.

- İlgili sorularda beklenen kaynak ilk üçte: **8/8**. Hepsi ayrıca birinci sırada.
- Kaynak bulunmayan sorularda doğru ret: **2/2**.
- Beklenen kaynağın yanıtta kullanılması: **8/8**.
- Kullanılan kaynak kimliklerinin dönen adaylarla/metinle tutarlılığı: **10/10**.
- Elle kaynak bağlılığı incelemesi: **9 uygun, 1 kısmen uygun**.
- Ortalama API süresi: **9.324 saniye**; en kısa 6.071, en uzun 12.390 saniye.

## Soru bazında sonuçlar

| Soru | Beklenen ticket | Kaynağın sırası | Kaynak yok testi | Süre (sn) | Elle kaynak bağlılığı |
|---|---|---|---|---|---|
| V2Q01 | 1008656.0 | 1 | — | 11.610 | Uygun |
| V2Q02 | 1009846.0 | 1 | — | 12.390 | Kısmen uygun: ek ihtimal |
| V2Q03 | 1006956.0 | 1 | — | 10.085 | Uygun |
| V2Q04 | 1008137.0 | 1 | — | 8.516 | Uygun |
| V2Q05 | 1007291.0 | 1 | — | 10.531 | Uygun |
| V2Q06 | 1004444.0 | 1 | — | 8.531 | Uygun |
| V2Q07 | 1010324.0 | 1 | — | 8.788 | Uygun |
| V2Q08 | 1006259.0 | 1 | — | 10.385 | Uygun |
| V2Q09 | Yok | — | Geçti | 6.071 | Uygun |
| V2Q10 | Yok | — | Geçti | 6.335 | Uygun |

## Bulunan küçük sorun

V2Q02, DNS ve IP/hostname farkını doğru açıklıyor; bağlantının açılmasının tüm uygulama sorunlarının bittiğini göstermediğini de doğru söylüyor. Ancak “bunlar tablespace/schema izinleri gibi DNS’den bağımsız konular olabilir” diyerek son ekran hatalarına kaynakta kurulmamış bir olasılık ekliyor.

1009846.0 kaydında schema/izin konusu daha önce ayrı ele alınıp c41–c42de kapatılmış; son ekran hataları c60–c61de geçiyor. Bunların sebebini schema izni olarak bağlayan kanıt yok. Bu kesin bir ters bilgi değil, kaynak sınırını aşan küçük bir nedensel yorumdur. Daha sıkı yanıt: “Bağlantı açılmış olsa da sonraki ekran hataları sürmüş; bu kayıt onların kesin nedenini ortaya koymuyor.”

Sorun raporlandı; bu çalıştırmada RAG promptu veya üretim yanıtı değiştirilmedi. Sonraki küçük adım bu tür ek ihtimalleri önleyecek prompt düzenlemesi ve hedefli yeniden kontrol olabilir.

## İçerik tamlığı ile kaynak bağlılığının ayrılması

V2Q03, V2Q06 ve V2Q07 rehberdeki bazı ek ayrıntıları kısa geçiyor: sırasıyla HQ/script kurulumu; uygulama izni ile bildirimi yapan roller; önceki başarısız denemeler ve statü/summary incelemesi. Bu nedenle rehber ayrıntı kapsamları kısmi kaydedildi. Yanıtlardaki ana soruya verilen bilgiler kaynakla uyumlu; eksik arka plan, uydurma bilgiyle aynı ölçülmedi. Her ölçüt için kapsam durumu manual review JSONunda saklandı.

## Çalıştırma koşulları ve tekrar kullanım

- Kullanılabilir Mendeley ticketı: 191.
- Yapılandırılmış yanıt modeli: `gpt-5.6-terra`.
- Embedding modeli: `@cf/baai/bge-m3`.
- Uzmanlık modu: `service_desk`.
- Prompt sürümü: `2026-10-22-v1`.
- `elapsed_ms`, mevcut API’nin embedding, arama ve yanıt üretme süresidir; uçtan uca HTTP ağ süresi ayrıca ölçülmedi.
- `evaluate_api.py` artık `--questions` ve `--output-dir` alır. Varsayılan V1 korunur; sonuç dosyası seçilen setin adını ve zamanını taşır. Her soru sonucu hemen kaydedilir.
- Ham yanıtlar korunmuştur; manuel inceleme ayrı dosyadadır. Bu sonuç 10 soruyla sınırlıdır ve tüm uygulamanın yüzde 100 doğru olduğu anlamına gelmez.

V2 tekrar çalıştırma komutu (yeni bulut istekleri oluşturur):

```powershell
Set-Location -LiteralPath "D:\ai-muhendis-chatbot"
.\.venv\Scripts\python.exe .\evaluate_api.py --questions .\evaluation_questions_v2.json --output-dir .\outputs_local\evaluation_set_v2_191_tickets\runs
```

Ham sonuç: `D:\ai-muhendis-chatbot\outputs_local\evaluation_set_v2_191_tickets\runs\evaluation_results_v2_20261105_161914_454264.json`

Elle incelenmiş sonuç: `D:\ai-muhendis-chatbot\outputs_local\evaluation_set_v2_191_tickets\runs\evaluation_results_v2_20261105_161914_454264_manual_review.json`

Çalıştırma bağlamı: `D:\ai-muhendis-chatbot\outputs_local\evaluation_set_v2_191_tickets\runs\evaluation_results_v2_20261105_161914_454264_context.json`
