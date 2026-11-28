# ==========================================
# src/modelos_pronostico.py
# Evaluación fuera de muestra y pronóstico del tipo de cambio (Hito 3)
# ==========================================
import os
import sqlite3
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingRegressor, RandomForestRegressor
from sklearn.linear_model import LassoCV, LinearRegression, RidgeCV
from sklearn.metrics import mean_absolute_error, mean_squared_error
from sklearn.model_selection import TimeSeriesSplit
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler

SEMILLA = 42
DB_PATH = "coyuntura.db"
RUTA_PRONOSTICO = "data/pronostico_resultados.csv"
RUTA_METRICAS = "resultados/metricas.csv"

# ---------- 1. Extracción desde vista_monitor ----------
# Leemos la vista consolidada en SQLite para mantener la misma base mensual
# y evitar discrepancias con el análisis de coyuntura.
conn = sqlite3.connect(DB_PATH)
datos = pd.read_sql_query("SELECT mes, nombre_serie, valor FROM vista_monitor", conn)
conn.close()

datos["mes"] = pd.to_datetime(datos["mes"])
raw_data = datos.pivot(index="mes", columns="nombre_serie", values="valor").sort_index()

# ---------- 2. Transformaciones estacionarias y rezagos ----------
# Trabajamos en variaciones logarítmicas mensuales (y cambio en VIX) en vez de
# niveles directos para reducir no estacionariedad y evitar regresiones espurias.
macro = pd.DataFrame(index=raw_data.index)
macro["dolar"] = 100 * np.log(raw_data["Tipo_Cambio"]).diff()
macro["cobre"] = 100 * np.log(raw_data["Precio_cobre"]).diff()
macro["dxy"] = 100 * np.log(raw_data["Indice_Dolar"]).diff()
macro["vix"] = raw_data["Indice_VIX"].diff()

# Usamos rezagos de 1 a 3 meses porque al pronosticar t solo contamos con
# información observada hasta t-1 (evitando fuga de información contemporánea).
X_lags = pd.DataFrame(index=macro.index)
for col in macro.columns:
    for lag in range(1, 4):
        X_lags[f"{col}_lag{lag}"] = macro[col].shift(lag)

X_cols = list(X_lags.columns)
df = pd.concat([macro["dolar"], X_lags], axis=1).dropna()

# ---------- 3. Corte temporal y evaluación fuera de muestra ----------
# Reservamos 2013-2019 para calibración inicial y evaluamos desde 2020-01-01
# respetando el orden cronológico para medir desempeño real fuera de muestra.
inicio_oos = int(df.index.searchsorted(pd.Timestamp("2020-01-01")))
if inicio_oos >= len(df):
    raise ValueError("No hay suficientes observaciones desde 2020-01-01 para evaluar OOS.")

train = df.iloc[:inicio_oos]
print(f"Entrenamiento inicial: {len(train)} meses | Evaluación OOS: {len(df) - inicio_oos} meses")

# Reestimamos en bloques de 12 meses usando únicamente historia pasada para
# simular cómo se actualizaría el modelo en la práctica sin mirar el futuro.
tscv = TimeSeriesSplit(n_splits=5)
pronosticos = []

for inicio_bloque in range(inicio_oos, len(df), 12):
    historia = df.iloc[:inicio_bloque]
    futuro = df.iloc[inicio_bloque : inicio_bloque + 12]
    X_h, y_h = historia[X_cols], historia["dolar"]

    # Estandarizamos dentro de un Pipeline para Ridge y Lasso porque las variables
    # tienen distintas escalas y la regularización es sensible a las unidades.
    ar1 = LinearRegression().fit(historia[["dolar_lag1"]], y_h)
    ridge = make_pipeline(
        StandardScaler(), RidgeCV(alphas=np.logspace(-2, 5, 50), cv=tscv)
    ).fit(X_h, y_h)
    lasso = make_pipeline(
        StandardScaler(), LassoCV(alphas=np.logspace(-3, 2, 50), cv=tscv, max_iter=20000)
    ).fit(X_h, y_h)
    bosque = RandomForestRegressor(
        n_estimators=300, min_samples_leaf=5, random_state=SEMILLA
    ).fit(X_h, y_h)
    gb = GradientBoostingRegressor(
        n_estimators=100, learning_rate=0.05, max_depth=2, random_state=SEMILLA
    ).fit(X_h, y_h)

    pronosticos.append(
        pd.DataFrame(
            {
                "Observado": futuro["dolar"],
                "Ingenuo": 0.0,
                "AR(1)": ar1.predict(futuro[["dolar_lag1"]]),
                "Ridge": ridge.predict(futuro[X_cols]),
                "Lasso": lasso.predict(futuro[X_cols]),
                "Random Forest": bosque.predict(futuro[X_cols]),
                "Gradient Boosting": gb.predict(futuro[X_cols]),
            },
            index=futuro.index,
        )
    )

eval_df = pd.concat(pronosticos)

# ---------- 4. Métricas fuera de muestra vs. benchmark ingenuo ----------
# El benchmark ingenuo (variación 0% = repetir el último nivel observado) es el
# piso mínimo: R2 OOS positivo indica mejora cuadrática respecto a no modelar.
mse_ingenuo = mean_squared_error(eval_df["Observado"], eval_df["Ingenuo"])

