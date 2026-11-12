# İlk Oracle rehberi — 12 Kasım 2026

Oracle Database 19c SQL Tuning Guide içindeki EXPLAIN PLAN ön koşulları ve Example 6-3 temel alınmıştır. Amaç bir sorgunun tahmini yürütme planını aynı oturumda üretmek ve BASIC biçiminde görüntülemektir. Bu bir performans düzeltmesi değildir.

- Resmî kaynak: https://docs.oracle.com/en/database/oracle/oracle-database/19/tgsql/generating-and-displaying-execution-plans.html
- Hazırlanan kayıt: `data_sources/official_guides/oracle_explain_plan.json`. **Bu dosya telif nedeniyle Git'e konmaz** (`.gitignore`); yalnız yerelde ve veritabanında durur. Ayrıntı: [KAYNAK_POLITIKASI.md](KAYNAK_POLITIKASI.md).
- Tür: `documentation`; kapsam: `procedure`; alan: `oracle_db`.
- Oracle telif atfı korunur; Microsoft kaynaklarına ait CC-BY-4.0 lisansı bu rehbere taşınmaz. Tam kitap depoya konmaz; kısa uyarlanmış açıklama ve sınırlı kaynak örneği kullanılır.
- PLAN_TABLE erişimi, açıklanan sorgunun nesne yetkileri, employees örnek tablosu ve kullanılmamış statement ID ön koşulları kayıttadır. Tablo kurma veya geniş yetki verme komutları üretilmez.
- EXPLAIN PLAN, açıklanan SELECT'i yürütmez; plan tablosuna yazar. Tahmini plan gerçek çalışma planından farklı olabilir; BASIC çıktısı gerçek süre/satır ölçümü sunmaz.
- Komutlar indirilen özgün HTML metniyle boşluk normalizasyonu dışında eşleşecek şekilde kontrol edildi. Kaynak HTML ve SHA-256 izi `outputs_local/oracle_guide_first_20261112` altında korunur.
- Mevcut aktarım aracıyla 1024 boyutlu embedding üretildi ve tek bütünlüklü chunk aktarıldı. Önceki 447 kayıt/chunk değişmeden kaldı; toplam 448 oldu. Önceki Windows rehberi korundu.
- Kendi vektörüyle ilk üçte bulunma ve doğal dil sorusuyla yanıt kontrolü geçti. İki kaynak komutu korundu; tahmini/gerçek plan ayrımı doğru aktarıldı. Doğal dil sorusu ve yanıt `answer_check.json`, aktarım sonucu `import_receipt.json` dosyasında saklanır. Tek soruluk kontrol genellenmiş başarı oranı değildir.
- Oracle sunucusunda SQL çalıştırılmadı; `execution_tested=false`. Model veya API bağlantısı değiştirilmedi. Yeni uygulama kodu veya şema güncellemesi gerekmedi.

## Manuel deneme

Oracle DB modunda yeni sohbet açıp şu soruyu sorun:

> Oracle 19c'de employees örnek tablosuna erişimim ve PLAN_TABLE yetkilerim var. Kullanılmamış ex_plan2 kimliğiyle EXPLAIN PLAN ve DBMS_XPLAN.DISPLAY BASIC kullanarak tahmini planı nasıl görüntülerim? Bu gerçek çalışma süresini gösterir mi?

Kaynaklar bölümünde Oracle SQL Tuning Guide görünmeli. Bot gerçek çalışma süresi ölçüldüğünü veya sorgunun hızlandırıldığını söylememelidir. Yalnız yeni rehber verisi eklendiği için, önceki Windows rehber kodu zaten yüklüyse API yeniden başlatması gerekmez.
