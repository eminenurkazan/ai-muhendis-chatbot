# Model seçimi — Akıllı Servis Masası ve Sistem Uzmanı Chatbot

Proje: PRJIC20260201 · Tarih: 26 Kasım 2026 · Sürüm: 1.0

Model seçiminde iki koşul belirleyici oldu:
- **Geliştirme bilgisayarı:** 8 GB RAM, GPU yok.
- **Erişim:** Projeye ayrılmış ücretli bir LLM API bütçesi yok; yalnızca ücretsiz veya mevcut erişimler kullanılabilir.

Embedding ve yanıt modelleri bulutta çalışır. Bilgi tabanında 458 kayıt vardır (ticket, Windows/Oracle soru–cevapları, resmî rehberler). 26 Kasım 2026'daki 23 soruluk test sonuçları [TEST_RAPORU.md](TEST_RAPORU.md) içindedir.

## 1. Güncel karar

| Görev | Seçim | Çalışma yeri | Doğrulanan durum (26 Kasım 2026) |
|---|---|---|---|
| Soru ve kayıt embedding'i | Cloudflare Workers AI `@cf/baai/bge-m3` | Cloudflare | 1024 boyut; 458 chunk'ın hepsi bu modelle vektörleştirildi |
| Benzer kayıt arama | PostgreSQL + pgvector, cosine benzerliği | Docker içindeki yerel PostgreSQL | V3 testinde 20 ilgili sorunun beklenen kaynağı 20/20 ilk sırada bulundu |
| RAG yanıtı | `gpt-5.6-terra` | OpenAI Responses API | 20/20 beklenen kaynak kullanıldı; 3/3 kaynak dışı soruda yanıt uydurulmadı; ortalama 8,2 sn |
| Akışı birleştirme | LangChain Runnable zinciri | Yerel FastAPI uygulaması | Embedding, arama ve yanıt adımları ayrı ve asenkron çağrılır |
| Uygulama verileri | SQL Server 2022 Express, `ServisMasasiApp` | Windows üzerinde doğrudan kurulum | Kullanıcı, kalıcı sohbet, puan ve log tabloları API'ye bağlı; 88 gerçek SQL entegrasyon testi geçti |

LLM yanıt üretir; embedding modeli anlamsal arama için vektör üretir. Bu ayrımın sonuçları:
- LLM değişirse mevcut embedding'ler kullanılmaya devam edebilir.
- Embedding modeli veya boyutu değişirse bütün bilgi tabanının yeniden vektörleştirilmesi gerekir.

Geliştirme sırasında kullanılan kod asistanlarının modelleri, uygulamanın yanıt modeli değildir. Uygulamanın yanıt modeli `gpt-5.6-terra`'dır.

## 2. Değerlendirilen alternatifler

İsterler GPT-4, Llama 3 ve Mistral gibi seçenekleri örnek veriyor. Aşağıdaki karşılaştırma, bu proje koşullarına göre yapılmış bir **gerekçedir**. Alternatif modellerle aynı test setinde karşılaştırmalı ölçüm yapılmamıştır.

| Seçenek | Nasıl çalışırdı | Bu projede neden seçilmedi |
|---|---|---|
| GPT-4 sınıfı model, ücretli OpenAI API | Bulut, istek başına ücret | Projeye ayrılmış API bütçesi yok. Kalite açısından uygun olurdu; aynı Responses API akışı kullanıldığı için ileride model adı değiştirilerek geçilebilir. |
| Llama 3 (8B) yerel | Ollama veya llama.cpp ile CPU'da | 8 GB RAM'de 4-bit nicemlenmiş 8B model yaklaşık 5 GB bellek ister. Aynı bilgisayarda Docker/PostgreSQL, SQL Server, API ve Streamlit de çalıştığı için bellek yetersiz kalır. GPU olmadığından yanıt süresi uzar. |
| Mistral 7B yerel | Aynı | Llama 3 ile aynı bellek ve hız kısıtı. Türkçe yanıt kalitesi bu proje için ayrıca doğrulanmadı. |
| HuggingFace Inference (barındırılan açık modeller) | Bulut | Ücretsiz katman hız ve kota sınırlıdır. Kurumsal kullanım için ücretli uç nokta gerekir. |
| **`gpt-5.6-terra`, Sign in with ChatGPT** | Bulut, mevcut ChatGPT planı | **Seçildi:** ek ücret yok, ağırlık indirmek gerekmiyor, Türkçe kaynaklı yanıt ve JSON çıktı biçimi testlerde doğrulandı. Sınırları için bkz. Bölüm 4. |

Embedding için de benzer bir karşılaştırma yapıldı:
- **`multilingual-e5-small` (yerel):** İlk aday buydu. Küçük olmasına rağmen CPU ve RAM tüketimini geliştirme bilgisayarına yüklediği için çalışan sistemde kullanılmadı. Yedek seçenek olarak kalabilir; aynı indekste E5 ve BGE-M3 vektörleri karıştırılmaz.
- **OpenAI embedding API'si:** Ücretli olduğu için seçilmedi.

## 3. BGE-M3 seçiminin gerekçesi

`@cf/baai/bge-m3`, BAAI'nin HuggingFace'te yayımladığı açık bir modeldir ve Cloudflare Workers AI üzerinde çalışır. Model ağırlıkları geliştirme bilgisayarına yüklenmez.