metricas = []
for modelo in ["Ingenuo", "AR(1)", "Ridge", "Lasso", "Random Forest", "Gradient Boosting"]:
    mse = mean_squared_error(eval_df["Observado"], eval_df[modelo])
    metricas.append(
        {
            "Modelo": modelo,
            "RMSE": np.sqrt(mse),
            "MAE": mean_absolute_error(eval_df["Observado"], eval_df[modelo]),
            "R2 OOS (%)": (1 - mse / mse_ingenuo) * 100,
        }
    )

tabla = pd.DataFrame(metricas).set_index("Modelo").round(3)
os.makedirs("resultados", exist_ok=True)
tabla.to_csv(RUTA_METRICAS)
print("\n=== MÉTRICAS FUERA DE MUESTRA ===")
print(tabla)

# ---------- 5. Exportación de pronósticos para el dashboard ----------
# Convertimos las variaciones pronosticadas a pesos (CLP/USD) para entregar un
# contrato uniforme al dashboard (pred_modelo, pred_ingenuo, ic_inf, ic_sup).
dolar = raw_data["Tipo_Cambio"].dropna()
mejor_modelo = tabla.drop(index="Ingenuo")["R2 OOS (%)"].idxmax()
error = tabla.loc[mejor_modelo, "RMSE"]

ult = eval_df.tail(min(12, len(eval_df)))
dolar_ant = dolar.shift(1).reindex(ult.index)
pred = dolar_ant * (1 + ult[mejor_modelo] / 100)

tramo_eval = pd.DataFrame(
    {
        "pred_modelo": pred,
        "pred_ingenuo": dolar_ant,
        "ic_inf": pred - 1.96 * error / 100 * dolar_ant,
        "ic_sup": pred + 1.96 * error / 100 * dolar_ant,
    }
)

# Ajustamos el modelo ganador sobre toda la muestra disponible para proyectar
# los próximos 6 meses de forma iterativa (actualizando rezagos de dolar y
# manteniendo los últimos rezagos observados de las variables exógenas).
modelos_full = {
    "AR(1)": lambda: LinearRegression().fit(df[["dolar_lag1"]], df["dolar"]),
    "Ridge": lambda: make_pipeline(
        StandardScaler(), RidgeCV(alphas=np.logspace(-2, 5, 50), cv=tscv)
    ).fit(df[X_cols], df["dolar"]),
    "Lasso": lambda: make_pipeline(
        StandardScaler(), LassoCV(alphas=np.logspace(-3, 2, 50), cv=tscv, max_iter=20000)
    ).fit(df[X_cols], df["dolar"]),
    "Random Forest": lambda: RandomForestRegressor(
        n_estimators=300, min_samples_leaf=5, random_state=SEMILLA
    ).fit(df[X_cols], df["dolar"]),
    "Gradient Boosting": lambda: GradientBoostingRegressor(
        n_estimators=100, learning_rate=0.05, max_depth=2, random_state=SEMILLA
    ).fit(df[X_cols], df["dolar"]),
}
modelo_final = modelos_full[mejor_modelo]()

# Última fila observada de macro para construir el vector inicial de rezagos (t+1)
ultimo_idx = df.index[-1]
pos_ultimo = macro.index.get_loc(ultimo_idx)
dolar_lags = [
    macro["dolar"].iloc[pos_ultimo],
    macro["dolar"].iloc[pos_ultimo - 1],
    macro["dolar"].iloc[pos_ultimo - 2],
]
exog_lags = {}
for col in ["cobre", "dxy", "vix"]:
    exog_lags[col] = [
        macro[col].iloc[pos_ultimo],
        macro[col].iloc[pos_ultimo - 1],
        macro[col].iloc[pos_ultimo - 2],
    ]

fechas = pd.date_range(ultimo_idx + pd.DateOffset(months=1), periods=6, freq="MS")
nivel_actual = float(dolar.loc[ultimo_idx])
filas_futuras = []

for h, fecha_f in enumerate(fechas, start=1):
    fila_x = {
        "dolar_lag1": dolar_lags[0],
        "dolar_lag2": dolar_lags[1],
        "dolar_lag3": dolar_lags[2],
    }
    for col, vals in exog_lags.items():
        fila_x[f"{col}_lag1"] = vals[0]
        fila_x[f"{col}_lag2"] = vals[1]
        fila_x[f"{col}_lag3"] = vals[2]

    X_step = pd.DataFrame([fila_x], index=[fecha_f])[X_cols]
    if mejor_modelo == "AR(1)":
        var_pred = float(modelo_final.predict(X_step[["dolar_lag1"]])[0])
    else:
        var_pred = float(modelo_final.predict(X_step)[0])

    nivel_pred = nivel_actual * (1 + var_pred / 100.0)
    banda = 1.96 * error / 100.0 * nivel_actual * np.sqrt(h)

    filas_futuras.append(
        {
            "fecha": fecha_f,
            "pred_modelo": nivel_pred,
            "pred_ingenuo": nivel_actual,
            "ic_inf": nivel_pred - banda,
            "ic_sup": nivel_pred + banda,
        }
    )

    # Avanzamos el rezago de dólar con la variación pronosticada
    dolar_lags = [var_pred, dolar_lags[0], dolar_lags[1]]
    nivel_actual = nivel_pred

tramo_futuro = pd.DataFrame(filas_futuras).set_index("fecha")
salida = pd.concat([tramo_eval, tramo_futuro]).round(1)
os.makedirs("data", exist_ok=True)
salida.to_csv(RUTA_PRONOSTICO)
print(f"\n[OK] Pronósticos guardados en {RUTA_PRONOSTICO} (modelo de referencia: {mejor_modelo})")
