# İlk resmî işlem rehberi — 12 Kasım 2026

Microsoft KB2498185 makalesinin yalnız Active Directory çoğaltma hatalarını CSV ile raporlama alt kapsamı eklendi. Yeni kayıt `documentation`, Windows Server alanında `procedure` olarak saklanır. Bu bir tanı prosedürüdür; onarım değildir.

- Kaynak: https://learn.microsoft.com/en-us/troubleshoot/windows-server/active-directory/diagnose-replication-failures
- Yazar: Microsoft. İçerik lisansı: CC-BY-4.0; kaynak deposunun LICENSE dosyası rehberde bağlantılıdır. Türkçe özet/uyarlama olduğu belirtilir.
- Kayıt: `data_sources/official_guides/microsoft_ad_replication.json`.
- Özgün Markdown görüntüsü: `outputs_local/official_guide_first_20261112/source.md`; SHA-256 değeri kayıtta korunur.
- Ön koşul, yetki, komut, beklenen rapor ve sınırlamalar tek kısa chunk içinde tutulur. 12.000 karakter üstü rehberler bu ilk araç tarafından reddedilir; otomatik ve bağlam kaybettiren parçalama yapılmaz.
- `database.import_documentation` check/embed/import/verify adımlarını destekler; `--record` ve `--cache` yolları açıkça belirtilir. Mevcut QA aktarımı değiştirilmez. Farklı içerikle aynı kimliğin üzerine yazılmaz.
- Mevcut 446 kayıt ve chunk değişmeden kaldı; bir rehber eklendi, toplam 447 kayıt/chunk oldu. MSSQL tabloları değiştirilmedi.
- Rehber hem genel aramada hem Windows Server modunda aranabilir; Oracle moduna girmez. Kaynak atfı, lisans ve çalıştırılarak test edilmediği bilgisi korunur.
- Prompt documentation/procedure kayıtları için belgeli komutları ön koşullarıyla birlikte Markdown içinde aktarmaya yönlendirilir. QA açıklama özetlerinden komut üretmeme kuralı korunur.
- Komutlar bu bilgisayarda veya gerçek AD ortamında çalıştırılmadı. Kaynakta bulunuş, aktarım ve arama/yanıt davranışı kontrol edildi; üretim başarısı iddia edilmez.

Kodun devreye girmesi için API ve Streamlit süreçleri yeniden başlatılmalıdır. API için `powershell.exe -NoProfile -ExecutionPolicy Bypass -File D:\ai-muhendis-chatbot\start_api.ps1` kullanılır. Arayüz `python -m streamlit run streamlit_app.py` ile başlatılır.

Bu aşamada yalnız ilk Windows rehberi eklendi. Oracle ve diğer rehberler kapsam dışıdır. Doğal dil kontrol sonucu yerel `answer_check.json` dosyasındadır; bir örnek tüm uzmanlık alanının başarı ölçümü değildir.