- Çok dillidir. Türkçe sorularla İngilizce ticket ve soru–cevap kayıtlarını eşleştirme ihtiyacına uygundur. V3 testindeki sorular Türkçe, kaynakların çoğu İngilizcedir; beklenen kaynak 20/20 ilk sırada bulundu.
- 1024 boyutlu vektör üretir; PostgreSQL'de `vector(1024)` olarak saklanır.
- Bilgi tabanı vektörleri aktarım sırasında bir kez üretilir. Çalışan API her soru için yalnızca bir embedding üretir.
- Cloudflare ücretsiz kotası üretim kapasitesi garantisi değildir. Kota, gecikme ve bağlantı hataları uygulama günlüğündeki aşama süreleriyle izlenir.

## 4. GPT-5.6-Terra seçiminin gerekçesi ve sınırları

Uygulama, OpenAI'nin Sign in with ChatGPT akışıyla kullanıcının ChatGPT planına bağlanır. Model, hesabın model kataloğundan doğrulanır ve yanıt `POST /v1/responses` üzerinden alınır.

- İlk `gpt-5.6-sol` denemesinde `subscription_sharing_usage_limit_exceeded` hatası alındı. `gpt-5.6-terra` erişimi tamamlandı ve bütün RAG yanıtlarında kullanılıyor.
- Model bulutta çalıştığı için büyük LLM ağırlıkları bilgisayara indirilmez.
- İsteklerde `store:false` ve `stream:true` kullanılır. Tamamlanmamış akış başarı sayılmaz.
- Plan kotası sınırsız değildir. Uygulama kendiliğinden ücretli API'ye geçmez.
- **Sınır:** Bu erişim kişisel hesapla çalışan yerel bir kurulumdur. Şirketin bütün kullanıcılarına sunulacak uzaktan barındırılan bir sürümde erişim ve ödeme modeli ayrıca kararlaştırılmalıdır. Projenin kendi kullanıcı/JWT sistemi ChatGPT bağlantısından bağımsızdır.

## 5. Güvenlik ve gizli bilgiler

- Cloudflare API token'ı ve ChatGPT OAuth tokenları kaynak koda yazılmaz, terminalde gösterilmez ve Git'e eklenmez.
- Kimlik bilgileri proje klasörünün dışında, Windows kullanıcısına bağlı DPAPI korumasıyla saklanır. Başka bir Windows kullanıcısı veya bilgisayar bu dosyaları açamaz; yeni kurulumda giriş tekrarlanır.
- Sunucuya geçildiğinde yerel DPAPI dosyası taşınmaz; dağıtım ortamının secret yönetimi kullanılır.
- Token reddedilirse kayıt temizlenir. Geçici ağ hatasında geçerli kayıt korunur.
- Bilgi tabanı metinleri güvenilmeyen bağlam olarak işlenir. İçlerindeki talimatlar sistem yönergelerinin yerine geçmez.

## 6. Ölçülen sonuçlar

| Tarih | Bilgi tabanı | Sorular | Beklenen kaynak 1. sırada | Kaynak dışı doğru ret | Ort. süre | Belge |
|---|---|---|---|---|---|---|
| 9 Ekim | 20 ticket | 10 | 8/8 | 2/2 | 10,1 sn | [PILOT_API_VE_DEGERLENDIRME.md](PILOT_API_VE_DEGERLENDIRME.md) |
| 5 Kasım | 191 ticket | 10 | 8/8 | 2/2 | 9,3 sn | [DEGERLENDIRME_V2_SONUCU.md](DEGERLENDIRME_V2_SONUCU.md) |
| 26 Kasım | 458 kayıt | 23 | 20/20 | 3/3 | 8,2 sn | [TEST_RAPORU.md](TEST_RAPORU.md) |

26 Kasım testinde 23 yanıtın elle incelemesi: 22 uygun, 1 kısmen uygun, 0 uygunsuz. Kısmen uygun yanıt, kayıttaki bir öneriyi yapılan işlemle birleştiriyor. Windows/Oracle sonuçları, konulara göre seçilmiş resmî rehberlere dayandığı için iyimserdir. Yanıtlardaki komutlar gerçek ortamda çalıştırılmadı. Set 3 kez çalıştırıldı: arama ve kullanılan kaynaklar üç çalıştırmada da aynıydı; elle inceleme 22/23/22 uygun, ortalama süre 8,2/9,4/9,2 sn. Uygulama günlüğüne göre sürenin tamamına yakını model aşamasındadır (medyan 8,1 sn; embedding 0,29 sn, arama 0,06 sn). Üç tekrar istatistiksel bir başarı oranı değildir.

## 7. Açık kararlar

1. Kurum içi veya çok kullanıcılı dağıtım yapılacaksa LLM erişimi (ücretli API veya kurum hesabı), kapasite ve secret yönetimini netleştirmek.
2. Uzun belgeler eklenecekse chunk boyutunu ölçmek ve çoklu chunk stratejisini uygulamak.
3. Alternatif bir LLM'e geçiş değerlendirilirse aynı V3 soru setiyle karşılaştırmalı ölçüm yapmak.

## 8. Resmî kaynaklar

- [Cloudflare BGE-M3](https://developers.cloudflare.com/workers-ai/models/bge-m3/)
- [Cloudflare OpenAI uyumlu API uçları](https://developers.cloudflare.com/workers-ai/configuration/open-ai-compatibility/)
- [OpenAI Sign in with ChatGPT genel bakış](https://developers.openai.com/siwc/token-sharing-open-source)
- [OpenAI model kataloğu ve Responses API](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [OpenAI hesaplar ve oturumlar](https://developers.openai.com/siwc/token-sharing-open-source/profiles-and-sessions)
- [OpenAI önizleme sınırlamaları](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [Windows DPAPI](https://learn.microsoft.com/en-us/windows/win32/api/dpapi/nf-dpapi-cryptprotectdata)

İlgili tasarımlar: [ER_Taslagi.md](ER_Taslagi.md) ve [RAG_Akisi.md](RAG_Akisi.md).
