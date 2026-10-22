-- Yalnızca yeni uygulama veritabanında çalıştırılacak başlangıç şeması.
-- PostgreSQL bilgi/embedding tablolarına dokunmaz.

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

IF EXISTS (SELECT 1 FROM sys.tables WHERE is_ms_shipped = 0)
    THROW 50002, 'Baslangic semasi bos veritabani gerektirir; mevcut tablolar degistirilmedi.', 1;

BEGIN TRY
BEGIN TRANSACTION;

-- Kullanıcı hesabı; parola yerine uygulamanın üreteceği hash saklanır.
CREATE TABLE dbo.users (
    id uniqueidentifier NOT NULL CONSTRAINT PK_users PRIMARY KEY DEFAULT NEWID(),
    email nvarchar(320) NOT NULL,
    email_normalized AS LOWER(LTRIM(RTRIM(email)) COLLATE Latin1_General_100_CI_AS_SC) PERSISTED,
    password_hash nvarchar(255) NOT NULL,
    role nvarchar(16) NOT NULL CONSTRAINT DF_users_role DEFAULT N'user',
    is_active bit NOT NULL CONSTRAINT DF_users_active DEFAULT 1,
    created_at datetime2(3) NOT NULL CONSTRAINT DF_users_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT CK_users_email CHECK (LEN(LTRIM(RTRIM(email))) BETWEEN 3 AND 320),
    CONSTRAINT CK_users_role CHECK (role IN (N'user', N'admin'))
);
CREATE UNIQUE INDEX UX_users_email_normalized ON dbo.users(email_normalized);

-- Her sohbet tek bir kullanıcıya aittir.
CREATE TABLE dbo.chat_sessions (
    id uniqueidentifier NOT NULL CONSTRAINT PK_chat_sessions PRIMARY KEY DEFAULT NEWID(),
    user_id uniqueidentifier NOT NULL,
    title nvarchar(200) NULL,
    expertise_mode nvarchar(32) NOT NULL CONSTRAINT DF_chat_sessions_mode DEFAULT N'service_desk',
    created_at datetime2(3) NOT NULL CONSTRAINT DF_chat_sessions_created DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT DF_chat_sessions_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_chat_sessions_users FOREIGN KEY (user_id) REFERENCES dbo.users(id),
    CONSTRAINT CK_chat_sessions_mode CHECK (expertise_mode IN (N'service_desk', N'windows_server', N'oracle_db'))
);
CREATE INDEX IX_chat_sessions_user_created ON dbo.chat_sessions(user_id, created_at DESC);

-- Sohbet mesajları ve yanıtın dayandığı kaynak bilgileri.
CREATE TABLE dbo.chat_messages (
    id uniqueidentifier NOT NULL CONSTRAINT PK_chat_messages PRIMARY KEY DEFAULT NEWID(),
    session_id uniqueidentifier NOT NULL,
    message_seq int NOT NULL,
    role nvarchar(16) NOT NULL,
    content nvarchar(max) NOT NULL,
    message_status nvarchar(16) NOT NULL CONSTRAINT DF_chat_messages_status DEFAULT N'completed',
    request_id uniqueidentifier NULL,
    citations_json nvarchar(max) NULL,
    source_snapshot_json nvarchar(max) NULL,
    model_name nvarchar(100) NULL,
    input_tokens int NULL,
    output_tokens int NULL,
    latency_ms int NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT DF_chat_messages_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_chat_messages_sessions FOREIGN KEY (session_id) REFERENCES dbo.chat_sessions(id),
    CONSTRAINT UQ_chat_messages_order UNIQUE (session_id, message_seq),
    CONSTRAINT CK_chat_messages_seq CHECK (message_seq > 0),
    CONSTRAINT CK_chat_messages_role CHECK (role IN (N'user', N'assistant')),
    CONSTRAINT CK_chat_messages_status CHECK (message_status IN (N'pending', N'completed', N'error')),
    CONSTRAINT CK_chat_messages_content CHECK (LEN(content) > 0),
    CONSTRAINT CK_chat_messages_citations CHECK (citations_json IS NULL OR ISJSON(citations_json) = 1),
    CONSTRAINT CK_chat_messages_snapshot CHECK (source_snapshot_json IS NULL OR ISJSON(source_snapshot_json) = 1),
    CONSTRAINT CK_chat_messages_input_tokens CHECK (input_tokens IS NULL OR input_tokens >= 0),
    CONSTRAINT CK_chat_messages_output_tokens CHECK (output_tokens IS NULL OR output_tokens >= 0),
    CONSTRAINT CK_chat_messages_latency CHECK (latency_ms IS NULL OR latency_ms >= 0)
);
CREATE INDEX IX_chat_messages_request_id ON dbo.chat_messages(request_id) WHERE request_id IS NOT NULL;

-- Her mesaj için en fazla bir geri bildirim kaydı.
-- Mesajın assistant'a ve puan veren kullanıcıya ait olduğunu uygulama doğrular.
CREATE TABLE dbo.feedback (
    id uniqueidentifier NOT NULL CONSTRAINT PK_feedback PRIMARY KEY DEFAULT NEWID(),
    message_id uniqueidentifier NOT NULL,
    rating tinyint NOT NULL,
    comment nvarchar(2000) NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT DF_feedback_created DEFAULT SYSUTCDATETIME(),
    updated_at datetime2(3) NOT NULL CONSTRAINT DF_feedback_updated DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_feedback_messages FOREIGN KEY (message_id) REFERENCES dbo.chat_messages(id),
    CONSTRAINT UQ_feedback_message UNIQUE (message_id),
    CONSTRAINT CK_feedback_rating CHECK (rating BETWEEN 1 AND 5)
);

-- Uygulama olayları; parola, token ve API anahtarı loglanmaz.
CREATE TABLE dbo.app_logs (
    id uniqueidentifier NOT NULL CONSTRAINT PK_app_logs PRIMARY KEY DEFAULT NEWID(),
    user_id uniqueidentifier NULL,
    correlation_id uniqueidentifier NOT NULL,
    level nvarchar(16) NOT NULL,
    event_type nvarchar(100) NOT NULL,
    details_json nvarchar(max) NULL,
    created_at datetime2(3) NOT NULL CONSTRAINT DF_app_logs_created DEFAULT SYSUTCDATETIME(),
    CONSTRAINT FK_app_logs_users FOREIGN KEY (user_id) REFERENCES dbo.users(id),
    CONSTRAINT CK_app_logs_level CHECK (level IN (N'debug', N'info', N'warning', N'error')),
    CONSTRAINT CK_app_logs_details CHECK (details_json IS NULL OR ISJSON(details_json) = 1)
);
CREATE INDEX IX_app_logs_correlation ON dbo.app_logs(correlation_id, created_at);

COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
