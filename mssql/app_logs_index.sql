-- Günlük listesi zamana göre sıralanır; indeks yoksa oluşturur, varsa dokunmaz. Veri değişmez.
IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name = N'IX_app_logs_created' AND object_id = OBJECT_ID(N'dbo.app_logs'))
    CREATE INDEX IX_app_logs_created ON dbo.app_logs(created_at DESC);
