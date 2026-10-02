# Model seçimi ve Plus hesabıyla erişim değerlendirmesi

Proje: PRJIC20260201 · Tarih: 2 Ekim 2026 · Sürüm: 0.4

Şirketin API bütçesi ve anahtar desteği henüz öğrenilemedi. Kullanıcının kararıyla geliştirme, şirketten bütçe gelmediği varsayımıyla ilerleyecek. Kullanıcının mevcut ChatGPT Plus hesabından yararlanma yolu da değerlendirmeye alındı. LLM erişimi henüz kesinleştirilmedi; önceki Groq seçimi, entegrasyon şartına uyumu kesinleşmiş bir karar olarak kabul edilmiyor.

İlk değerlendirilecek yol, uygun yerel prototipte OpenAI'nin resmî Sign in with ChatGPT akışıyla Plus plan kullanımını Responses API'ye bağlamaktır. Kullanıcının hesabında erişim ve ilk çağrı henüz doğrulanmadı. Embedding başlangıç seçimi, yerel CPU üzerinde multilingual-e5-small ve 384 boyut olarak korunuyor.

## 1. Güncel karar durumu

| Görev | Başlangıç kararı veya aday | Çalışma yeri | Durum |
|---|---|---|---|
| Ticket alanlarını çıkarma ve RAG yanıtı | Plus plan kullanımıyla OpenAI Responses API; model adayı `gpt-6.1-sol` | OpenAI sunucuları; uygulama yerel prototip | Uygunluk, hesap model kataloğu ve pilot bekleniyor; nihai model seçilmedi |
| Alternatif LLM erişimi | `openai/gpt-oss-120b` modelini Groq ücretsiz planında kullanma | GroqCloud; Hugging Face istemcisiyle | Alternatif; belgedeki LLM entegrasyon şartının kabulü kesin değil |
| Soru ve chunk embedding'leri | `intfloat/multilingual-e5-small` | Kullanıcının bilgisayarında CPU | Seçildi; kurulum, süre ve bellek ölçümü bekleniyor |
| Vektör boyutu | 384 | PostgreSQL + pgvector içinde `vector(384)` | Fiziksel şema uygulanacak |

LLM metin üretir; embedding modeli arama vektörünü üretir. LLM değişikliği tek başına embedding'leri yenilemeyi gerektirmez. Embedding modeli değişirse vektörler yeniden oluşturulur.

## 2. Plus hesabının resmî uygulama entegrasyonu

Standart OpenAI API anahtarıyla kullanım ayrı faturalandırılır; Plus sahibi olmak, bu standart anahtarın harcamalarının abonelikten karşılandığı anlamına gelmez.

Güncel OpenAI belgelerinde ayrıca Sign in with ChatGPT kapsamında ChatGPT plan kullanımı vardır. Uygun açık kaynak veya yerel uygulama, kullanıcının OAuth iznini alıp plan kotasıyla desteklenen Responses API istekleri gönderebilir. Resmî örnek, uygun Plus veya Pro planıyla yerel bir uygulama kullanımını açıklar.

Bu akışta model kataloğu ve yanıt üretimi için resmî `https://api.openai.com/v1` uçları kullanılır. Kimlik doğrulama, ayrı ücretli API anahtarı yerine bu bağlantıda alınan OAuth erişim tokenıyla yapılır. Mevcut Plus kotası kullanılır; sınırsız kullanım varsayılmaz. Model OpenAI sunucularında çalışacağı için bilgisayara büyük LLM ağırlıkları yüklenmez.

Yerel prototip için bu yol öncelikle değerlendirilecek. Model adayı `gpt-6.1-sol` olsa da gerçek model kimliği, giriş yapılan hesabın kataloğundan seçilecek. Yerel veya açık kaynak uygulama koşullarının şirket tarafından sunulacak uzaktan barındırılan uygulamada da geçerli olduğu varsayılmaz; bu kapsamın erişim koşulları ayrıca değerlendirilir. Kullanıcının kişisel Plus planı, bütün şirket kullanıcıları için sınırsız ortak model hesabı olarak tasarlanmaz.

Uygulamanın proje belgesinde istenen kendi JWT kullanıcı yönetimi korunur. ChatGPT bağlantısı model erişimi için ayrı bir bağlantıdır; uygulamanın kendi kayıt/giriş ve sohbet sahipliği kontrollerinin yerine geçirilmez. Yerel prototipte kullanılacak ChatGPT hesabı ve bağlantısı görünür ve doğrulanmış olmalıdır.

