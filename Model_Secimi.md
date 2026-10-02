# Model seçimi — Akıllı Servis Masası ve Sistem Uzmanı Chatbot

Proje: PRJIC20260201 · Tarih: 2 Ekim 2026 · Sürüm: 0.5

Model seçimi, 8 GB RAM ve GPU bulunmayan geliştirme bilgisayarının koşulları ile ücretsiz/var olan erişim seçenekleri dikkate alınarak yapılmıştır. Seçimler 10 ticketlık pilotta gerçek API çağrılarıyla doğrulanmıştır.

## 1. Güncel pilot kararı

| Görev | Seçim | Çalışma yeri | Doğrulanan durum |
|---|---|---|---|
| Soru ve ticket embedding'i | Cloudflare Workers AI `@cf/baai/bge-m3` | Cloudflare | 1024 boyutlu embedding alındı. |
| Benzer kayıt arama | Normalize vektörler + cosine benzerliği | Pilot Python uygulamasının belleği | Üç olumlu soruda beklenen ticket ilk sırada bulundu. |
| RAG yanıtı | `gpt-5.6-terra` | OpenAI Responses API | Kaynaklı Türkçe yanıt ve kapsam dışı soruda çekimserlik doğrulandı. |
| Gelecek vektör deposu | PostgreSQL + pgvector `vector(1024)` | Proje veritabanı | Tasarlandı; bağlantı henüz kurulmadı. |

LLM yanıt üretir; embedding modeli anlamsal arama için vektör üretir. LLM değişirse mevcut embedding'ler kullanılabilir. Embedding modeli veya boyutu değişirse bütün bilgi tabanı yeniden vektörleştirilir.

## 2. BGE-M3 seçiminin gerekçesi

`@cf/baai/bge-m3`, Cloudflare Workers AI üzerinde çalıştığı için model ağırlıkları geliştirme bilgisayarına yüklenmez. Bu seçim 8 GB RAM ve GPU bulunmayan bilgisayardaki yükü azaltır.

- Çok dilli kullanım, Türkçe sorularla İngilizce ticketları eşleştirme ihtiyacına uygundur.
- Model 1024 boyutlu vektör üretir.
- Pilot, 10 ticketı tek toplu istekte; her kullanıcı sorusunu ayrı bir istekte vektörleştirmiştir.
- Ticket vektörleri CSV değişmediği sürece yerel cache'den okunur. Böylece her çalıştırmada tekrar üretilmez.
- Cloudflare ücretsiz kotası ve servis erişimi üretim kapasitesi garantisi değildir. Kota, gecikme ve geçici bağlantı hataları izlenmelidir.

Yerel `multilingual-e5-small` ilk adaydı. Küçük boyutuna rağmen CPU ve RAM tüketimini geliştirme bilgisayarına yüklediği için çalışan pilotta BGE-M3 tercih edildi. E5 bir yedek seçenek olarak yeniden değerlendirilebilir; aynı indekste E5 ve BGE-M3 vektörleri karıştırılmaz.

## 3. GPT-5.6-Terra seçiminin gerekçesi

Yerel/açık kaynak prototip, OpenAI'nin Sign in with ChatGPT akışıyla kullanıcının uygun ChatGPT planına bağlanır. Model hesabın model kataloğundan doğrulanır ve yanıt `POST /v1/responses` üzerinden alınır.

- `gpt-5.6-sol` pilotunda `subscription_sharing_usage_limit_exceeded` hatası alındı.
- `gpt-5.6-terra` erişimi tamamlandı ve RAG yanıtlarında kullanıldı.
- Model bulutta çalıştığı için büyük LLM ağırlıkları bilgisayara indirilmez.
- İsteklerde `store:false` ve `stream:true` kullanılır; tamamlanmamış akış başarı sayılmaz.
- Plus plan kotası sınırsız değildir. Uygulama ücretli API'ye kendiliğinden geçmez.

Bu bağlantı yerel ve açık kaynak pilot için uygundur. Şirketin bütün kullanıcılarına sunulacak uzaktan barındırılan sürümde erişim ve ödeme modeli ayrıca kararlaştırılmalıdır. Projenin kendi kullanıcı/JWT sistemi, ChatGPT bağlantısından ayrı kalır.

## 4. Güvenlik ve gizli bilgiler

- Cloudflare API token'ı ve ChatGPT OAuth tokenları kaynak koda yazılmaz, terminal çıktısında gösterilmez ve Git'e eklenmez.
- Windows pilotunda kimlik bilgileri proje klasörünün dışında, mevcut Windows kullanıcısına bağlı DPAPI korumasıyla saklanır.
- Sunucuya geçildiğinde yerel DPAPI dosyası taşınmaz; dağıtım ortamının secret yönetimi kullanılır.
- Token reddedilirse kayıt temizlenir. Geçici ağ hatasında geçerli kayıt korunur.
- Ticket metinleri güvenilmeyen bağlam olarak işlenir; içlerindeki talimatlar sistem yönergelerinin yerine geçmez.

## 5. Pilot sonuçları ve sınırları

Chrome, yük dengeleyici ve Oracle sorularında beklenen kayıt ilk sırada bulunmuştur. Domates çorbası sorusunda Terra, aday ticketların ilgisiz olduğunu belirtmiş ve teknik çözüm uydurmamıştır. Oracle yanıtında `resolution_confirmed=false` bilgisi ve eksik SQL/cache ayrıntıları korunmuştur.

Bu dört deneme, entegrasyonun çalıştığını gösterir. Model kalitesini genellemek için yeterli değildir. Sonraki değerlendirmede arama başarısı ve oluşturulan yanıtın kaynak uyumu ayrı metriklerle ölçülecektir.

## 6. Sonraki kararlar

1. Uzun ticket ve dokümanlar için chunk boyutunu ölçmek.
2. pgvector üzerinde `vector(1024)` şemasını ve aramayı doğrulamak.
3. Windows Server ve Oracle kaynaklarını genişletmek.
4. Ayrı değerlendirme setinde arama ve yanıt kalitesini ölçmek.
5. Sunucu dağıtımı için LLM erişim ve secret yönetimi kararını netleştirmek.

## 7. Resmî kaynaklar

- [Cloudflare BGE-M3](https://developers.cloudflare.com/workers-ai/models/bge-m3/)
- [Cloudflare OpenAI uyumlu API uçları](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)
- [OpenAI Sign in with ChatGPT genel bakış](https://developers.openai.com/siwc/token-sharing-open-source)
- [OpenAI model kataloğu ve Responses API](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenAI hesaplar ve oturumlar](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [OpenAI önizleme sınırlamaları](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)

İlgili tasarımlar: [ER_Taslagi.md](ER_Taslagi.md) ve [RAG_Akisi.md](RAG_Akisi.md).

