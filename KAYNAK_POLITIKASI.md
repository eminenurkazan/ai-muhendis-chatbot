# Resmî rehber kaynak politikası

Tarih: 12 Kasım 2026. Bu belge, bilgi tabanına eklenecek resmî işlem rehberlerinin (`documentation` / `procedure`) hangi kaynaklardan, hangi koşullarla alınacağını belirler. Mevcut iki rehber ([ilk aktarım](RESMI_REHBER_ILK_AKTARIM.md)) bu kurallara göre hazırlanmıştır. Komut ve işlem rehberleri yalnız bu belgedeki kaynaklardan eklenir.

## 1. İzinli kaynaklar

| Kaynak | Alan | Kullanım | Lisans durumu |
|---|---|---|---|
| Microsoft Learn: Windows Server Troubleshooting (`learn.microsoft.com/en-us/troubleshoot/windows-server/`) | `windows_server` | AD, DNS, IIS, ağ ve sunucu sorun giderme | Sayfanın kaynak deposundaki LICENSE dosyasına göre belirlenir (şimdiki kayıt: CC-BY-4.0) |
| Microsoft `SupportArticles-docs` deposu (GitHub) | `windows_server` | Yukarıdaki makalelerin Markdown kaynağı; değişmez sürüm/commit alınabilir | Deponun LICENSE dosyası okunur ve kayda yazılır |
| Microsoft Learn: Windows/PowerShell belgeleri (ör. `Get-WinEvent`, `wevtutil`) | `windows_server` | Event Log analizi | Sayfa başına kontrol edilir; doğrulanmadan eklenmez |
| Oracle Database 19c: SQL Tuning Guide, Administrator's Guide, Backup and Recovery guide (`docs.oracle.com/en/database/oracle/oracle-database/19/`) | `oracle_db` | SQL optimizasyonu, tablespace, yedekleme/kurtarma | Açık lisans **varsayılmaz**; Oracle telif hakkı geçerlidir |

Listede olmayan kaynak (blog, forum, üçüncü taraf eğitim sitesi, model çıktısı) rehber olarak eklenmez. Yeni bir kaynak gerekirse önce bu tabloya eklenir ve lisansı yazılır.

Stack Exchange ve Mendeley kayıtları ayrı bir süreçtir ([UZMANLIK_VERILERININ_KULLANIMI.md](UZMANLIK_VERILERININ_KULLANIMI.md)); bu belgenin kapsamı dışındadır.

## 2. Lisansa göre davranış

- **CC-BY-4.0 (Microsoft):** Türkçe özet veya uyarlama yapılabilir. Yazar, kaynak bağlantısı, lisans ve lisans bağlantısı kayıtta tutulur; içeriğin uyarlandığı belirtilir. Lisans bilgisi her sayfa için ilgili depodan okunur; başka sayfa için varsayılmaz.
- **Oracle:** Oracle belgelerinde açık lisans yoktur. Oracle'ın yasal bildirimi, lisans sözleşmesi veya yasanın izin verdiği haller dışında belgenin herhangi bir bölümünün kullanılmasını, kopyalanmasını, çevrilmesini, değiştirilmesini ve dağıtılmasını yasaklar ([bildirim](https://docs.oracle.com/global_resources/cpyr.htm)). 19c rehberlerinin kendi bildirim sayfası doğrulanamadı; bu belge hukuki görüş değildir. Bu nedenle:
  - **Oracle rehber kayıtları depoya konmaz.** `data_sources/official_guides/oracle_*.json` `.gitignore` içindedir; kayıtlar yalnız yerel veritabanında ve yerel dosyada tutulur. Kaynak kopyaları zaten `outputs_local/` altındadır.
  - **Olgu temelli kısa kayıt:** Metin çevrilmez veya cümle cümle özetlenmez. Kayıt, belgenin bildirdiği olguları kendi ifademizle verir: komut veya paketin ne yaptığı, ön koşul/yetki, sınır. Bölüm yapısı ve örnek cümleler taklit edilmez.
  - **Komut:** Çalışmak için gereken en kısa, genel sözdizimi biçimi kullanılır. Belgedeki örnek tablo, örnek veri ve örnek çıktı bire bir alınmaz; gerekirse genel yer tutucularla (ör. `<tablo_adı>`) yazılır.
  - **Atıf:** Kaynak bağlantısı, bölüm adı ve sürüm (ör. 19c) kayıtta kalır. `license` alanına "Oracle documentation copyright; açık lisans varsayılmadı" yazılır. CC-BY lisansı Oracle içeriğine uygulanmaz.
  - **Uzunluk:** Kayıt kısa tutulur (yaklaşık 1500 karakter altı, bir komut/kavram odağı).
- Lisansı belirlenemeyen sayfa eklenmez.

## 3. Kapsam kuralları

