# MSSQL bağlantısı ve ilk veri erişim katmanı

22 Ekim 2026. Windows üzerinde SQL Server 2022 Express, `.\SQLEXPRESS` örneği kullanılır. Uygulama veritabanı `ServisMasasiApp`; dosyaları `D:\SQLServer2022` altındadır. PostgreSQL, bilgi tabanı ve vektör araması için ayrı kalır.

## Dosyalar ve görevleri

- `connection.py`: `MSSQL_CONNECTION_STRING` ortam ayarından bağlantı açar; bağlantı dizesini hata mesajına koymaz.
- `schema.sql`: ilk kurulumda beş tabloyu oluşturur; yalnızca boş `ServisMasasiApp` üzerinde çalışır. Yeniden çalıştırma veya şema güncelleme aracı değildir.
- `repository.py`: kullanıcı oluşturma/bulma, kullanıcının sohbetlerini oluşturma/listeleme ve sıralı mesaj ekleme/okuma işlemleri sağlar.
- `verify_sqlexpress.ps1`: `master` üzerinde yalnızca Python bağlantısını kontrol eder.
- `verify_repository.ps1`: uygulama veritabanında geçici kayıtlarla altı entegrasyon testi çalıştırır; her test sonunda örnek kayıtları geri alır.
- `fix_email_collation.sql`: eski başlangıç şemasını kullanmış veritabanlarında e-posta harf dönüşümünü düzeltir. Güncel `schema.sql` aynı düzeltmeyi zaten içerir; yeni kurulumda ayrıca çalıştırılmaz.

## Katmanın çalışma biçimi

Repository, veritabanına giden SQL sorgularını tek yerde toplar. Kullanıcıdan gelen değerler sorgu metnine eklenmez; parametre olarak gönderilir. Kullanıcıya ait olmayan sohbet için okuma ve mesaj ekleme reddedilir. Mesaj sırası, sohbet satırı transaction boyunca kilitlenerek belirlenir. Sohbet listesi ve mesaj okuma çağrısı en fazla 100 kayıt döndürür; sonraki mesajlar `after_seq` ile alınır.

Repository bağlantıyı kapatmaz ve commit yapmaz. Çağıran servis, tüm işlem başarılıysa `connection.commit()`, hata olursa `connection.rollback()` çağırıp bağlantıyı kapatmalıdır. Böylece bir kullanıcı sorusu ve bot yanıtı gibi ilişkili kayıtlar birlikte kaydedilebilir. Uzun süren bulut çağrıları sırasında veritabanı transaction'ı açık tutulmamalıdır.

`create_user` hazır bir `password_hash` bekler; parola hash'leme veya giriş doğrulama işlemi yapmaz. Dönen kullanıcı bilgisinde hash bulunmaz. E-posta normalizasyonu ve sorgusu açıkça `Latin1_General_100_CI_AS_SC` karşılaştırma kuralını kullanır; Türkçe veritabanı ayarındaki `I/ı` dönüşümü e-posta aramasına taşınmaz. Bu adımda kimlik doğrulama uygulanmadı: `user_id` ileride doğrulanmış oturumdan alınmalıdır; istemcinin gönderdiği kimliğe güvenilmemelidir. Uzmanlık modu alanına kayıt yazılması, Windows/Oracle prompt'larının uygulandığı anlamına gelmez.

Kalıcı sohbet ekranı `/chats/{chat_id}/ask` üzerinden bu katmanı kullanır; bağımsız `/ask` kayıt yapmaz. Mevcut veritabanına `python -m mssql.upgrade_chat_persistence` ile nullable yanıt görüntüsü alanı eklenir; başlangıç şeması yeniden çalıştırılmaz. Geri bildirim yazımı ve sahiplik kontrolü uygulamaya bağlandı; aynı yanıtın puanı mevcut kayıt üzerinde güncellenir. Log tablosunun yazma yöntemleri sonraki uygulama adımında eklenecektir.

## Yerel kontrol

Hizmet Manual kurulduğu için kapalıysa Yönetici PowerShell'de başlat:

```powershell
Start-Service -Name 'MSSQL$SQLEXPRESS'
```

Normal PowerShell'de veri erişim testini çalıştır:

```powershell
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "D:\ai-muhendis-chatbot\mssql\verify_repository.ps1"
```

Bulut model çağrısı yapılmaz. Testler gerçek SQL Server kullanır; bağlantı veya tablo eksikliği testin başarısız olmasına yol açar. Normal test keşfinde `MSSQL_TEST_CONNECTION_STRING` ayarı verilmemişse bu yerel entegrasyon testleri atlanır. Bu ayar yalnızca açıkça test yapılacağı zaman verilmelidir.
