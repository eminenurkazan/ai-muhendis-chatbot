# Model seçimi — Akıllı Servis Masası ve Sistem Uzmanı Chatbot

Proje: PRJIC20260201 · Tarih: 22 Ekim 2026 · Sürüm: 0.6

Model seçimi, 8 GB RAM ve GPU bulunmayan geliştirme bilgisayarının koşulları ile ücretsiz/var olan erişim seçenekleri dikkate alınarak yapılmıştır. Mevcut yerel pilotta 20 onaylı ticket ve PostgreSQL + pgvector içinde 20 arama chunk'ı vardır. Embedding ve yanıt modelleri bulutta çalışır. İlk düzenli 10 soruluk değerlendirme 9 Ekim'de yapılmış; modüler RAG akışı ve MSSQL altyapısı 22 Ekim'de ayrıca kontrol edilmiştir.

## 1. Güncel pilot kararı

| Görev | Seçim | Çalışma yeri | Doğrulanan durum |
|---|---|---|---|
| Soru ve ticket embedding'i | Cloudflare Workers AI `@cf/baai/bge-m3` | Cloudflare | 1024 boyut; 20 chunk'ın embedding'i PostgreSQL'e aktarıldı. |
| Benzer kayıt arama | PostgreSQL + pgvector, cosine benzerliği | Docker içindeki yerel PostgreSQL | API ilk üç adayı veritabanından getirir; 9 Ekim testinde beklenen kaynak ilk üçte 8/8 bulundu. |
| RAG yanıtı | `gpt-5.6-terra` | OpenAI Responses API | Kaynaklı Türkçe yanıt ve ilgili kaynak bulunmadığında çekimserlik doğrulandı. |
| Akışı birleştirme | LangChain Runnable zinciri | Yerel FastAPI uygulaması | Embedding, arama ve yanıt adımları ayrı modüllerden çağrılır. |
| Uygulama verileri | SQL Server 2022 Express, `ServisMasasiApp` | Windows üzerinde doğrudan kurulum; dosyalar D: üzerinde | Beş tablo ve kullanıcı/sohbet/mesaj veri erişim katmanı hazır; altı MSSQL entegrasyon testi geçti. API henüz sohbet geçmişini kaydetmez. |

LLM yanıt üretir; embedding modeli anlamsal arama için vektör üretir. LLM değişirse mevcut embedding'ler kullanılabilir. Embedding modeli veya boyutu değişirse bütün bilgi tabanı yeniden vektörleştirilir.

Geliştirme sırasında Codex'te seçilen asistan modeli, uygulamanın yanıt modeli değildir. Mevcut kodun yanıt modeli `gpt-5.6-terra` olarak kalır. İlk bellek içi arama denemesi tarihsel pilottur; çalışan API'nin veri kaynağı PostgreSQL'dir.

## 2. BGE-M3 seçiminin gerekçesi

`@cf/baai/bge-m3`, Cloudflare Workers AI üzerinde çalıştığı için model ağırlıkları geliştirme bilgisayarına yüklenmez. Bu seçim 8 GB RAM ve GPU bulunmayan bilgisayardaki yükü azaltır.

- Çok dilli kullanım, Türkçe sorularla İngilizce ticketları eşleştirme ihtiyacına uygundur.
- Model 1024 boyutlu vektör üretir.
- İlk 10 ticketın hazır vektörleri `database.import_pilot` ile; ayrıca incelenen 10 ticketın vektörleri `database.import_reviewed` ile PostgreSQL'e aktarılmıştır. Kısa kayıt başına bir chunk vardır.
- Yerel embedding cache'i veri hazırlama ve aktarım adımlarında kullanılır. Çalışan API her soru için bir embedding üretir ve kayıt vektörlerini PostgreSQL'de arar; tüm ticketları her istekte yeniden vektörleştirmez.
- Cloudflare ücretsiz kotası ve servis erişimi üretim kapasitesi garantisi değildir. Kota, gecikme ve geçici bağlantı hataları izlenmelidir.

Yerel `multilingual-e5-small` ilk adaydı. Küçük boyutuna rağmen CPU ve RAM tüketimini geliştirme bilgisayarına yüklediği için çalışan pilotta BGE-M3 tercih edildi. E5 bir yedek seçenek olarak yeniden değerlendirilebilir; aynı indekste E5 ve BGE-M3 vektörleri karıştırılmaz.

## 3. GPT-5.6-Terra seçiminin gerekçesi

Yerel/açık kaynak prototip, OpenAI'nin Sign in with ChatGPT akışıyla kullanıcının uygun ChatGPT planına bağlanır. Model hesabın model kataloğundan doğrulanır ve yanıt `POST /v1/responses` üzerinden alınır.

- İlk `gpt-5.6-sol` denemesinde `subscription_sharing_usage_limit_exceeded` hatası alındı. Bu tarihsel sonuç, güncel hesap erişimi hakkında yeniden yapılmış bir ölçüm değildir.
- `gpt-5.6-terra` erişimi tamamlandı ve RAG yanıtlarında kullanıldı.
- Model bulutta çalıştığı için büyük LLM ağırlıkları bilgisayara indirilmez.
- İsteklerde `store:false` ve `stream:true` kullanılır; tamamlanmamış akış başarı sayılmaz.
- Plus plan kotası sınırsız değildir. Uygulama ücretli API'ye kendiliğinden geçmez.

