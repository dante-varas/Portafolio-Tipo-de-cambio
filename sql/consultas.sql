-- =========================================================
-- sql/consultas.sql
-- Consultas SQL y vista de variación interanual para coyuntura
-- =========================================================

-- Recrear la vista asegura que los cambios en la definición queden aplicados
-- en coyuntura.db sin conflictos con versiones anteriores.
DROP VIEW IF EXISTS v_variacion_12m;

-- Definimos v_variacion_12m con frecuencia mensual y variación de 12 meses
-- sin redondear para conservar precisión numérica en análisis posteriores
-- (el ordenamiento se aplica al consultar la vista, no dentro del CREATE VIEW).
CREATE VIEW v_variacion_12m AS
WITH mensual AS (
    SELECT
        o.id_serie,
        strftime('%Y-%m', o.fecha) AS mes,
        AVG(o.valor)               AS valor
    FROM observaciones AS o
    GROUP BY o.id_serie, mes
)
SELECT
    s.nombre,
    t.tema,
    m.mes,
    m.valor AS valor_nivel,
    100.0 * (
        (m.valor / LAG(m.valor, 12) OVER (PARTITION BY m.id_serie ORDER BY m.mes)) - 1
    ) AS var_12m
FROM mensual AS m
JOIN series AS s ON s.id_serie = m.id_serie
JOIN temas  AS t ON t.id_tema  = s.id_tema;

-- Consulta de control por serie para auditar cobertura de observaciones,
-- fechas extremas y nivel promedio histórico en la base.
SELECT
    t.tema,
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