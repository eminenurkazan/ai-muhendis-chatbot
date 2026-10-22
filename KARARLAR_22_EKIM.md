# 22 Ekim 2026 — uygulama kararları ve açık sorular

Bu belge, yerel geliştirme koşullarını ve henüz yanıtı bilinmeyen teslim kararlarını ayırır. Proje isterlerindeki bir seçenek, şirkette sağlanmış bir hizmet gibi kabul edilmez.

## Kesinleşenler

- Geliştirme, öğrencinin kendi Windows bilgisayarında ve `D:\ai-muhendis-chatbot` klasöründe yürür. Docker'ın disk konumu `D:\DockerWSL`; SQL Server Express'in program ve veritabanı dosyaları sıkıştırılmamış `D:\SQLServer2022` klasörü altındadır. SQL Server'ın bazı ortak kurulum bileşenleri C: üzerinde kalır.
- PostgreSQL + pgvector, ticket metinleri ve embedding araması içindir. 22 Ekim kontrolünde 20 onaylı/aramaya hazır kayıt ve 20 chunk vardır. Bunlar yeniden üretilmez.
- LocalDB 2019 kullanıcı oturumunda başlatılamadığı için uygulama bağlantısında kullanılmıyor; eski kurulum kaldırılmadı. SQL Server 2022 Express doğrudan Windows'a kuruldu. Bağlantı adı `.\SQLEXPRESS`, sürücü 64 bit ODBC Driver 17, kimlik doğrulaması Windows hesabıdır.
- `ServisMasasiApp` veritabanında `users`, `chat_sessions`, `chat_messages`, `feedback` ve `app_logs` tabloları oluşturuldu. Kullanıcı/sohbet/mesaj veri erişim katmanı `mssql/repository.py` dosyasındadır; altı yerel entegrasyon testi geçti ve örnek kayıtlar geri alındı. E-posta normalizasyonu için Türkçe harf dönüşümünden bağımsız bir alan kuralı uygulandı. Bağlantı `mssql/verify_sqlexpress.ps1` ile kullanıcı oturumunda da doğrulandı. API henüz bu tablolara yazmıyor.
- SQL Server motorunun başlatma tipi Manual, SQL Server Browser Disabled olarak seçildi. Bellek ayarında önerilen `max server memory=1410 MB` kabul edildi; bu değer işlemin tüm RAM kullanımına konmuş kesin bir sınır değildir. Bilgisayar yeniden açıldığında MSSQL testi öncesinde hizmetin çalıştığı kontrol edilmelidir.
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

Modüler LangChain RAG akışı, ayrı MSSQL bağlantısı ve küçük veri erişim katmanı hazırdır. Sonradan eklenen Windows/Oracle uzmanlık prompt'ları API'den seçilebilir; altı yeni çevrimdışı test ve iki seçilmiş gerçek API kontrolü geçti. Kullanıcı/JWT ve sohbet geçmişinin API'ye bağlanması sonraki uygulama işleridir. Son birleşik kontrolde 15 test geçti. Commit ve GitHub'a gönderme adımları kullanıcı onayıyla yapılır; çalışma özeti [CALISMA_NOTU_22_EKIM.md](CALISMA_NOTU_22_EKIM.md) içindedir.
