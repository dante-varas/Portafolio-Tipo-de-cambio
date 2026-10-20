import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

conn = sqlite3.connect("coyuntura.db")

datos_sql = pd.read_sql_query(
    "SELECT mes AS fecha, nombre_serie, valor FROM vista_monitor", conn
)
datos_sql["fecha"] = pd.to_datetime(datos_sql["fecha"])
df_analisis = datos_sql.pivot(index="fecha", columns="nombre_serie", values="valor")
df_analisis["Diferencial_Tasas"] = df_analisis["TPM"] - df_analisis["Tasa_FED_EEUU"]

# Gráfico 1: Tipo de cambio vs cobre
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(df_analisis.index, df_analisis["Tipo_Cambio"], color="blue")
ax1.set_ylabel("CLP / USD", color="blue")
ax2 = ax1.twinx()
ax2.plot(df_analisis.index, df_analisis["Precio_cobre"], color="orange", linestyle="--")
ax2.set_ylabel("Cobre (USD/lb)", color="orange")
plt.title("Evolución Tipo de Cambio vs Precio del Cobre")
ax1.grid(True)
plt.tight_layout()
plt.savefig("tc_cobre.png", dpi=200)
plt.show()

# Gráfico 2: Matriz de correlaciones
variables = ["Tipo_Cambio", "Diferencial_Tasas", "Precio_cobre", "Indice_VIX", "Indice_Dolar"]
matriz = df_analisis[variables].corr()
print(matriz.round(2))
plt.figure(figsize=(7, 5))
sns.heatmap(matriz, annot=True, cmap="coolwarm", fmt=".2f")
plt.title("Correlación entre Tipo de Cambio y Variables Clave")
plt.tight_layout()
plt.savefig("correlaciones.png", dpi=200)
plt.show()

# Dato de septiembre 2026
print(pd.read_sql_query(
    "SELECT mes, valor, var_interanual_pct FROM vista_monitor "
    "WHERE nombre_serie = 'Tipo_Cambio' AND mes = '2026-09'", conn
))
conn.close()