USE akcios_termekek_db;
GO

---lekérdezések tesztelése---
---milyen SPAR-os termékek vannak (tulajdonságaikkal)?---
SELECT
    c.cikk_kod,
	t.tulajdonsag_kod,
    c.nev AS cikk_nev,
    t.nev AS tulajdonsag_nev
FROM dbo.cikk AS c
INNER JOIN dbo.cikk_es_tulajdonsag AS cet
    ON c.azonosito = cet.cikk_azonosito
INNER JOIN dbo.tulajdonsag AS t
    ON t.azonosito = cet.tulajdonsag_azonosito
WHERE c.nev LIKE '%SPAR%';

--milyen friss termékek vannak ma?---
SELECT
    c.cikk_kod,
    t.tulajdonsag_kod,
	t.nev,
    c.nev AS cikk_nev
FROM dbo.cikk AS c    
INNER JOIN dbo.cikk_es_tulajdonsag AS cet
    ON c.azonosito = cet.cikk_azonosito
INNER JOIN dbo.tulajdonsag AS t
    ON t.azonosito = cet.tulajdonsag_azonosito
INNER JOIN dbo.kiszereles AS kisz
    ON kisz.cikk_azonosito = c.azonosito
INNER JOIN dbo.termek AS term
    ON term.kiszereles_azonosito = kisz.azonosito
INNER JOIN dbo.kedvezmeny AS k
    ON k.termek_azonosito = term.azonosito
WHERE t.nev LIKE '%friss%' AND SYSDATETIME() BETWEEN k.datum_tol AND k.datum_ig;

---milyen akciókat tudok felhasználni, ha csak LIDL és SPAR kártyám van?---
SELECT
    ul.nev AS uzletlanc_nev,
    c.nev AS cikk_nev,
    k.kedvezmenyes_ar,
    k.datum_tol,
    k.datum_ig
FROM dbo.kedvezmeny AS k
JOIN dbo.termek AS t
    ON k.termek_azonosito = t.azonosito
JOIN dbo.uzletlanc AS ul
    ON t.uzletlanc_azonosito = ul.azonosito
JOIN dbo.kiszereles AS kisz
    ON t.kiszereles_azonosito = kisz.azonosito
JOIN dbo.cikk AS c
    ON kisz.cikk_azonosito = c.azonosito
JOIN dbo.kedvezmeny_tipus AS kt
    ON k.kedvezmeny_tipus_azonosito = kt.azonosito
WHERE CAST(SYSDATETIME() AS DATE) BETWEEN k.datum_tol AND k.datum_ig
  AND
  (
        k.kartyas = 0
        OR
        (
            k.kartyas = 1
            AND ul.nev IN ('LIDL', 'SPAR')
        )
  )
ORDER BY
    ul.nev,
    c.nev;