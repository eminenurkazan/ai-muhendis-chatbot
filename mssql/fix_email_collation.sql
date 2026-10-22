-- İlk şemadaki e-posta normalizasyonunu Türkçe I/i dönüşümünden bağımsız yapar.
-- Mevcut kullanıcı kayıtlarını korur; çakışma olursa değişiklikleri geri alır.
SET NOCOUNT ON;
SET XACT_ABORT ON;
SET ANSI_NULLS ON;
SET QUOTED_IDENTIFIER ON;
SET ANSI_PADDING ON;
SET ANSI_WARNINGS ON;
SET ARITHABORT ON;
SET CONCAT_NULL_YIELDS_NULL ON;
SET NUMERIC_ROUNDABORT OFF;

IF DB_NAME() <> N'ServisMasasiApp'
    THROW 50001, 'Bu dosya sadece ServisMasasiApp veritabaninda calistirilabilir.', 1;

BEGIN TRY
    BEGIN TRANSACTION;
    DROP INDEX UX_users_email_normalized ON dbo.users;
    ALTER TABLE dbo.users DROP COLUMN email_normalized;
    ALTER TABLE dbo.users ADD email_normalized AS
        LOWER(LTRIM(RTRIM(email)) COLLATE Latin1_General_100_CI_AS_SC) PERSISTED;
    CREATE UNIQUE INDEX UX_users_email_normalized ON dbo.users(email_normalized);
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
