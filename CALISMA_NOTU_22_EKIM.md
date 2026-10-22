# 22 Ekim çalışma ve öğrenme notu

Amaç, çalışan RAG çekirdeğini modüllere ayırmak ve yerel uygulama veritabanını hazırlamaktı. Günün ilk bölümünde LangChain zinciri ve katman ayrımı `f2b0211` commit'iyle kaydedildi. Sonraki MSSQL ve uzmanlık prompt'u değişikliklerinin son kontrolleri bu notta özetlenir.

## Ortaya çıkan yapı

Bir soru `api.py` üzerinden alınır. `rag_service.py` soruyu ve uzmanlık modunu doğrular. `rag_chain.py` embedding, arama ve yanıt adımlarını birleştirir. `rag_provider.py` mevcut Cloudflare ve ChatGPT erişimini kullanır; `rag_repository.py` PostgreSQL aramasını çağırır. Kaynak kimlikleri doğrulandıktan sonra yanıt, kullanılan kaynaklar, süre, uzmanlık modu ve prompt sürümü döner.

PostgreSQL + pgvector içinde mevcut 20 onaylı ticket ve 20 adet 1024 boyutlu BGE-M3 chunk'ı korunur. Bugün bu veriler yeniden hazırlanmadı veya tekrar embedding üretilmedi.

SQL Server 2022 Express, Windows'a doğrudan kuruldu. `.\SQLEXPRESS` içindeki `ServisMasasiApp`, `users`, `chat_sessions`, `chat_messages`, `feedback`, `app_logs` tablolarını içerir. Veri ve günlük dosyaları sıkıştırılmamış `D:\SQLServer2022` altındadır. LocalDB kullanıcı oturumunda açılamadığı için uygulama bağlantısında kullanılmaz; eski kurulum kaldırılmadı.

SQL Server motoru Manual başlatılır. Önerilen `max server memory=1410 MB` seçildi; bu ayar tüm süreç belleğini kesin olarak sınırlamaz. Windows yeniden açılınca gerekiyorsa Yönetici PowerShell'de hizmet başlatılır:

```powershell
Start-Service -Name 'MSSQL$SQLEXPRESS'
```

## Öğrenilen ayrımlar

- Veritabanının kurulması, uygulamanın onu kullanmasıyla aynı aşama değildir. MSSQL tabloları ve kullanıcı/sohbet/mesaj repository'si hazırdır; `/ask` henüz sohbet geçmişini kaydetmez.
- Repository, SQL sorgularını tek yerde toplar. Kullanıcı değerleri parametrelerle gönderilir. Sohbet sahipliği, doğrulanmış kullanıcı kimliğiyle denetlenmelidir; mevcut yöntemler JWT giriş sistemi oluşturmaz.
- Transaction, ilişkili kayıtları birlikte kaydetmeye veya geri almaya yarar. Repository commit yapmaz; bunu çağıran servis yönetir. Testler örnek kayıtları geri alır. Bulut yanıtı beklerken transaction açık tutulmamalıdır.
- Türkçe harf ayarı e-posta normalizasyonunda `I/ı` farkı oluşturdu. Testte yakalanan sorun, yalnızca e-posta alanına ve sorgusuna açık collation kuralı verilerek düzeltildi. Genel veritabanı dili değiştirilmedi.
- Prompt, her soruda modele verilen çalışma yönergesidir. `windows_server` veya `oracle_db` seçimi Terra'yı yeniden eğitmez ve bilgi tabanına yeni kaynak eklemez. Mevcut varsayılan yönerge korunmuştur.
- Aramadan üç aday gelmesi, üçünün de ilgili olduğu anlamına gelmez. `retrieved_ticket_ids` adayları; `used_ticket_ids` yanıtın dayandığı kayıtları gösterir.

## Kontrol sonuçları

Birleşik test çalıştırmasında 6 MSSQL, 3 RAG ve 6 prompt testi olmak üzere **15/15 test geçti**. MSSQL testleri kullanıcı/e-posta, sohbet sahipliği, sıralı Türkçe mesajlar, kaynak özetleri, hatalı girişler ve yanlış veritabanının reddedilmesini kontrol etti. Örnek kayıtlar geri alındı.

Kullanıcı yeni sunucuyu başlatıp iki gerçek API isteği çalıştırdı:

| Mod ve soru | Gözlenen sonuç | Süre |
|---|---|---|
| Windows Server / AD'den BitLocker kurtarma anahtarı | İlgili kaynak yok; kullanılan kaynak listesi boş, `insufficient_context=true`. | 9873 ms |
| Oracle / yavaş sequence değerleri | Kaynak `1010047.0`; SQL veya cache değeri uydurulmadı, müşteri doğrulaması bulunmadığı belirtildi. | 11674 ms |

İki yanıtta da `prompt_version=2026-10-22-v1` görüldü. Bu kontroller sınırlı örneklerdir; genel Windows/Oracle uzmanlığı veya saldırılara dayanıklılık kanıtı değildir. 9 Ekim'deki 10 soruluk değerlendirme bu adımda yeniden çalıştırılmadı.

## Teslime kadar öncelikler

1. Kullanıcı kayıt/giriş, parola hash'leme, JWT ve sohbet sahipliğiyle API bağlantısını tamamlamak.
2. Sohbet geçmişi, kaynak gösterimi ve geri bildirimi kullanıcı arayüzüne bağlamak.
3. Windows Server/Oracle hedef sürümlerini ve kaynak kapsamını netleştirip olumlu/kapsam dışı sorularla değerlendirmeyi genişletmek.
4. Yerel kurulum yönergelerini, ER diyagramını, test raporunu ve gösterimi tamamlamak.

Şirket GitLab erişimi, başlangıç belgelerinin teslim kanalı ve hedef ürün sürümleri açık karar olarak `KARARLAR_22_EKIM.md` içinde tutulur. Mevcut çalışma kişisel bilgisayarda yerel gösterim içindir. Commit ve GitHub'a gönderme kullanıcı onayıyla yapılır.