Bu projede doğrulanan kullanım, kişisel hesapla çalışan yerel pilottur. Şirketin bütün kullanıcılarına sunulacak uzaktan barındırılan sürümde erişim ve ödeme modeli ayrıca kararlaştırılmalıdır. Projenin kendi kullanıcı/JWT sistemi, ChatGPT bağlantısından ayrı kalır.

## 4. Güvenlik ve gizli bilgiler

- Cloudflare API token'ı ve ChatGPT OAuth tokenları kaynak koda yazılmaz, terminal çıktısında gösterilmez ve Git'e eklenmez.
- Windows pilotunda kimlik bilgileri proje klasörünün dışında, mevcut Windows kullanıcısına bağlı DPAPI korumasıyla saklanır.
- Sunucuya geçildiğinde yerel DPAPI dosyası taşınmaz; dağıtım ortamının secret yönetimi kullanılır.
- Token reddedilirse kayıt temizlenir. Geçici ağ hatasında geçerli kayıt korunur.
- Ticket metinleri güvenilmeyen bağlam olarak işlenir; içlerindeki talimatlar sistem yönergelerinin yerine geçmez.

## 5. Pilot sonuçları ve sınırları

9 Ekim değerlendirmesi, 20 kısa ticket üzerinde önceden hazırlanmış 8 ilgili ve 2 kaynakta karşılığı bulunmayan soruyu kapsar. İlgili soruların beklenen kaynakları ilk üçte **8/8**, ilk sırada da **8/8** bulunmuştur. Kaynakta karşılığı olmayan iki soruda çekimserlik kontrolü **2/2** geçmiştir. On yanıtın ortalama süresi **10089 ms** (yaklaşık 10,1 saniye) olarak kaydedilmiştir.

Yanıtlar onaylı ticket özetleriyle elle karşılaştırılmış; bu küçük sette kaynak dışı teknik talimat tespit edilmemiştir. Özgün yorumlara ikinci bir tam denetim yapılmamıştır. Otomatik testin kaynak kimliği kontrolü tek başına yanıtın doğruluğunu kanıtlamaz. Soru bazında sonuçlar [PILOT_API_VE_DEGERLENDIRME.md](PILOT_API_VE_DEGERLENDIRME.md) içindedir.

22 Ekim'deki modül ayrımından sonra üç çevrimdışı regresyon testi ve seçilmiş gerçek API kontrolleri yapılmıştır. UAT sorusunda kaynak ve ortam sınırı, BitLocker sorusunda kaynak yetersizliği ve boş soruda HTTP 422 davranışı kullanıcı tarafından doğrulanmıştır. Bu kontroller, 9 Ekim'deki on soruluk değerlendirmenin yeniden çalıştırılması değildir.

Sonuçlar mevcut 20 kısa kayıt ve seçilmiş sorularla sınırlıdır. Windows Server/Oracle için ayrı uzmanlık prompt'ları `2026-10-22-v1` sürümüyle eklendi; altı yeni çevrimdışı test ve iki seçilmiş gerçek API kontrolü geçti. Windows modunda BitLocker sorusu kaynak yokluğu nedeniyle yanıtsız bırakıldı (9873 ms); Oracle modunda sequence sorusu `1010047.0` kaynağıyla sınırları korunarak yanıtlandı (11674 ms). Daha geniş kaynak kapsamı, uzun belgeler, çoklu chunk ve çok kullanıcılı yük henüz doğrulanmadı. Prompt seçimi Terra modelini veya mevcut kaynak havuzunu değiştirmez. Ayrıntılar [PROMPT_YAPISI.md](PROMPT_YAPISI.md) içindedir.

## 6. Sonraki kararlar

1. Uzun ticket ve dokümanlar için chunk boyutunu ölçmek.
2. Windows Server ve Oracle için hedef sürümleri ve kaynakları belirlemek; eklenen uzmanlık prompt'larını gerçek yanıtlarla test etmek.
3. Daha geniş ve farklı ifade edilmiş sorularla arama başarısını ve yanıtın kaynak uyumunu ayrı ölçmek.
4. MSSQL veri erişim katmanını doğrulanmış kullanıcı kimliği ve kullanıcıya ait sohbet geçmişiyle API'ye bağlamak.
5. Yerel gösterimin ötesine geçilecekse LLM erişimi, kapasite ve secret yönetimi kararını netleştirmek.

## 7. Resmî kaynaklar

- [Cloudflare BGE-M3](https://developers.cloudflare.com/workers-ai/models/bge-m3/)
- [Cloudflare OpenAI uyumlu API uçları](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)
- [OpenAI Sign in with ChatGPT genel bakış](https://developers.openai.com/siwc/token-sharing-open-source)
- [OpenAI model kataloğu ve Responses API](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenAI hesaplar ve oturumlar](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [OpenAI önizleme sınırlamaları](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)

İlgili tasarımlar: [ER_Taslagi.md](ER_Taslagi.md) ve [RAG_Akisi.md](RAG_Akisi.md).

