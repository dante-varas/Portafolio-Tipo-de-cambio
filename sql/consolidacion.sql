--- ---------------------------------------------------------
--- 1. Vista Monitor: Variación interanual y promedio movil.
--- --------------------------------------------------------
DROP VIEW IF EXISTS vista_monitor;
CREATE VIEW vista_monitor AS
WITH mensual AS (
    SELECT o.id_serie,
           strftime('%Y-%m', o.fecha) AS mes,
           AVG(o.valor)               AS valor
    FROM observaciones AS o
    GROUP BY o.id_serie, mes
)
SELECT
    m.mes,
    s.nombre AS nombre_serie,
    t.tema   AS nombre_tema,
    s.fuente,
    m.valor,
    LAG(m.valor, 12) OVER (PARTITION BY m.id_serie ORDER BY m.mes) AS valor_hace_un_ano,
    ROUND(((m.valor - LAG(m.valor, 12) OVER (PARTITION BY m.id_serie ORDER BY m.mes)) /
           LAG(m.valor, 12) OVER (PARTITION BY m.id_serie ORDER BY m.mes)) * 100, 2) AS var_interanual_pct,
    AVG(m.valor) OVER (PARTITION BY m.id_serie ORDER BY m.mes
                       ROWS BETWEEN 2 PRECEDING AND CURRENT ROW) AS promedio_movil_3m
FROM mensual AS m
JOIN series AS s ON m.id_serie = s.id_serie
JOIN temas  AS t ON s.id_tema  = t.id_tema;
--- -------------------------------------------
--- 2. Vista consolidada por tema y serie.
--- -------------------------------------------
SELECT 
    t.tema AS nombre_tema,
    s.nombre AS nombre_serie,
    COUNT(o.valor)         AS total_datos,
    ROUND(AVG(o.valor), 2) AS promedio,
    ROUND(MIN(o.valor), 2) AS min_valor,
    ROUND(MAX(o.valor), 2) AS max_valor
FROM observaciones AS o
JOIN series AS s ON o.id_serie = s.id_serie
JOIN temas  AS t ON s.id_tema  = t.id_tema
GROUP BY t.tema, s.nombre
ORDER BY t.tema, s.nombre;