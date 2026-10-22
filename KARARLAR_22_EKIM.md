# 22 Ekim 2026 — uygulama kararları ve açık sorular

Bu belge, yerel geliştirme koşullarını ve henüz yanıtı bilinmeyen teslim kararlarını ayırır. Proje isterlerindeki bir seçenek, şirkette sağlanmış bir hizmet gibi kabul edilmez.

## Kesinleşenler

- Geliştirme, öğrencinin kendi Windows bilgisayarında ve `D:\ai-muhendis-chatbot` klasöründe yürür. C: diskinde az boş alan olduğu için yeni kullanıcı veritabanı dosyaları oluşturulacaksa D: tercih edilir. Mevcut LocalDB kurulum ve sistem dosyaları C: üzerinde bırakılır.
- PostgreSQL + pgvector, ticket metinleri ve embedding araması içindir. 22 Ekim kontrolünde 20 onaylı/aramaya hazır kayıt ve 20 chunk vardır. Bunlar yeniden üretilmez.
- SQL Server LocalDB 2019 (`MSSQLLocalDB`) ve 64 bit ODBC Driver 17 kurulu. MSSQL, tasarıma göre kullanıcı, sohbet, geri bildirim ve uygulama olayları içindir. Yeni kullanıcı veritabanı henüz oluşturulmadı.
- API şimdilik yalnızca `127.0.0.1` üzerinde çalışan yerel pilottur; kimlik doğrulaması ve üretim güvenliği eklenmeden ağa açılmaz.
- Soru embedding'i Cloudflare BGE-M3 ile, yanıt ise mevcut kişisel ChatGPT oturumu üzerinden üretilir. Bu erişimler şirket hizmeti veya sınırsız üretim kapasitesi sayılmaz. Mevcut token saklama ve kaynak kimliği doğrulama davranışı korunur.
- Kodun ve testlerin asıl konumu D: projesidir. C: altındaki ChatGPT proje aynası ve `sources/` yalnızca referanstır.

## Açık sorular

| Konu | Şu anki durum | Netleşince yapılacak iş |
|---|---|---|
| Windows Server hedef sürümü ve erişim | İsterlerde sürüm veya sunucu verilmemiş. | Modül, kaynak ve testleri seçilen sürüme göre sınırla. |
| Oracle hedef sürümü ve erişim | İsterlerde sürüm veya sunucu verilmemiş. | SQL/backup önerilerini sürüm ve yetkiye göre doğrula. |
| Şirket GitLab erişimi | Henüz doğrulanmadı; mevcut depo GitHub'da. | Teslim istenen GitLab adresi/erişimi sağlanırsa ayrıca aktar. |
| Başlangıç belgelerinin teslim kanalı | Teslim edildiği doğrulanmadı. | Yetkili kişinin istediği kanal ve tarihi kaydet. |
| Çok kullanıcılı/uzaktan dağıtım | Sunucu tahsis edilmedi. | Şimdilik yerel gösterim yap; gerekiyorsa barındırma, sır saklama ve maliyeti ayrı kararlaştır. |

## Sıradaki teknik iş

Mevcut RAG akışını küçük parçalara ayırırken sonuç biçimi ve kaynak denetimi aynı kalacak. SQL Server bağlantısı PostgreSQL ayarından ayrı tutulacak. Gerçek tablo oluşturma, commit ve GitHub'a gönderme işlemleri ayrıca onaylanacak.
