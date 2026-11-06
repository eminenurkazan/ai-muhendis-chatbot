# Uzmanlık veri seti genişletmesi

Tarih: 5 Kasım 2026. Mevcut Mendeley Help Desk Tickets kaynağına ek olarak Server Fault ve Database Administrators kaynaklarından iki ayrı teknik soru–cevap alt kümesi indirildi. Bunlar elle yazılmış birkaç örnek veya model tarafından üretilmiş cevaplar değildir; kaynak kimliği korunan gerçek topluluk soru–cevaplarıdır.

## İndirilen veri

Son indirme klasörü: `outputs_local/expertise_qa/20261105T065002_329245Z`.

| Kaynak | Alan | Benzersiz soru adayı | Otomatik koşulları geçen | Seçilen soru–cevap |
|---|---|---:|---:|---:|
| Server Fault | Windows Server | 340 | 277 | 200 |
| Database Administrators | Oracle DB | 138 | 114 | 114 |
| Toplam | | 478 | 391 | 314 |

Windows için en fazla 200 kayıt seçildi; kalan 77 uygun aday ilk kümenin dışında kaldı. Oracle tarafında koşulları geçen 114 kayıt bulundu; sayı hedefe ulaşsın diye koşullar düşürülmedi. Başka sorgular veya sayfalarla kapsam ileride genişletilebilir. Bu alt küme bütün Stack Exchange verisinin kopyası değildir; sorguları ve sınırları manifest içinde kayıtlıdır.

## Konu kapsamı

Windows kümesinde 54 Active Directory, 50 IIS, 46 Event Log ve 70 Windows Server sürümü sorgusuyla eşleşen kayıt vardır. Oracle kümesinde 15 performans, 19 tablespace, 32 backup/RMAN ve 55 genel Oracle eşleşmesi bulunur. Bir kayıt birkaç konuyla eşleşebildiği için bu sayılar toplanınca benzersiz kayıt sayısını vermez.

Tüm seçilen sorular 2018 ve sonrasında açılmıştır. Birden fazla Windows Server ve Oracle sürümü yer alır; 2018 sonrası soru tarihi, kullanılan ürün sürümünün güncel olduğunu göstermez. 62 kayıtta resim bulunur, 56 kayıtta eski ürün sürümü etiketleri için inceleme işareti vardır; bu iki grup örtüşebilir.

## Kalite ve kaynak takibi

- Her sorunun kabul edilmiş cevabı, soru ve cevap kimlikleriyle eşleştirildi.
- Cevap puanı en az 1 olmalı; çok kısa metinler ve eksik yazar/lisans bilgileri elendi.
- Soru ve cevap yazarları, özgün bağlantıları, ayrı lisansları ve tarihleri korunur.
- HTML'deki paragraf ve kod blokları metne çevrildi; ham API yanıtları ayrıca saklandı.
- 314 kimliğin tamamı benzersizdir. Veri hazırlama kodunun dört çevrimdışı testi geçti.

Kabul edilmiş cevap, teknik doğruluk veya farklı sürümlerde uygulanabilirlik garantisi değildir. Özellikle komut, yetki, veri kaybı/kesinti etkisi, eksik görsel bağlam ve hedef sürüm uygunluğu incelenmelidir. Ayrıntılar [data_sources/README.md](data_sources/README.md) içindedir.

## İlk indirme anındaki durum

**314 kayıt indirildi; henüz chatbot'un aramasına eklenmedi.** Hepsi `pending` durumundadır. Bu adımda embedding üretilmedi ve PostgreSQL değiştirilmedi. Mevcut çalışan bilgi tabanı hâlâ Mendeley kaynaklı 20 onaylı ticket'tır.

Sıradaki adım, temsili örneklerle inceleme ölçütlerini netleştirmek, uygunsuz kayıtları ayırmak ve QA aktarımını hazırlamaktır. Onaylanan kayıtlar için soru–cevap bütünlüğü ve kod blokları korunarak chunk oluşturulmalı; sürüm, alan ve atıf bilgileriyle PostgreSQL'e aktarılmalıdır. Uzmanlık moduna uygun arama ve doküman bağlantılı kaynak gösterimi de bu aktarımın parçasıdır. Sonrasında yeni alanlara ait bağımsız olumlu ve kaynak dışı testler çalıştırılmalıdır.

Ham metinler, yazar bilgileri ve örnekler Git'e kendiliğinden eklenmez. Paylaşılacak veri paketi ilgili lisanslara ve atıf koşullarına uygun ayrıca hazırlanmalıdır. Bu adımda commit veya push yapılmadı.


## 6 Kasım 2026 güncel durum

314 adayın tamamı kaynak incelemesinden geçti: 255 uzmanlık QA uygulamada, 59 dışarıda. 191 Mendeley ticketıyla toplam 446 kayıt vardır. Son 150 kayıt resmî kaynaklarla karşılaştırıldı: 137 dar kapsam için destekli, 13 için destek yetersiz. Bunlar bağımsız ürün ortamında test edilmiş bütün cevaplar değildir. [Güncel kullanım](UZMANLIK_VERILERININ_KULLANIMI.md) ve [karşılaştırma raporu](RESMI_BELGE_KARSILASTIRMASI_150.md). Ham dosyalar ve embedding önbellekleri yereldir; Git kopyası veritabanını kendiliğinden kurmaz.