1. **Dar kapsam:** Bir rehber tek bir işlem veya tanı akışını kapsar. Belgenin tamamı yüklenmez.
2. **Tek chunk:** Ön koşul, yetki, komut, beklenen çıktı ve sınırlar tek parçada kalır. Rehber 12.000 karakteri aşıyorsa daraltılır; otomatik bölme yapılmaz.
3. **Tanı önceliği:** İlk tercih okuma/raporlama/teşhis adımlarıdır. Veri silen, yapılandırmayı değiştiren, sunucuyu yeniden başlatan veya yedeği silen işlemler eklenmez. Gerekiyorsa yalnız kaynakta belirtilen uyarıyla ve açıkça "değişiklik yapar" notuyla eklenir.
4. **Komut doğruluğu:** Komut zorunlu değildir; proje isteri "teknik komutlar ve çözüm adımları" olduğundan yalnız çözüm adımı içeren rehber de eklenebilir (`commands` boş liste). Komut varsa kaynak sayfada bire bir bulunmalıdır. Eksik komut, parametre veya örnek çıktı modele tamamlatılmaz, bizim tarafımızdan uydurulmaz.
5. **Çalıştırılmadı:** Komutlar gerçek AD, IIS veya Oracle ortamında denenmedikçe `execution_tested=false` kalır. Üretimde işe yaradığı iddia edilmez.
6. **Sürüm:** Ürün ve sürüm bilgisi kayda yazılır (ör. Oracle 19c, Windows Server sürümü). Sürümü belirsiz içerik eklenmez.
7. **Tekrar önleme:** Aynı konuyu iki kez ayrı rehber olarak ekleme. Aynı kimlikle farklı içerik üzerine yazılmaz.

## 4. Rehber başına zorunlu alanlar

Kayıt `data_sources/official_guides/<ad>.json` dosyasındadır; alan adları mevcut iki kayıttaki şemayı izler.

| Alan | Gereksinim |
|---|---|
| `source_record_id` | Kararlı kimlik (ör. `microsoft:kbNNNN:konu`, `oracle:19c:bölüm:konu`) |
| `source_url`, `source_name`, `source_author` | Sayfanın kendi adresi ve yazarı |
| `source_version`, `source_snapshot_sha256` | Alınan içeriğin sürümü/özeti; özgün görüntü `outputs_local/` altında saklanır |
| `license`, `license_url` | Bölüm 2'ye göre |
| `domain`, `record_type` | `windows_server` veya `oracle_db`; `documentation` / `procedure` |
| `problem`, `product_version_environment` | Hangi soruna ve hangi ürün sürümüne yönelik |
| `commands`, `solution`, `limitations` | Kaynaktaki komutlar, adımlar, ön koşul/yetki ve kullanım sınırları |
| `resolution_confirmed`, `solution_scope` | Teşhis mi onarım mı; onarım doğrulanmış gibi işaretlenmez |
| `official_verification_status`, `official_context` | Resmî kaynağa dayandığı bilgisi |
| `transformation` | Ne değiştirildi (özet, çeviri, kısaltma) |
| `execution_tested` | Varsayılan `false` |
| `retrieved_at` | Alınma tarihi |

## 5. Eklemeden önce kontrol listesi

- [ ] Kaynak Bölüm 1 tablosunda.
- [ ] Sayfa açıldı, lisans ilgili LICENSE dosyasından veya sayfadan okundu ve kayda yazıldı.
- [ ] Varsa her komut kaynak sayfada bire bir bulundu (komut yoksa `commands` boş).
- [ ] Oracle ise: metin çevrilmedi/kopyalanmadı, olgu temelli ve kısa; örnek tablo/veri/çıktı bire bir alınmadı; kayıt dosyası `oracle_*.json` adıyla `.gitignore` kapsamında ve `git status` listesinde görünmüyor.
- [ ] Tanı odaklı; değişiklik yapan adım varsa açıkça işaretli.
- [ ] Tek chunk, 12.000 karakterin altında.
- [ ] Sürüm ve ön koşul/yetki yazıldı.
- [ ] `execution_tested=false`, onarım başarısı iddiası yok.
- [ ] `database.import_documentation` ile check, embed, import, verify adımları çalıştı; önceki kayıtlar değişmedi.
- [ ] Doğal dil kontrolü yapıldı ve sonucu kaydedildi.

## 6. Test sorularıyla ilişkisi

Rehberler, test sorularını yanıtlamak için ezberletilmez.

- Test soruları rehber cümleleri kopyalanmadan, farklı kullanıcı sorunları olarak yazılır.
- Test setine kaynağı bilgi tabanında olmayan en az 1–2 soru da konur; botun çekimserliği ölçülür.
- Test raporu, rehberlerin test konularına bakılarak seçildiğini açıkça belirtir; sonuçlar bütün uzmanlık alanı için başarı yüzdesi olarak sunulmaz.
- Komutlar gerçek ortamda çalıştırılmadığı için rapor yalnız "doğru kaynağı buldu ve belgelenmiş adımları sınırlarıyla aktardı" sonucunu iddia eder.