## 3. Proje isterlerine uyum değerlendirmesi

Belgedeki ifade: “HuggingFace veya OpenAI API entegrasyonu.”

| Seçenek | Entegrasyon açısından değerlendirme |
|---|---|
| Standart OpenAI API, ayrı API anahtarıyla | Doğrudan OpenAI API kullanımıdır; ayrı API bütçesi gerektirir. |
| Uygun uygulamada Plus plan kullanımıyla resmî Responses API | Teknik olarak resmî OpenAI API entegrasyonudur. Yerel prototip için adaydır; hesap ve uygulama uygunluğu doğrulanmalıdır. |
| Hugging Face'den indirilen yerel modeller | Hugging Face model entegrasyonudur. Embedding seçimimiz bu yolu kullanır. LLM'in yerel çalışabilirliği ve kalitesi ayrı ölçülür. |
| Groq'ta GPT-OSS-120B; Hugging Face istemcisiyle | OpenAI tarafından yayımlanan modeli Groq çalıştırır; OpenAI API hizmeti değildir. HF istemcisi ve sağlayıcı entegrasyonu kullanılır, fakat bu yolun belgeyi hazırlayan kişinin LLM entegrasyon beklentisini karşıladığı kesin kabul edilmez. |

OpenAI modelini başka sağlayıcıda çalıştırmak, OpenAI API hizmetini kullanmakla aynı şey değildir. Hugging Face SDK'sı kullanılması da çıkarım hizmetinin Groq'ta çalıştığı gerçeğini değiştirmez. Groq seçeneği bu yüzden kesinleşmiş teslim mimarisi olarak yazılmaz.

## 4. Erişim maliyeti ve kota

Plus plan kullanımında mevcut aboneliğin desteklenen kotası tüketilir. Hesaba özel erişim, kullanılabilir modeller ve limitler girişten sonra doğrulanır; ek kredi veya ücretli API kullanımı bu başlangıç planının parçası değildir.

Groq alternatifi değerlendirilecek olursa ücretsiz plan koşulları uygulanır. 2 Ekim 2026 tarihinde açılan genel kota tablosunda GPT-OSS-120B için 30 istek/dakika, 1.000 istek/gün, 8.000 token/dakika ve 200.000 token/gün belirtilir. Hesaba özel limitler farklı olabilir ve değişebilir. Ücretsiz kullanım, sınırsız veya üretim kapasitesi garantisi değildir.

Hugging Face'in standart yönlendirilmiş API kredisi de sınırsız ücretsiz erişim olarak varsayılmaz: güncel dokümanda ücretsiz hesaplar için aylık 0,10 USD kredi belirtilir. Groq'a doğrudan sağlayıcı anahtarıyla yapılan HF istemci çağrısı ile HF kredisi kullanan yönlendirme ayrı erişim biçimleridir.

Henüz model çağrısı veya gerçek tüketim ölçümü yoktur. Başlangıçta kullanılacak içerik, seçilmiş açık ticket ve uzman kaynak örnekleridir.

## 5. Embedding gerekçesi ve ayarları

Multilingual-E5-small, MIT lisanslı ve Türkçe ile İngilizceyi kapsayan çok dilli bir embedding modelidir. Model kartında 384 boyutlu vektör ve en fazla 512 token giriş sınırı belirtilir. Türkçe sorular ile İngilizce kaynakları eşleştirme ihtiyacı için seçildi; bu dil çiftindeki arama başarısı pilotta ölçülecek.

Yerel CPU kullanımı, embedding API ücretini ve harici kota bağımlılığını kaldırır. Küçük pilotta uygulanabilir olduğunu düşünüyoruz; i5-1155G7 işlemci ve 8 GB RAM'li bilgisayardaki süre ve bellek tüketimi ölçülmeden hız garantisi verilmez. Model bir kez indirilip tekrar kullanılacak.

