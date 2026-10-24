-- sql/consultas.sql
-- Consultas SQL para el análisis de coyuntura
--Llevar todas las series a frecuencia mensual promedio
DROP VIEW IF EXISTS v_variacion_12m;
CREATE VIEW v_variacion_12m AS
WITH mensual AS (
    SELECT o.id_serie,
           strftime('%Y-%m', o.fecha) AS mes,
           AVG(o.valor) AS valor
    FROM observaciones AS o
    GROUP BY o.id_serie, mes
)

-- Uniendo tablas y calcular variación interanual (12 meses)
SELECT s.nombre,
       t.tema,
       m.mes,
       m.valor AS valor_nivel,
       100.0 * ((m.valor / LAG(m.valor, 12) OVER (
           PARTITION BY m.id_serie 
           ORDER BY m.mes
       )) - 1) AS var_12m
FROM mensual AS m
JOIN series AS s ON s.id_serie = m.id_serie
JOIN temas AS t ON t.id_tema = s.id_tema
ORDER BY s.nombre, m.mes;

-- Resumen por serie: cantidad de datos, fechas y promedio
SELECT t.tema,
       s.nombre,
       COUNT(o.valor) AS n_obs,
       MIN(o.fecha)   AS fecha_inicio,
       MAX(o.fecha)   AS fecha_fin,
       AVG(o.valor)   AS promedio
FROM observaciones AS o
JOIN series AS s ON s.id_serie = o.id_serie
JOIN temas  AS t ON t.id_tema  = s.id_tema
GROUP BY t.tema, s.nombre
ORDER BY t.tema, s.nombre;