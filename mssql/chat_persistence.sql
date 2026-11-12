-- Existing data stays intact. Run once on ServisMasasiApp; safe to run again.
SET NOCOUNT ON;
SET XACT_ABORT ON;
IF DB_NAME() <> N'ServisMasasiApp'
    THROW 50001, 'Only ServisMasasiApp is allowed.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF COL_LENGTH('dbo.chat_messages', 'response_json') IS NULL
    BEGIN
        ALTER TABLE dbo.chat_messages ADD response_json nvarchar(max) NULL;
        EXEC(N'ALTER TABLE dbo.chat_messages ADD CONSTRAINT CK_chat_messages_response
             CHECK (response_json IS NULL OR ISJSON(response_json) = 1)');
    END;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
