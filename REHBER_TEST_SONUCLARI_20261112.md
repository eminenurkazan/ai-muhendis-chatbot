# İlk iki resmî rehberin test sonuçları

Tarih: 12 Kasım 2026. Bu rapor iki rehberin aktarım ve RAG davranışına ait ara doğrulamadır. İsterlerdeki 10 servis masası + 5 Windows Server + 5 Oracle optimizasyon senaryosunu kapsayan son raporun yerine geçmez.

## Hazırlık ve kapsam

- Başlangıçtaki 446 kayıt/chunk korundu. Microsoft rehberiyle 447, Oracle rehberiyle 448 kayıt/chunk oldu.
- Her rehberin ön koşulları, belgeli komutları, beklenen çıktısı ve sınırları tek kısa chunk içinde saklanır. Tür documentation, kapsam procedure olarak işaretlidir.
- Kaynak URL, yazar, sürüm/içerik hash’i, uyarlama ve telif bilgileri korunur. Microsoft CC-BY-4.0 lisansı Oracle kaynağına uygulanmadı.
- Kendi vektörüyle ilk üçte bulunma kontrolü iki kayıtta da geçti. Bu kontrol doğal dil başarımıyla aynı değildir.
- Oracle kaydı yeniden aktarılınca added=0, already_present=1 döndü; kopya oluşmadı.

## Kaydedilmiş doğal dil kontrolleri

Bu iki çağrı, mevcut RAG hizmetinden gerçek embedding, PostgreSQL araması ve bulut yanıt modeli kullanılarak yapıldı. Süre rag_service ölçümüdür; arayüz, JWT kontrolü ve MSSQL’e sohbet kaydını içermez.

| Kontrol | Mod | Beklenen ve kullanılan kaynak | Arama sırası | Süre | Sonuç |
|---|---|---|---|---|---|
| G01 | windows_server | microsoft:kb2498185:replication-diagnosis | 1 | 13.516 sn | Kaynak ve belgeli komut korundu |
| G02 | oracle_db | oracle:19c:tgsql:explain-plan-basic | 1 | 12.253 sn | Kaynak ve belgeli komut korundu |

### G01 sorusu

Windows Server Active Directory ortamında etki alanı denetleyicilerinin çoğaltma hatalarını repadmin ile CSV raporuna nasıl çıkarabilirim? Gerekli araç ve yetkiyi de belirt.

### G02 sorusu

Oracle 19c örnek employees tablosuna erişimim ve PLAN_TABLE yetkilerim var. Kullanılmamış ex_plan2 kimliğiyle tahmini planı EXPLAIN PLAN ve DBMS_XPLAN.DISPLAY BASIC kullanarak nasıl görüntülerim? Bu gerçek çalışma süresini gösterir mi?

## Yanıtların elle değerlendirilmesi

- Windows: Repadmin/RSAT ve kaynak makalenin yetki koşulu belirtilmiş; CSV yönlendirmesi korunmuş. Dosyaya yazma/üzerine yazma etkisi açıklanmış. Raporlama işlemi onarım gibi sunulmamış. Enterprise Admins ifadesi bu kaynak yönteminin koşuludur; bütün repadmin kullanımları için asgari yetki iddiası değildir.
- Oracle: Example 6-3 içindeki iki SQL komutu korunmuş; aynı oturum, PLAN_TABLE ve örnek employees tablosu kapsamı korunmuş. Tahmini planın gerçek süre/satır ölçümü olmadığı ve gerçek yürütme planından farklı olabileceği açıklanmış.

## Kullanıcının arayüz kontrolleri

