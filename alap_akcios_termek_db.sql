CREATE DATABASE akcios_termekek_db
COLLATE Hungarian_100_CI_AS_SC_UTF8;
GO

USE akcios_termekek_db;
GO

---Táblák és fontos megszoritások---
CREATE TABLE dbo.felhasznalo
(
    azonosito int IDENTITY(1,1),
    felhasznalo_kod AS ('FEL' + RIGHT('0000' + CAST(azonosito AS varchar(10)), 4)) PERSISTED,
    felhasznalonev varchar(100) NOT NULL,
	CONSTRAINT PK_felhasznalo PRIMARY KEY (azonosito),
	CONSTRAINT UQ_egyedi_felhasznalonev UNIQUE (felhasznalonev)
);
GO

CREATE TABLE dbo.kategoria
(
    azonosito INT IDENTITY(1,1),
    kategoria_kod AS ('KAT' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    nev VARCHAR(100) NOT NULL,
    szulo_azonosito INT NULL,
	CONSTRAINT PK_kategoria PRIMARY KEY (azonosito),
    CONSTRAINT FK_kategoria_szuloje
        FOREIGN KEY (szulo_azonosito) REFERENCES dbo.kategoria(azonosito),
    CONSTRAINT UQ_egyedi_kategoria_nev UNIQUE (nev),
	CONSTRAINT CK_kategoria_nem_onmagara_mutat
        CHECK (szulo_azonosito IS NULL OR szulo_azonosito <> azonosito)
);
GO

CREATE TABLE dbo.cikk
(
    azonosito INT IDENTITY(1,1),
    cikk_kod AS ('CIK' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    nev VARCHAR(200) NOT NULL,
    kategoria_azonosito INT NOT NULL,
	CONSTRAINT PK_cikk PRIMARY KEY (azonosito),
    CONSTRAINT FK_cikk_kategoriaja
        FOREIGN KEY (kategoria_azonosito) REFERENCES dbo.kategoria(azonosito),
	CONSTRAINT UQ_egyedi_cikk_nev UNIQUE (nev)
);
GO

CREATE TABLE dbo.tulajdonsag
(
    azonosito INT IDENTITY(1,1),
    tulajdonsag_kod AS ('TUL' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    nev VARCHAR(500) NOT NULL,
	CONSTRAINT PK_tulajdonsag PRIMARY KEY (azonosito),
	CONSTRAINT UQ_egyedi_tulajdonsag_nev UNIQUE (nev)
);
GO

CREATE TABLE dbo.cikk_es_tulajdonsag
(
    azonosito INT IDENTITY(1,1),
    kapcsolat_kod AS ('CET' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    cikk_azonosito INT NOT NULL,
    tulajdonsag_azonosito INT NOT NULL,
	CONSTRAINT PK_cikk_es_tulajdonsag PRIMARY KEY (azonosito),
    CONSTRAINT FK_cikk_es_tulajdonsag_cikkre_mutat
        FOREIGN KEY (cikk_azonosito) REFERENCES dbo.cikk(azonosito),
    CONSTRAINT FK_cikk_es_tulajdonsag_tulajdonsagra_mutat
        FOREIGN KEY (tulajdonsag_azonosito) REFERENCES dbo.tulajdonsag(azonosito),
    CONSTRAINT UQ_egyedi_osszekoto_cikk_es_tulajdonsag UNIQUE (cikk_azonosito, tulajdonsag_azonosito)
);
GO

CREATE TABLE dbo.kiszereles
(
    azonosito INT IDENTITY(1,1),
    kiszereles_kod AS ('KIS' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    cikk_azonosito INT NOT NULL,
    egyseg DECIMAL(10,3) NULL,
    mertekegyseg VARCHAR(2) NULL,
    darabszam INT NOT NULL,
	CONSTRAINT PK_kiszereles PRIMARY KEY (azonosito),
    CONSTRAINT FK_kiszereles_cikk
        FOREIGN KEY (cikk_azonosito) REFERENCES dbo.cikk(azonosito),
	CONSTRAINT UQ_egyedi_kiszereles_cikk_egyseg_mertekegyseg_darabszam
		UNIQUE (cikk_azonosito, egyseg, mertekegyseg, darabszam),
    CONSTRAINT CK_pozitiv_kiszereles_darabszam CHECK (darabszam > 0),
    CONSTRAINT CK_pozitiv_kiszereles_egyseg CHECK (egyseg IS NULL OR egyseg > 0),
    CONSTRAINT CK_ervenyes_kiszereles_mertekegyseg
		CHECK (mertekegyseg IS NULL OR mertekegyseg IN ('kg', 'l', 'db'))
);
GO

CREATE TABLE dbo.uzletlanc
(
    azonosito INT IDENTITY(1,1),
    uzletlanc_kod AS ('UZL' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    nev VARCHAR(10) NOT NULL,
	CONSTRAINT PK_uzletlancs PRIMARY KEY (azonosito),
	CONSTRAINT UQ_egyedi_uzletlanc UNIQUE (nev)
);
GO

CREATE TABLE dbo.kartya_tulajdonos
(
    azonosito INT IDENTITY(1,1),
    kartya_kod AS ('KAR' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    felhasznalo_azonosito INT NOT NULL,
    uzletlanc_azonosito INT NOT NULL,
	CONSTRAINT PK_kartya_tulajdonos PRIMARY KEY (azonosito),
    CONSTRAINT FK_kartya_tulajdonos_felhasznaloja
        FOREIGN KEY (felhasznalo_azonosito) REFERENCES dbo.felhasznalo(azonosito),
    CONSTRAINT FK_kartya_tulajdonos_uzletlanca
        FOREIGN KEY (uzletlanc_azonosito) REFERENCES dbo.uzletlanc(azonosito),
    CONSTRAINT UQ_egyedi_osszekoto_kartya_tulajdonos_es_felhasznalo
		UNIQUE (felhasznalo_azonosito, uzletlanc_azonosito)
);
GO

CREATE TABLE dbo.termek
(
    azonosito INT IDENTITY(1,1),
    termek_kod AS ('TER' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    uzletlanc_azonosito INT NOT NULL,
    kiszereles_azonosito INT NOT NULL,
	CONSTRAINT PK_termek PRIMARY KEY (azonosito),
    CONSTRAINT FK_termek_uzletlanca
        FOREIGN KEY (uzletlanc_azonosito) REFERENCES dbo.uzletlanc(azonosito),
    CONSTRAINT FK_termek_kiszerelese
        FOREIGN KEY (kiszereles_azonosito) REFERENCES dbo.kiszereles(azonosito),
    CONSTRAINT UQ_egyedi_termek_uzlet_es_kiszereles UNIQUE (uzletlanc_azonosito, kiszereles_azonosito)
);
GO

CREATE TABLE dbo.aktualis_ar_naplo
(
    azonosito INT IDENTITY(1,1),
    termek_azonosito INT NOT NULL,
    regi_ar INT NOT NULL,
    uj_ar INT NOT NULL,
    modositas_idopontja datetime2 NOT NULL
        CONSTRAINT DF_aktualis_ar_naplo_modositas_idopontja DEFAULT SYSDATETIME(),
    CONSTRAINT PK_aktualis_ar_naplo PRIMARY KEY (azonosito),
    CONSTRAINT FK_aktualis_ar_naplo_termeke
        FOREIGN KEY (termek_azonosito) REFERENCES dbo.termek(azonosito),
    CONSTRAINT CK_pozitiv_regi_ar CHECK (regi_ar > 0),
    CONSTRAINT CK_pozitiv_uj_ar CHECK (uj_ar > 0)
);
GO

CREATE TABLE dbo.kedvezmeny_tipus
(
    azonosito INT IDENTITY(1,1),
    tipus_kod AS ('KTP' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    tipus VARCHAR(50) NOT NULL,
    leiras VARCHAR(500) NULL,
	CONSTRAINT PK_kedvezmeny_tipus PRIMARY KEY (azonosito),
    CONSTRAINT UQ_egyedi_kedvezmeny_tipus_es_leiras UNIQUE (tipus, leiras)
);
GO

CREATE TABLE dbo.kedvezmeny
(
    azonosito INT IDENTITY(1,1),
    kedvezmeny_kod AS ('KED' + RIGHT('0000' + CAST(azonosito AS VARCHAR(10)), 4)) PERSISTED,
    termek_azonosito INT NOT NULL,
    kedvezmeny_tipus_azonosito INT NOT NULL,
    kedvezmenyes_ar INT NOT NULL,
    kartyas BIT NOT NULL,
    datum_tol DATE NOT NULL,
    datum_ig DATE NOT NULL,
	CONSTRAINT PK_kedvezmeny PRIMARY KEY (azonosito),
    CONSTRAINT FK_kedvezmeny_termeke
        FOREIGN KEY (termek_azonosito) REFERENCES dbo.termek(azonosito),
    CONSTRAINT FK_kedvezmeny_tipusa
        FOREIGN KEY (kedvezmeny_tipus_azonosito) REFERENCES dbo.kedvezmeny_tipus(azonosito),
	CONSTRAINT UQ_egyedi_kedvezmeny_termek_tipus_idoszak
		UNIQUE (termek_azonosito, kedvezmeny_tipus_azonosito, datum_tol, datum_ig),
    CONSTRAINT CK_pozitiv_kedvezmeny_ar CHECK (kedvezmenyes_ar > 0),
    CONSTRAINT CK_ervenyes_kedvezmeny_datum CHECK (datum_ig >= datum_tol)
);
GO

CREATE TABLE dbo.kedvencek
(
    azonosito int IDENTITY(1,1),
    kedvenc_kod AS ('KDV' + RIGHT('0000' + CAST(azonosito AS varchar(10)), 4)) PERSISTED UNIQUE,
    felhasznalo_azonosito int NOT NULL,
    cikk_azonosito int NOT NULL,
	CONSTRAINT PK_kedvencek PRIMARY KEY (azonosito),
    CONSTRAINT FK_kedvencek_felhasznalo
        FOREIGN KEY (felhasznalo_azonosito)
        REFERENCES dbo.felhasznalo(azonosito),
    CONSTRAINT FK_kedvencek_cikk
        FOREIGN KEY (cikk_azonosito)
        REFERENCES dbo.cikk(azonosito),
    CONSTRAINT UQ_kedvencek_felhasznalo_cikk UNIQUE (felhasznalo_azonosito, cikk_azonosito)
);
GO

CREATE TABLE dbo.naplo
(
    azonosito int IDENTITY(1,1),
    tabla_nev varchar(50) NOT NULL,
    rekord_azonosito int NOT NULL,
    muvelet_tipusa varchar(100) NOT NULL,
    modositas_idopontja datetime2 NOT NULL
        CONSTRAINT DF_naplo_modositasi_idopontja DEFAULT SYSDATETIME(),
    felhasznalo_azonosito varchar(100) NOT NULL,
	CONSTRAINT PK_naplo PRIMARY KEY (azonosito)
);
GO

---Triggerek---
CREATE TRIGGER dbo.TR_kategoria_hierarchia_ellenorzes
ON dbo.kategoria
AFTER INSERT, UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM inserted
        WHERE szulo_azonosito = azonosito
    )
    BEGIN
        RAISERROR('A kategoria nem mutathat onmagara.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;

    DECLARE @van_melyseg_hiba BIT = 0;

    ;WITH kategoria_lanc AS
    (
        SELECT
            k.azonosito,
            k.szulo_azonosito,
            1 AS melyseg
        FROM dbo.kategoria k

        UNION ALL

        SELECT
            kl.azonosito,
            k.szulo_azonosito,
            kl.melyseg + 1
        FROM kategoria_lanc kl
        INNER JOIN dbo.kategoria k
            ON kl.szulo_azonosito = k.azonosito
        WHERE kl.szulo_azonosito IS NOT NULL
          AND kl.melyseg < 10
    )
    SELECT @van_melyseg_hiba = 1
    FROM kategoria_lanc
    WHERE melyseg > 3;

    IF @van_melyseg_hiba = 1
    BEGIN
        RAISERROR('A kategoria hierarchia legfeljebb 3 szintu lehet.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;

    DECLARE @van_hurok BIT = 0;

    ;WITH hurok AS
    (
        SELECT
            k.azonosito AS kezdo_azonosito,
            k.azonosito,
            k.szulo_azonosito,
            CAST(',' + CAST(k.azonosito AS VARCHAR(MAX)) + ',' AS VARCHAR(MAX)) AS utvonal
        FROM dbo.kategoria k

        UNION ALL

        SELECT
            h.kezdo_azonosito,
            k.azonosito,
            k.szulo_azonosito,
            CAST(h.utvonal + CAST(k.azonosito AS VARCHAR(MAX)) + ',' AS VARCHAR(MAX)) AS utvonal
        FROM hurok h
        INNER JOIN dbo.kategoria k
            ON h.szulo_azonosito = k.azonosito
        WHERE h.szulo_azonosito IS NOT NULL
          AND CHARINDEX(',' + CAST(k.azonosito AS VARCHAR(MAX)) + ',', h.utvonal) = 0
    )
    SELECT @van_hurok = 1
    FROM hurok
    WHERE szulo_azonosito = kezdo_azonosito;

    IF @van_hurok = 1
    BEGIN
        RAISERROR('A kategoria hierarchiaban hivatkozasi hurok keletkezne.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

CREATE TRIGGER dbo.TR_tiltott_cikk_modositasa
ON dbo.cikk
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM deleted d
        INNER JOIN dbo.cikk_es_tulajdonsag ct
            ON d.azonosito = ct.cikk_azonosito
    )
    BEGIN
        RAISERROR('A cikk nem modosithato vagy torolheto, mert tulajdonsaghoz kapcsolodik.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

CREATE TRIGGER dbo.TR_tiltott_tulajdonsag_modositasa
ON dbo.tulajdonsag
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM deleted d
        INNER JOIN dbo.cikk_es_tulajdonsag ct
            ON d.azonosito = ct.tulajdonsag_azonosito
    )
    BEGIN
        RAISERROR('A tulajdonsag nem modosithato vagy torolheto, mert cikkhez kapcsolodik.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

CREATE TRIGGER dbo.TR_tiltott_kiszereles_modositasa
ON dbo.kiszereles
AFTER UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS (
        SELECT 1
        FROM deleted d
        INNER JOIN dbo.termek t
            ON d.azonosito = t.kiszereles_azonosito
    )
    BEGIN
        RAISERROR('A kiszereles nem modosithato vagy torolheto, mert termek hivatkozik ra.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

CREATE TRIGGER dbo.TR_tiltott_termek_hivatkozas_modositas
ON dbo.termek
AFTER UPDATE
AS
BEGIN
    SET NOCOUNT ON;

    IF EXISTS
    (
        SELECT 1
        FROM inserted i
        INNER JOIN deleted d
            ON i.azonosito = d.azonosito
        WHERE i.uzletlanc_azonosito <> d.uzletlanc_azonosito
           OR i.kiszereles_azonosito <> d.kiszereles_azonosito
    )
    BEGIN
        RAISERROR('A termek uzletlanc vagy kiszereles hivatkozasa nem modosithato.', 16, 1);
        ROLLBACK TRANSACTION;
        RETURN;
    END;
END;
GO

CREATE TRIGGER dbo.TR_tiltott_aktualis_ar_naplo_modositas
ON dbo.aktualis_ar_naplo
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF SESSION_CONTEXT(N'belso_trigger_muvelet') IS NULL
    BEGIN
        RAISERROR('Az aktualis_ar_naplo tabla csak belso muveleten keresztul modosithato.', 16, 1);
        ROLLBACK TRANSACTION;
    END
END;
GO

CREATE TRIGGER dbo.TR_tiltott_naplo_modositas
ON dbo.naplo
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    IF SESSION_CONTEXT(N'belso_trigger_muvelet') IS NULL
    BEGIN
        RAISERROR('A naplo tabla csak belso triggeren keresztul modosithato.', 16, 1);
        ROLLBACK TRANSACTION;
		RETURN;
    END
END;
GO

---egy naplózó trigger létrehozása (tesztelés miatt)---
CREATE TRIGGER dbo.TR_termek_naplozas
ON dbo.termek
AFTER INSERT, UPDATE, DELETE
AS
BEGIN
    SET NOCOUNT ON;

    EXEC sys.sp_set_session_context 
        @key = N'belso_trigger_muvelet', 
        @value = 1;

    INSERT INTO dbo.naplo
    (
        tabla_nev,
        rekord_azonosito,
        muvelet_tipusa,
        felhasznalo_azonosito
    )
    SELECT
        'termek',
        i.azonosito,
        'INSERT',
        ORIGINAL_LOGIN()
    FROM inserted i
    WHERE NOT EXISTS (
        SELECT 1 FROM deleted d WHERE d.azonosito = i.azonosito
    );

    INSERT INTO dbo.naplo
    (
        tabla_nev,
        rekord_azonosito,
        muvelet_tipusa,
        felhasznalo_azonosito
    )
    SELECT
        'termek',
        i.azonosito,
        'UPDATE',
        ORIGINAL_LOGIN()
    FROM inserted i
    INNER JOIN deleted d
        ON i.azonosito = d.azonosito;

    INSERT INTO dbo.naplo
    (
        tabla_nev,
        rekord_azonosito,
        muvelet_tipusa,
        felhasznalo_azonosito
    )
    SELECT
        'termek',
        d.azonosito,
        'DELETE',
        ORIGINAL_LOGIN()
    FROM deleted d
    WHERE NOT EXISTS (
        SELECT 1 FROM inserted i WHERE i.azonosito = d.azonosito
    );

    EXEC sys.sp_set_session_context 
        @key = N'belso_trigger_muvelet', 
        @value = NULL;
END;
GO

---Tárolt eljárások---
CREATE PROCEDURE dbo.SP_kedvenc_mentese
    @cikk_azonosito int
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @felhasznalonev varchar(100) = ORIGINAL_LOGIN();
    DECLARE @felhasznalo_azonosito int;

    SELECT @felhasznalo_azonosito = azonosito
    FROM dbo.felhasznalo
    WHERE felhasznalonev = @felhasznalonev;

    IF NOT EXISTS
    (
        SELECT 1
        FROM dbo.kedvencek
        WHERE felhasznalo_azonosito = @felhasznalo_azonosito
          AND cikk_azonosito = @cikk_azonosito
    )
    BEGIN
        INSERT INTO dbo.kedvencek
        (
            felhasznalo_azonosito,
            cikk_azonosito
        )
        VALUES
        (
            @felhasznalo_azonosito,
            @cikk_azonosito
        );
    END;
END;
GO

CREATE PROCEDURE dbo.SP_sajat_kedvencek_lekerdezese
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @felhasznalonev varchar(100) = ORIGINAL_LOGIN();

    SELECT
        k.azonosito AS kedvenc_azonosito,
        k.kedvenc_kod,
        c.azonosito AS cikk_azonosito,
        c.cikk_kod,
        c.nev AS cikk_nev,
        kat.nev AS kategoria_nev
    FROM dbo.kedvencek k
    INNER JOIN dbo.felhasznalo f
        ON k.felhasznalo_azonosito = f.azonosito
    INNER JOIN dbo.cikk c
        ON k.cikk_azonosito = c.azonosito
    INNER JOIN dbo.kategoria kat
        ON c.kategoria_azonosito = kat.azonosito
    WHERE f.felhasznalonev = @felhasznalonev
    ORDER BY c.nev;
END;
GO

CREATE PROCEDURE dbo.SP_sajat_felhasznalo_lekerdezese
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @felhasznalonev varchar(100) = ORIGINAL_LOGIN();

    SELECT
        azonosito,
        felhasznalo_kod,
        felhasznalonev
    FROM dbo.felhasznalo
    WHERE felhasznalonev = @felhasznalonev;
END;
GO

CREATE PROCEDURE dbo.SP_kedvenc_torlese
    @cikk_azonosito int
AS
BEGIN
    SET NOCOUNT ON;

    DECLARE @felhasznalonev varchar(100) = ORIGINAL_LOGIN();

    DELETE k
    FROM dbo.kedvencek k
    INNER JOIN dbo.felhasznalo f
        ON k.felhasznalo_azonosito = f.azonosito
    WHERE f.felhasznalonev = @felhasznalonev
      AND k.cikk_azonosito = @cikk_azonosito;
END;
GO

CREATE PROCEDURE dbo.SP_aktualis_ar_modositasa
    @termek_azonosito INT,
    @uj_ar INT
AS
BEGIN
    SET NOCOUNT ON;

    IF @uj_ar IS NULL OR @uj_ar <= 0
    BEGIN
        RAISERROR('Az uj arnak pozitivnak kell lennie.', 16, 1);
        RETURN;
    END;

    IF NOT EXISTS (
        SELECT 1
        FROM dbo.termek
        WHERE azonosito = @termek_azonosito
    )
    BEGIN
        RAISERROR('Nem letezik ilyen termek_azonosito.', 16, 1);
        RETURN;
    END;

    DECLARE @regi_ar INT;

    SELECT TOP 1
        @regi_ar = uj_ar
    FROM dbo.aktualis_ar_naplo
    WHERE termek_azonosito = @termek_azonosito
    ORDER BY modositas_idopontja DESC, azonosito DESC;

    -- Csak akkor naplozunk uj sort, ha nincs meg ar, vagy az uj feltoltesben valtozott az ar.
    IF @regi_ar IS NULL OR @regi_ar <> @uj_ar
    BEGIN
        BEGIN TRY
            EXEC sys.sp_set_session_context
                @key = N'belso_trigger_muvelet',
                @value = 1;

            INSERT INTO dbo.aktualis_ar_naplo
            (
                termek_azonosito,
                regi_ar,
                uj_ar
            )
            VALUES
            (
                @termek_azonosito,
                ISNULL(@regi_ar, @uj_ar),
                @uj_ar
            );

            EXEC sys.sp_set_session_context
                @key = N'belso_trigger_muvelet',
                @value = NULL;
        END TRY
        BEGIN CATCH
            EXEC sys.sp_set_session_context
                @key = N'belso_trigger_muvelet',
                @value = NULL;

            THROW;
        END CATCH;
    END;
END;
GO

---view tábla általános felhasználóknak (=felhasznalo)---
CREATE VIEW dbo.V_sajat_kedvencek
AS
SELECT
    k.azonosito AS kedvenc_azonosito,
    k.kedvenc_kod,
    c.azonosito AS cikk_azonosito,
    c.cikk_kod,
    c.nev AS cikk_nev,
    kat.nev AS kategoria_nev
FROM dbo.kedvencek k
INNER JOIN dbo.felhasznalo f
    ON k.felhasznalo_azonosito = f.azonosito
INNER JOIN dbo.cikk c
    ON k.cikk_azonosito = c.azonosito
INNER JOIN dbo.kategoria kat
    ON c.kategoria_azonosito = kat.azonosito
WHERE f.felhasznalonev = ORIGINAL_LOGIN();
GO

---Szerepkörök---
CREATE ROLE felhasznalo;
CREATE ROLE karbantarto;
CREATE ROLE admin;
GO

---Felhasznaló---
GRANT SELECT ON dbo.kategoria TO felhasznalo;
GRANT SELECT ON dbo.cikk TO felhasznalo;
GRANT SELECT ON dbo.tulajdonsag TO felhasznalo;
GRANT SELECT ON dbo.cikk_es_tulajdonsag TO felhasznalo;
GRANT SELECT ON dbo.kiszereles TO felhasznalo;
GRANT SELECT ON dbo.uzletlanc TO felhasznalo;
GRANT SELECT ON dbo.termek TO felhasznalo;
GRANT SELECT ON dbo.kedvezmeny_tipus TO felhasznalo;
GRANT SELECT ON dbo.kedvezmeny TO felhasznalo;
GRANT SELECT ON dbo.V_sajat_kedvencek TO felhasznalo;
GO

DENY SELECT, INSERT, UPDATE, DELETE ON dbo.naplo TO felhasznalo;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.felhasznalo TO felhasznalo;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.kedvencek TO felhasznalo;
DENY SELECT, INSERT, UPDATE, DELETE ON dbo.kartya_tulajdonos TO felhasznalo;
GO

GRANT EXECUTE ON dbo.SP_kedvenc_mentese TO felhasznalo;
GRANT EXECUTE ON dbo.SP_sajat_kedvencek_lekerdezese TO felhasznalo;
GRANT EXECUTE ON dbo.SP_kedvenc_torlese TO felhasznalo;
GRANT EXECUTE ON dbo.SP_sajat_felhasznalo_lekerdezese TO felhasznalo;
GO

---Karbantartó---
GRANT SELECT, INSERT, UPDATE ON dbo.cikk TO karbantarto;
GRANT SELECT, INSERT, UPDATE ON dbo.kiszereles TO karbantarto;
GRANT SELECT, INSERT, UPDATE ON dbo.termek TO karbantarto;
GRANT EXECUTE ON dbo.SP_aktualis_ar_modositasa TO karbantarto;
GO

DENY DELETE ON dbo.cikk TO karbantarto;
DENY DELETE ON dbo.termek TO karbantarto;
DENY DELETE ON dbo.kiszereles TO karbantarto;
GO

---Admin---
---ALTER ROLE db_owner ADD MEMBER [windows_felhasznalo];
---GO

---teszteléshez teszt_felhasznalo beengedése (mivel nincs még egy windows fiokom)---
USE master;
GO

CREATE LOGIN teszt_felhasznalo
WITH PASSWORD = 'Teszt12345!',
CHECK_POLICY = OFF;
GO

USE akcios_termekek_db;
GO

CREATE USER teszt_felhasznalo FOR LOGIN teszt_felhasznalo;
GO

ALTER ROLE felhasznalo ADD MEMBER teszt_felhasznalo;
GO

INSERT INTO dbo.felhasznalo
(
    felhasznalonev
)
VALUES
(
    'teszt_felhasznalo'
);
GO