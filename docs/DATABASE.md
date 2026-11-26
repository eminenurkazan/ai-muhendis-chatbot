# PostgreSQL + pgvector pilotu

Bu klasördeki RAG pilotunun varsayılan araması artık PostgreSQL + pgvector
üzerinden yapılır. Bellek içi eski karşılaştırma yalnızca açıkça
`--memory` verilirse çalışır.

## Kurulum ve çalıştırma

PowerShell'de proje klasöründe:

```powershell
$env:DATABASE_URL = "postgresql://servis_app:servis_dev_password@localhost:5432/servis_masasi"
docker compose up -d
```

Ardından Python komutları:

```powershell
python -m pip install -r requirements.txt
python -m database.init_schema
python -m database.check_connection
python -m database.import_pilot
python rag_ticket_pilotu.py
```

`init_schema` ilk kurulumda `vector` uzantısını ve üç tabloyu oluşturur.
`check_connection`, bu yüzden şema adımından sonra çalıştırılır. `DATABASE_URL`
yalnızca ayarlandığı PowerShell oturumunda geçerlidir; yeni terminal açıldığında
yeniden ayarlanmalıdır. Docker Desktop açık ve PostgreSQL konteyneri çalışır
durumda olmalıdır. Geliştirme veritabanının portu yalnızca bu bilgisayardaki
`127.0.0.1:5432` adresine açılır.

`import_pilot` hazır `outputs_local/ticket_vektorleri.json` dosyasındaki 10
embedding'i kullanır; yeni embedding üretmez. Aynı `source_record_id` ile
tekrar çalıştırıldığında kaynak ve kayıtlar güncellenir, duplicate kayıt
oluşmaz. Aktarım tek işlem içinde yapıldığı için yarım aktarım aramaya hazır
hale gelmez.

Aktarımı ikinci kez çalıştırıp yine `records=10, chunks=10` sonucunu alın.
Bağımsız SQL kontrolü için:

```powershell
docker compose exec -T postgres psql -U servis_app -d servis_masasi -c "SELECT (SELECT count(*) FROM knowledge_sources) AS kaynak, (SELECT count(*) FROM knowledge_records) AS kayit, (SELECT count(*) FROM knowledge_chunks) AS chunk;"
```

Beklenen sonuç `1 kaynak, 10 kayıt, 10 chunk`tır. Programı her soruda yeniden
başlattığınızda normal mod kayıtları PostgreSQL'den arar. Chrome, yük
dengeleyici ve Oracle sequence sorularında ilk kaynaklar sırasıyla
`1005127.0`, `1007295.0`, `1010047.0` olmalıdır. Oracle yanıtı ayrı müşteri
doğrulaması olmadığını ve kaynakta SQL/cache ayrıntıları bulunmadığını
korumalıdır.

Geçici karşılaştırma için:

```powershell
python rag_ticket_pilotu.py --memory
```

## Öğrenme notu

`knowledge_records`, bir ticketın anlamlı ve denetlenebilir bütününü tutar:
problem, çözüm, sonuç, onay durumu ve sınırlamalar burada bulunur. Bu kayıt
yanıt üretirken kaynak bağlamıdır.

`knowledge_chunks` ise arama birimidir. Uzun bir kayıt ileride birden fazla
anlamlı parçaya bölünebilir; her parçanın kendi metni, embedding'i, model adı
ve içerik hash'i olur. Bu ayrım sayesinde kaynak kaydın kimliği ve iş alanı
alanları, arama için kullanılan metin parçalarından kopmaz. Pilotun kısa 10
ticketında her kayıt tek chunk olsa bile tablo ayrımı gelecekteki bölmeyi
şimdiden destekler.

Kullanıcı sorusu BGE-M3 ile 1024 boyutlu bir embedding'e dönüştürülür. Bu
vektör, `knowledge_chunks.embedding` sütunundaki aynı modelle üretilmiş
vektörlerle karşılaştırılır. SQL'deki pgvector `<=>` işleci cosine distance
verir; `1 - distance` sıralama için cosine similarity değerine çevrilir.
Sadece `review_status='approved'` ve `index_status='ready'` kayıtlar, ayrıca
aynı `embedding_model` kullanan chunklar aday olabilir. En yakın üç chunkın
üst kayıt alanları yanıt üretimine bağlam olarak verilir.