| Kontrol | Gözlenen sonuç |
|---|---|
| Windows Server modunda AD raporlama sorusu | Kaynaklı yanıt, kod bloğu ve raporun onarım olmadığı açıklaması doğru görüldü. Ekranda 16,5 sn gösterildi. |
| Windows Server modunda Oracle sorusu | Oracle rehberi bu alan filtresine girmedi; model doğrudan kaynak bulamadığını söyledi. Mod değiştirme yönlendirmesi için iyileştirme fırsatı var. |
| Oracle DB modunda Oracle sorusu | İlk denemede zaman aşımı; sonraki başarılı denemede iki SQL kod bloğu ve tahmini/gerçek plan ayrımı doğru görüldü. |
| Oracle geçmiş sohbetini açma | Mesaj okuma istekleri 200 OK döndü. O aşamada sohbetin 0 mesaj içerdiği doğrudan SQL okumasıyla doğrulandı. Önceki tamamlanmamış istekten yalnız başlık kalmıştı. |

## Açık sorun: aralıklı bekleme ve zaman aşımı

Kullanıcı arayüzde koyulaşma, oturum hizmetine geçici erişilememe uyarısı ve istek zaman aşımı gözledi. Sonradan yapılan bağlantı ölçümlerinde SQL ve rehber araması çalıştı; bu, önceki isteğin neden geciktiğini kanıtlamaz. Neden kesinleştirilmedi ve sorun çözülmüş sayılmıyor. Tamamlanmış HTTP erişim satırları tek başına aşama sürelerini göstermiyor. Tekrarında istek kimliğiyle ilişkili, gizli bilgi içermeyen aşama süreleri izlenmeli.

Boş sohbet açıldığında kullanıcıya açıklama ve yükleniyor göstergesi eklendi. Bu bir görünürlük düzeltmesidir; zaman aşımının kök neden çözümü değildir. Önceki başarısız soru/yanıtlar sonradan uydurularak geçmişe eklenmedi.

## Yazılım testleri ve sınırlar

- Microsoft rehberinin aktarım kodu eklendikten sonra gerçek yerel SQL kontrolleri de açıkken 96 yazılım testi geçti.
- Oracle eklemesi aynı aktarım koduyla veri olarak yapıldı; kaynak komut eşleşmesi, aktarım, doğal dil yanıtı ve tekrar aktarım kontrol edildi.
- Boş sohbet açıklaması sonrasında test_saved_chat.py çalıştırıldı: 7 geçti, gerçek SQL testi bu çalıştırmada kapalı olduğu için 1 atlandı.
- Komutlar gerçek Active Directory veya Oracle Database üzerinde çalıştırılmadı. execution_tested=false; performans artışı, gerçek ortam başarısı veya onarım doğrulaması iddia edilmez.
- İki örnek sınırlıdır: tüm bilgi tabanı veya uzmanlık alanı için başarı yüzdesi hesaplanamaz.

## Yerel kanıtlar

- outputs_local/official_guide_first_20261112/answer_check.json — Windows sorusu, yanıtı, kaynak kimlikleri ve süre.
- outputs_local/official_guide_first_20261112/source.md — özgün Microsoft kaynak görüntüsü.
- outputs_local/oracle_guide_first_20261112/answer_check.json — Oracle sorusu, yanıtı, kaynak kimlikleri ve süre.
- outputs_local/oracle_guide_first_20261112/import_receipt.json — önceki 447 kaydın korunduğu aktarım makbuzu.
- outputs_local/oracle_guide_first_20261112/source.html — özgün Oracle kaynak görüntüsü.

Bu yerel kanıtlar Git dışında tutulur. Depodaki yapılandırılmış rehber kayıtlarında kaynak URL ve hash bilgileri vardır. Depoyu klonlamak, PostgreSQL kayıtlarını veya embedding önbelleğini kendiliğinden taşımaz; aktarım ayrıca çalıştırılmalıdır.

## Üçüncü rehber: domain join DNS çözümleme (12 Kasım 2026)

