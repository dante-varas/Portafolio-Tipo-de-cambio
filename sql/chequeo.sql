--corroborando

SELECT t.tema,
       s.nombre,
       COUNT(o.valor) AS n_obs,
       MIN(o.fecha) AS desde,
       MAX(o.fecha) AS hasta
FROM temas AS t
LEFT JOIN series AS s
    ON s.id_tema = t.id_tema
LEFT JOIN observaciones AS o 
    ON o.id_serie = s.id_serie
GROUP BY t.tema, s.nombre
ORDER BY t.tema, n_obs;