- Sorulara `query: `, bilgi parçalarına `passage: ` ön eki eklenecek.
- Vektörler normalize edilecek; başlangıçta cosine benzerliği kullanılacak.
- E5 tokenizer'ına göre 256–384 tokenlık parçalar ve gerekirse yaklaşık 50 token örtüşme denenecek.
- Ön ek ve özel tokenlar dahil giriş 512 tokenı aşmayacak. Uzun içerik sessiz kesme yerine anlamı korunarak yeniden bölünecek.
- Kısa ticketlarda sorun, çözüm ve sonuç aynı chunk'ta kalabilir. SQL/PowerShell kodu ve çözüm sınırlamaları korunacak.
- Model kimliği ve revizyonu kaydedilecek; aynı aramada tek model ve boyut kullanılacak.

Plus için belgelenen plan kullanım yolu Responses API'ye yöneliktir. OpenAI embedding API çağrılarının aynı abonelik kotasından karşılanacağı varsayılmaz; bu nedenle yerel E5 planı korunur.

## 6. İlk doğrulama ve RAG pilotu

1. Yerel ortam ve 10 ticket örneğinin sorun/çözüm/sonuç alanlarını okuyan kod doğrulanır.
2. Plus bağlantısı için yerel uygulama uygunluğu, resmî OAuth akışı, izin ve hesap model kataloğu kontrol edilir. Kimlik bilgileri sohbet içinde paylaşılmaz veya Git'e eklenmez.
3. Tek açık örnekle resmî Responses API çağrısı denenir. Kullanım kotası, yanıt süresi ve model kimliği kaydedilir. Bu akışta HTTP istekleri `store:false` ve `stream:true` kullanır; bağlam her istekte `input` dizisiyle iletilir.
4. Bu önizleme akışında system prompt, API'nin `instructions` alanı veya desteklenen developer mesajlarıyla uygulanır. Açık system mesajı öğesi ve desteklenmeyen alanlar kullanılmaz; gerçek istek şeması güncel kısıtlara göre hazırlanır.
5. E5 CPU üzerinde küçük örnekte çalıştırılır; vektör boyutu, girdi uzunluğu, süre ve bellek ölçülür.
6. Türkçe ve İngilizce sorularda doğru ticketın üst sıralarda bulunması incelenir. Başlangıçta en ilgili 5 chunk denenebilir.
7. Bulunan chunk metinleri LLM'e verilir. Çözüm uydurma, yanlış başarı bildirimi, yanlış kaynak ve SQL/PowerShell hataları kontrol edilir.
8. Projenin en az 10 servis masası, 5 Windows Server ve 5 Oracle senaryosunda arama başarısı ile yanıt doğruluğu ayrı ölçülür. Mevcut 10 ticketlık veri hazırlama pilotu bu test raporunun yerine geçmez.

Ürün sürümü ve kaynak kapsamı korunur. Kaynak eksikse açıklayıcı soru veya eksiklik bildirimi kullanılır. Hesap erişimi veya uygulama uygunluğu doğrulanmadan Plus yolu çalışıyor sayılmaz; aynı şekilde Groq erişimi denenmeden veya ister uyumu netleşmeden nihai karar ilan edilmez.

## 7. Resmî kaynaklar

2 Ekim 2026 tarihinde kontrol edildi:

- [OpenAI ChatGPT plan kullanımına genel bakış](https://developers.openai.com/siwc/token-sharing-open-source)
- [Plus planıyla yerel uygulama örneği](https://developers.openai.com/cookbook/articles/sign-in-with-chatgpt)
- [Resmî model kataloğu ve Responses API isteği](https://developers.openai.com/siwc/token-sharing-open-source/models-and-inference)
- [Kayıt ve OAuth bağlantısı](https://developers.openai.com/siwc/token-sharing-open-source/sign-in)
- [Önizleme sınırlamaları](https://developers.openai.com/siwc/token-sharing-open-source/preview-limitations)
- [OpenAI abonelik ve API kullanım ayrımı](https://learn.chatgpt.com/docs/pricing)
- [GPT-OSS-120B model kartı](https://huggingface.co/openai/gpt-oss-120b)
- [Groq ücretsiz plan kotaları](https://console.groq.com/docs/rate-limits)
- [Hugging Face Groq sağlayıcısı](https://huggingface.co/docs/inference-providers/providers/groq)
- [Hugging Face kredi ve faturalandırma ayrımı](https://huggingface.co/docs/inference-providers/pricing)
- [Multilingual-E5-small model kartı](https://huggingface.co/intfloat/multilingual-e5-small)

İlgili tasarımlar: [01_ER_Taslagi.md](01_ER_Taslagi.md) ve [02_RAG_Akisi.md](02_RAG_Akisi.md).