- Kaynak: Microsoft KB4341920 (CC-BY-4.0), kayıt `microsoft:kb4341920:domain-join-dns-resolution`. Kaynak politikası: [KAYNAK_POLITIKASI.md](KAYNAK_POLITIKASI.md).
- Aktarım: önceki 448 kayıt/chunk değişmedi, toplam 449. Kendi vektörüyle ilk üçte bulundu (`verify`).
- Doğal dil kontrolü (windows_server modu, rehber cümlelerinden farklı soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı; `nltest /dsgetdc` komutu korundu, komutun yalnız sınama yaptığı ve onarım yapmadığı belirtildi, NetBIOS yerine DNS adı uyarısı ve NetSetup.log eklendi. Süre 12,4 sn (rag_service ölçümü). Kaynakta olmayan çıktı yorumu eklenmedi.
- Komut gerçek AD ortamında çalıştırılmadı; `execution_tested=false`.

## Dördüncü rehber: IIS HTTP 403.14 (12 Kasım 2026)

- Kaynak: Microsoft KB942062 (CC-BY-4.0), kayıt `microsoft:kb942062:iis-403-14-directory-listing`. Önceki 449 kayıt/chunk değişmedi, toplam 450. Kendi vektörüyle ilk üçte bulundu.
- Doğal dil kontrolü (windows_server modu): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt önce Default Document yönteminin uygun olduğunu söyledi, Directory Browsing'in güvenlik etkisini belirtti. Süre 11,4 sn.
- Elle değerlendirme: Güvenlik uyarısı kaynakta değil, rehber kaydının bize ait sınırlamalar bölümündedir; yanıt bunu kaynaktaymış gibi sunmadı ama "kaynak" ile "bizim notumuz" ayrımı yanıt metninde görünmüyor. "Site yöneticisi yetkisi gerektirir" ifadesi kaynak tarafından açıkça belirtilmiş bir yetki koşulu değildir (kaynak hedef kitleyi site yöneticileri olarak belirtir); küçük bir çıkarımdır.
- Komutlar gerçek ortamda çalıştırılmadı; `execution_tested=false`.

## Beşinci rehber: AD hesap kilitlenmesi, EventCombMT (12 Kasım 2026)

- Kaynak: Microsoft KB824209 (CC-BY-4.0), kayıt `microsoft:kb824209:ad-account-lockout-eventcombmt`. Önceki 450 kayıt/chunk değişmedi, toplam 451. Kendi vektörüyle ilk üçte bulundu.
- Doğal dil kontrolü (windows_server modu): beklenen kaynak ilk sırada ve yanıtta kullanıldı; menü adımları kaynağa uygun, "olayları toplar, nedeni belirlemez, kilidi açmaz" sınırı korundu. Süre 10,4 sn.
- Elle değerlendirme, eksikler: (1) Yanıt, aracın ayrı indirilmesi gerektiğini (Account Lockout and Management Tools / ALTools.exe) söylemedi. (2) Hazır aramadaki olay kimliklerinin eski Windows sürümlerine ait olduğu ve güncel karşılıklarının doğrulanmadığı uyarısı yanıtta yok. (3) "Okuma yetkisi olmalıdır" ifadesi kaynakta açıkça yazmaz; rehber kaydındaki bize ait nottur ve yanıtta kaynak koşulu gibi duruyor. Bu üç nokta prompt veya rehber metninin iyileştirme fırsatıdır; yanıt kaynakla çelişmiyor ama eksik.
- Komut/araç gerçek ortamda çalıştırılmadı; `execution_tested=false`.

## Altıncı rehber: IIS uygulama havuzu kapanma süresi, Event ID 5013 (12 Kasım 2026)

- Kaynak: Microsoft KB2634635 (CC-BY-4.0), kayıt `microsoft:kb2634635:iis-apppool-shutdown-5013`. Önceki 451 kayıt/chunk değişmedi, toplam 452. Kendi vektörüyle ilk üçte bulundu.
- Doğal dil kontrolü (windows_server modu, olay metnini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt ShutdownTimeLimit (varsayılan 90 sn), zorla kapatma/geri dönüştürme, iki inceleme yolu (süreyi kontrol etme, w3wp.exe bellek dökümü) ve "süreyi artırmak nedeni çözmez" sınırını doğru aktardı. Süre 12,3 sn.
- Elle değerlendirme: Yanıt rehberin IIS 7.0/7.5 kapsamını açıkça belirtti ve kullanıcının IIS sürümünü sordu; bu sürüm sınırının korunduğunu gösteren iyi bir davranıştır. Kaynakta olmayan komut veya ayar adımı uydurulmadı.
- Sınır: Kaynak 2020 tarihli ve IIS 7.0/7.5 içindir; yeni sürümler için geçerliliği doğrulanmadı. Komut içermez, gerçek ortamda denenmedi (`execution_tested=false`).

## Yedinci rehber: Oracle erişim yolları (12 Kasım 2026)

- Kaynak: Oracle 19c SQL Tuning Guide, Optimizer Access Paths; kayıt `oracle:19c:tgsql:optimizer-access-paths`. Kayıt dosyası telif nedeniyle Git dışındadır ([KAYNAK_POLITIKASI.md](KAYNAK_POLITIKASI.md)). Önceki 452 kayıt/chunk değişmedi, toplam 453. Kendi vektörüyle ilk üçte bulundu.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt "indeks var ama kullanılmadı" sorusuna kaydın nedenlerini sıraladı (fonksiyon, bileşik indeksin ilk sütunu, başı joker LIKE, düşük seçicilik, istatistik), access/filter farkını ve DISPLAY_CURSOR çağrısını verdi, imlecin önbellekte olması koşulunu belirtti. Süre 15,8 sn.
- Elle değerlendirme: Kaynakla çelişen veya kayıtta olmayan komut/öneri görülmedi. Yanıt belirli bir sorguyu hızlandırma iddiası taşımadı.
- Sınır: Kaydın bazı ifadeleri kaynak sayfasının özetinden alındı; sayfa HTML'inde yalnız işlem adları ve komut doğrulandı. Gerçek Oracle ortamında çalıştırılmadı; `execution_tested=false`.

## Sekizinci rehber: Oracle optimizer istatistikleri (12 Kasım 2026)

- Kaynak: Oracle 19c SQL Tuning Guide, Gathering Optimizer Statistics; kayıt `oracle:19c:tgsql:gathering-optimizer-statistics` (dosya telif nedeniyle Git dışında). Önceki 453 kayıt/chunk değişmedi, toplam 454. Kendi vektörüyle ilk üçte bulundu.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt STALE_STATS sorgusunu, YES/NO/NULL anlamını, %10 eşiğini, GATHER_TABLE_STATS çağrısını ve otomatik toplamayı doğru aktardı; "sonraki planları değiştirebilir, hızlanma garantisi yok, üretimde DBA ile değerlendirin" sınırlarını belirtti. Süre 21,1 sn (bu rehberin ölçümleri arasında en uzunu; model yanıt süresi dalgalanıyor).
- Elle değerlendirme: Kaynakla çelişen öneri görülmedi. "Gerekli yetkilere sahip olmanız gerekir" ifadesi kaynaktan değil, kaydın bize ait sınırlamalar notundandır.
- Sınır: Kaynak sayfanın son ~4000 karakteri özetleyici tarafından okunmadı; kayıttaki olgular okunan bölümden ve sayfa HTML'inde doğrulandı. Gerçek ortamda çalıştırılmadı; `execution_tested=false`.

## Chunk kararı

Bilgi tabanındaki kayıtlar (ticket, QA, rehber) kısadır; her rehber ön koşul, komut ve sınırlarıyla birlikte tek chunk olarak embedding'lenir. Bölmek komutu koşullarından koparabileceği için otomatik parçalama yapılmadı. 12.000 karakteri aşan rehberler aktarım aracınca reddedilir. Uzun belge parçalama stratejisi değerlendirilmemiştir.

## Dokuzuncu rehber: Oracle sorgu dönüşümleri (12 Kasım 2026)

- Kaynak: Oracle 19c SQL Tuning Guide, Query Transformations (OR expansion, view merging, predicate pushing, subquery unnesting); kayıt `oracle:19c:tgsql:query-transformations` (dosya telif nedeniyle Git dışında). Önceki 454 kayıt/chunk değişmedi, toplam 455. Kendi vektörüyle ilk üçte bulundu.
- Kayıt hazırlanırken sayfa özetleyicisinin verdiği ipucu (hint) adları (USE_CONCAT, NO_MERGE, PUSH_PRED, NO_UNNEST, NO_QUERY_TRANSFORMATION vb.) kaynak HTML'inde bulunamadı; kayda konmadı. Kayıt doğrudan sayfa metnindeki dört alt bölüme dayandırıldı.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı (ikinci sırada erişim yolları rehberi de arama sonucunda geldi). Yanıt subquery unnesting ve view merging'i doğru açıkladı, koşulları (aynı satırlar, AVG gibi toplama, maliyet/geçerlilik) belirtti, "plan SQL'den farklı olması tek başına sorun değil, hangi dönüşümün uygulandığı planda incelenmeli" sınırını korudu. Süre 12,9 sn.
- Elle değerlendirme: Kaynakta olmayan komut veya ipucu adı uydurulmadı; belirli sorguyu hızlandırma iddiası yok.
- Gerçek Oracle ortamında çalıştırılmadı; `execution_tested=false`.

## Onuncu rehber: Oracle Real-Time SQL Monitoring (12 Kasım 2026)

- Kaynak: Oracle 19c SQL Tuning Guide, Monitoring Database Operations; kayıt `oracle:19c:tgsql:real-time-sql-monitoring` (dosya telif nedeniyle Git dışında). Önceki 455 kayıt/chunk değişmedi, toplam 456. Kendi vektörüyle ilk üçte bulundu. Kayıt, sayfanın indirilen metninden doğrudan okunarak hazırlandı; 5 saniye eşiği, STATISTICS_LEVEL, /*+ MONITOR */, Tuning Pack ve CONTROL_MANAGEMENT_PACK_ACCESS ifadeleri sayfada doğrulandı.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt plan adımı başına süre/CPU/okuma-yazma/I/O ölçümlerini, V$SQL_MONITOR ve V$SQL_PLAN_MONITOR görünümlerini, otomatik izleme koşullarını ve kaynaktaki örnek çağrıyı doğru aktardı; Tuning Pack nedeniyle ek lisans gerekebileceğini ve lisansın ortamda doğrulanması gerektiğini belirtti. Süre 11,5 sn.
- Elle değerlendirme: Kaynakla çelişen veya kayıtta olmayan komut görülmedi; sorguyu hızlandırma iddiası yok. Kaynak sayfa REPORT_SQL_MONITOR için hem DBMS_SQL_MONITOR hem DBMS_SQLTUNE adını geçirir; kayıt yalnız sayfadaki örnek çağrıyı verir, hangisinin doğru olduğu belirlenmedi.
- Gerçek Oracle ortamında çalıştırılmadı; `execution_tested=false`.

## Oracle optimizasyon rehberleri özeti

Test raporundaki 5 Oracle optimizasyon sorusu için kaynak konular: EXPLAIN PLAN ile tahmini plan, erişim yolları, optimizer istatistikleri, sorgu dönüşümleri ve Real-Time SQL Monitoring (5 rehber). Rehberler test konularına bakılarak seçilmiştir; sonuçlar bu seçimden iyimser etkilenebilir. Tablespace ve RMAN rehberleri sonraki adımdır.

## On birinci rehber: Oracle tablespace alanı (12 Kasım 2026)

- Kaynak: Oracle 19c Administrator's Guide, Managing Tablespaces; kayıt `oracle:19c:admin:tablespace-space-and-growth` (dosya telif nedeniyle Git dışında). Önceki 456 kayıt/chunk değişmedi, toplam 457. Kendi vektörüyle ilk üçte bulundu. Kayıt, sayfanın indirilen metninin ilgili alt bölümleri doğrudan okunarak hazırlandı.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. İkinci kullanılan kaynak mevcut bir Stack Exchange kaynaklı kayıttır (`dba:q260240:a260244`); yanıttaki "hangi segmentler yer kullanıyor, kullanıcıların varsayılan tablespace/quota ayarları" önerisi bu kayıttan geldi (kayıt metni doğrulandı), rehberden değil. Yanıt boş alan ve veri dosyası sorgularını, ADD DATAFILE komutunu, bigfile'a ADD DATAFILE verilmemesi uyarısını, "depolama/yapılandırmayı değiştirir, üretimde önce test edin" sınırını ve DBA onayını aktardı. Süre 12,2 sn.
- Elle değerlendirme: Kaynakla çelişen komut görülmedi. "Disk alanı ve DBA onayı" uyarısı kaynakta bu bölümde yok, rehber kaydındaki bize ait nottur ve yanıtta öyle ayrıştırılmadı.
- Gerçek Oracle ortamında çalıştırılmadı; `execution_tested=false`.

## On ikinci rehber: Oracle RMAN yedek raporlama (12 Kasım 2026)

- Kaynak: Oracle 19c Backup and Recovery User's Guide, Reporting on RMAN Operations; kayıt `oracle:19c:bradv:rman-backup-reporting` (dosya telif nedeniyle Git dışında). Önceki 457 kayıt/chunk değişmedi, toplam 458. Kendi vektörüyle ilk üçte bulundu. Kayıt, sayfanın indirilen metninin ilgili bölümleri doğrudan okunarak hazırlandı.
- Kapsam sınırı: Rehber yalnız yedeklerin raporlanmasıdır (LIST BACKUP SUMMARY, REPORT NEED BACKUP, REPORT OBSOLETE, REPORT UNRECOVERABLE). Yedek alma, geri yükleme (restore) ve kurtarma (recovery) rehberleri eklenmemiştir; proje isterindeki "backup-restore" maddesi yalnız raporlama tarafıyla karşılanmaktadır.
- Doğal dil kontrolü (oracle_db modu, rehber ifadelerini kopyalamayan soru): beklenen kaynak ilk sırada ve yanıtta kullanıldı. Yanıt dört raporlama komutunu, REPORT NEED BACKUP'ın saklama politikası NONE iken çalışmadığını ve CROSSCHECK'in depo durumunu güncellediği için salt rapor olmadığını doğru aktardı; silme kararı için DBA onayını önerdi. Süre 12,8 sn.
- Elle değerlendirme: Kaynakla çelişen komut görülmedi. "LIST ve REPORT komutları yedek silmez" ifadesi kaynakta bu sözlerle yazmaz; kaynak bu komutları raporlama komutları olarak anlatır, sonuç bu tanımdan çıkarımdır. "DBA onayı" ifadesi kaynak değil, rehber kaydındaki bize ait nottur.
- Gerçek Oracle ortamında çalıştırılmadı; `execution_tested=false`.

## Rehber envanteri (12 Kasım 2026)

Bilgi tabanı 458 kayıt/chunk. Yeni resmî rehberler: Windows 5 (AD çoğaltma raporu, domain join DNS, IIS 403.14, hesap kilitlenmesi/EventCombMT, IIS Event 5013), Oracle 7 (EXPLAIN PLAN, erişim yolları, optimizer istatistikleri, sorgu dönüşümleri, Real-Time SQL Monitoring, tablespace alanı, RMAN raporlama). Rehberlerin hiçbiri gerçek AD, IIS veya Oracle ortamında çalıştırılmadı.
