import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from sklearn.linear_model import LinearRegression, RidgeCV, LassoCV
from sklearn.ensemble import RandomForestRegressor, GradientBoostingRegressor
from sklearn.preprocessing import StandardScaler
from sklearn.pipeline import make_pipeline
from sklearn.model_selection import TimeSeriesSplit
from sklearn.metrics import mean_squared_error, mean_absolute_error

SEMILLA = 42
DB_PATH = "coyuntura.db"
RUTA_PRONOSTICO = "data/pronostico_resultados.csv"

# EXTRACCION DE DATOS
conn = sqlite3.connect(DB_PATH)
datos = pd.read_sql_query("SELECT mes, nombre_serie, valor FROM vista_monitor", conn)
conn.close()

datos["mes"] = pd.to_datetime(datos["mes"])
raw_data = datos.pivot(index="mes", columns="nombre_serie", values="valor")

# VARIACIONES MENSUALES
macro = pd.DataFrame(index=raw_data.index)
macro["dolar"] = 100 * np.log(raw_data["Tipo_Cambio"]).diff()
macro["cobre"] = 100 * np.log(raw_data["Precio_cobre"]).diff()
macro["dxy"] = 100 * np.log(raw_data["Indice_Dolar"]).diff()
macro["vix"] = raw_data["Indice_VIX"].diff()

# REZAGOS (1, 2 y 3 meses)
X_lags = pd.DataFrame(index=macro.index)
for col in macro.columns:
    for lag in range(1, 4):
        X_lags[f"{col}_lag{lag}"] = macro[col].shift(lag)

X_cols = list(X_lags.columns)
df = pd.concat([macro["dolar"], X_lags], axis=1).dropna()

# ENTRENAMIENTO 2013-2019 Y EVALUACION DESDE 2020
inicio_oos = df.index.get_loc(pd.Timestamp("2020-01-01"))
train = df.iloc[:inicio_oos]
print(f"Entrenamiento: {len(train)} meses; evaluación: {len(df) - inicio_oos} meses")

# PRONOSTICO FUERA DE MUESTRA (se reestima cada 12 meses)
tscv = TimeSeriesSplit(n_splits=5)
pronosticos = []

for inicio_bloque in range(inicio_oos, len(df), 12):
    historia = df.iloc[:inicio_bloque]
    futuro = df.iloc[inicio_bloque:inicio_bloque + 12]
    X_h, y_h = historia[X_cols], historia["dolar"]

    ar1 = LinearRegression().fit(historia[["dolar_lag1"]], y_h)
    ridge = make_pipeline(StandardScaler(), RidgeCV(alphas=np.logspace(-2, 5, 50), cv=tscv)).fit(X_h, y_h)
    lasso = make_pipeline(StandardScaler(), LassoCV(alphas=np.logspace(-3, 2, 50), cv=tscv, max_iter=20000)).fit(X_h, y_h)
    bosque = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=SEMILLA).fit(X_h, y_h)
    gb = GradientBoostingRegressor(n_estimators=100, learning_rate=0.05, max_depth=2, random_state=SEMILLA).fit(X_h, y_h)

    pronosticos.append(pd.DataFrame({
        "Observado": futuro["dolar"],
        "Ingenuo": 0.0,
        "AR(1)": ar1.predict(futuro[["dolar_lag1"]]),
        "Ridge": ridge.predict(futuro[X_cols]),
        "Lasso": lasso.predict(futuro[X_cols]),
        "Random Forest": bosque.predict(futuro[X_cols]),
        "Gradient Boosting": gb.predict(futuro[X_cols]),
    }, index=futuro.index))

eval_df = pd.concat(pronosticos)
print(eval_df.head().round(2))