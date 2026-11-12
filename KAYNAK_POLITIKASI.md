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
- **Oracle:** Metin kopyalanmaz. Kayıt, kısa ve kendi cümlelerimizle yazılmış bir özettir. Belgelenmiş komut/SQL yalnız çalışmak için gerekli en kısa biçimde, bire bir ve kaynağa atıfla alınır. `license` alanına "Oracle documentation copyright; açık lisans varsayılmadı" yazılır. CC-BY lisansı Oracle içeriğine uygulanmaz.
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
- [ ] Oracle ise: metin kopyalanmadı, özet kendi cümlelerimizle yazıldı.
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
