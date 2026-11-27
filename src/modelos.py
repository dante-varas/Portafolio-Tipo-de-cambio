import sqlite3
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt

# Semilla para que los resultados del bosque se puedan repetir
SEMILLA = 42

DB_PATH = "coyuntura.db"
RUTA_PRONOSTICO = "data/pronostico_resultados.csv"   # archivo que lee el dashboard

# EXTRACCION DE DATOS
conn = sqlite3.connect(DB_PATH)
query = """
SELECT mes, nombre_serie, valor
FROM vista_monitor
WHERE nombre_serie IN ('Tipo_Cambio', 'Precio_cobre', 'Indice_Dolar',
                       'Indice_VIX', 'TPM', 'Tasa_FED_EEUU')
ORDER BY mes ASC
"""
datos = pd.read_sql_query(query, conn)
conn.close()

# Una columna por serie y una fila por mes
datos["mes"] = pd.to_datetime(datos["mes"])
raw_data = datos.pivot(index="mes", columns="nombre_serie", values="valor")

# VARIACIONES MENSUALES
# Tipo de cambio, cobre e índice dólar en variación %; el VIX y el diferencial de tasas se diferencian
macro = pd.DataFrame(index=raw_data.index)
macro["dolar"] = 100 * np.log(raw_data["Tipo_Cambio"]).diff()
macro["cobre"] = 100 * np.log(raw_data["Precio_cobre"]).diff()
macro["dxy"] = 100 * np.log(raw_data["Indice_Dolar"]).diff()
macro["vix"] = raw_data["Indice_VIX"].diff()

print(macro.dropna().head(3).round(2))

# REZAGOS
# Usar solo los tres meses anteriores para pronosticar cada mes
X_lags = pd.DataFrame(index=macro.index)
for col in macro.columns:
    for lag in range(1, 4):
        X_lags[f"{col}_lag{lag}"] = macro[col].shift(lag)

# Unir el dólar con sus rezagos y separar entrenamiento (2013-2019) y evaluación (desde 2020)
X_cols = list(X_lags.columns)
df = pd.concat([macro["dolar"], X_lags], axis=1).dropna()
inicio_oos = df.index.get_loc(pd.Timestamp("2020-01-01"))
train = df.iloc[:inicio_oos]

print(f"Predictores: {len(X_cols)}")
print(f"Entrenamiento: {len(train)} meses; evaluación: {len(df) - inicio_oos} meses")