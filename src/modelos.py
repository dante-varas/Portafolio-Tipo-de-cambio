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
# METRICAS FUERA DE MUESTRA
# R2 OOS = 1 - MSE(modelo) / MSE(ingenuo). Si es positivo, el modelo le gana al ingenuo
mse_ingenuo = mean_squared_error(eval_df["Observado"], eval_df["Ingenuo"])

metricas = []
for modelo in ["Ingenuo", "AR(1)", "Ridge", "Lasso", "Random Forest", "Gradient Boosting"]:
    mse = mean_squared_error(eval_df["Observado"], eval_df[modelo])
    metricas.append({
        "Modelo": modelo,
        "RMSE": np.sqrt(mse),
        "MAE": mean_absolute_error(eval_df["Observado"], eval_df[modelo]),
        "R2 OOS (%)": (1 - mse / mse_ingenuo) * 100,
    })

tabla = pd.DataFrame(metricas).set_index("Modelo").round(3)
os.makedirs("resultados", exist_ok=True)
tabla.to_csv("resultados/metricas.csv")
print(tabla)

# ARCHIVO PARA EL DASHBOARD
# Se usa el Random Forest porque fue el que tuvo mayor R2 OOS
dolar = raw_data["Tipo_Cambio"].dropna()
error = tabla.loc["Random Forest", "RMSE"]

# Últimos 12 meses: pasar el pronóstico de variación % a pesos
ult = eval_df.tail(12)
dolar_ant = dolar.shift(1).loc[ult.index]
pred = dolar_ant * (1 + ult["Random Forest"] / 100)

tramo_eval = pd.DataFrame({
    "pred_modelo": pred,
    "pred_ingenuo": dolar_ant,
    "ic_inf": pred - 1.96 * error / 100 * dolar_ant,
    "ic_sup": pred + 1.96 * error / 100 * dolar_ant,
})

# Próximo mes: entrenar con toda la muestra y usar los últimos 3 meses como rezagos
bosque = RandomForestRegressor(n_estimators=300, min_samples_leaf=5, random_state=SEMILLA)
bosque.fit(df[X_cols], df["dolar"])

X_nuevo = pd.DataFrame(index=macro.index)
for col in macro.columns:
    for lag in range(1, 4):
        X_nuevo[f"{col}_lag{lag}"] = macro[col].shift(lag - 1)
var_siguiente = bosque.predict(X_nuevo.dropna().iloc[[-1]])[0]

# Próximos 6 meses: se mantiene el pronóstico del mes siguiente y el intervalo se abre con el tiempo
ultimo = dolar.iloc[-1]
valor = ultimo * (1 + var_siguiente / 100)
fechas = pd.date_range(dolar.index[-1] + pd.DateOffset(months=1), periods=6, freq="MS")
h = np.arange(1, 7)

tramo_futuro = pd.DataFrame({
    "pred_modelo": valor,
    "pred_ingenuo": ultimo,
    "ic_inf": valor - 1.96 * error / 100 * ultimo * np.sqrt(h),
    "ic_sup": valor + 1.96 * error / 100 * ultimo * np.sqrt(h),
}, index=fechas)

salida = pd.concat([tramo_eval, tramo_futuro]).round(1)
os.makedirs("data", exist_ok=True)
salida.to_csv(RUTA_PRONOSTICO)
salida.to_csv("resultados/pronostico_resultados.csv")
print(salida)