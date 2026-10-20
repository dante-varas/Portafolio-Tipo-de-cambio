# ==========================================
# src/analisis_coyuntura.py  -  Parte de Mica
# Análisis de coyuntura inicial (Hito 2)
# ==========================================
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

conn = sqlite3.connect("coyuntura.db")

# ---------- 1. Datos desde la vista ----------
datos_sql = pd.read_sql_query(
    "SELECT mes AS fecha, nombre_serie, valor, var_interanual_pct, promedio_movil_3m "
    "FROM vista_monitor", conn
)
datos_sql["fecha"] = pd.to_datetime(datos_sql["fecha"])

# Formato ancho: una columna por serie
niveles = datos_sql.pivot(index="fecha", columns="nombre_serie", values="valor")
var_ia  = datos_sql.pivot(index="fecha", columns="nombre_serie", values="var_interanual_pct")
pm3     = datos_sql.pivot(index="fecha", columns="nombre_serie", values="promedio_movil_3m")

# Diferencial de tasas (Chile - EE.UU.), en puntos porcentuales
niveles["Diferencial_Tasas"] = niveles["TPM"] - niveles["Tasa_FED_EEUU"]

# ---------- Gráfico 1: Tipo de cambio vs cobre ----------
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(niveles.index, niveles["Tipo_Cambio"], color="blue", label="Tipo de cambio")
ax1.set_ylabel("CLP / USD", color="blue")
ax2 = ax1.twinx()
ax2.plot(niveles.index, niveles["Precio_cobre"], color="orange", linestyle="--", label="Cobre")
ax2.set_ylabel("Cobre (USD/lb)", color="orange")
plt.title("Tipo de cambio vs precio del cobre")
ax1.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("tc_cobre.png", dpi=200)
plt.show()

# ---------- Gráfico 2: Matriz de correlaciones ----------
variables = ["Tipo_Cambio", "Diferencial_Tasas", "Precio_cobre", "Indice_VIX", "Indice_Dolar"]
matriz = niveles[variables].corr()

plt.figure(figsize=(7, 5))
sns.heatmap(matriz, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1)
plt.title("Correlación entre tipo de cambio y variables clave")
plt.tight_layout()
plt.savefig("correlaciones.png", dpi=200)
plt.show()

# ---------- Gráfico 3: Tipo de cambio en nivel y variación interanual ----------
desde = "2022-01-01"   # últimos años, para que se vea la coyuntura
tc   = niveles.loc[desde:, "Tipo_Cambio"]
tc3  = pm3.loc[desde:, "Tipo_Cambio"]
tcia = var_ia.loc[desde:, "Tipo_Cambio"]

fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
a1.plot(tc.index, tc, color="blue", label="Tipo de cambio")
a1.plot(tc3.index, tc3, color="gray", linestyle="--", label="Promedio móvil 3 meses")
a1.set_ylabel("CLP / USD")
a1.legend()
a1.grid(True, alpha=0.3)
a1.set_title("Tipo de cambio: nivel y variación interanual")

colores = ["red" if v > 0 else "green" for v in tcia.fillna(0)]
a2.bar(tcia.index, tcia, width=20, color=colores)
a2.axhline(0, color="black", linewidth=0.8)
a2.set_ylabel("Var. interanual (%)")
a2.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("tc_nivel_variacion.png", dpi=200)
plt.show()

# ---------- Gráfico 4: Indicadores de contexto ----------
fig, ejes = plt.subplots(2, 2, figsize=(10, 6), sharex=True)
paneles = [
    ("Precio_cobre", var_ia, "Cobre (var. interanual %)"),
    ("Indice_Dolar", var_ia, "Índice dólar (var. interanual %)"),
    ("Indice_VIX", niveles, "VIX (nivel)"),
    ("Diferencial_Tasas", niveles, "Diferencial TPM - FED (pp)"),
]
for ax, (serie, tabla, titulo) in zip(ejes.flat, paneles):
    datos = tabla.loc[desde:, serie]
    ax.plot(datos.index, datos, color="teal")
    ax.axhline(0, color="black", linewidth=0.6)
    ax.set_title(titulo, fontsize=10)
    ax.grid(True, alpha=0.3)
plt.tight_layout()
plt.savefig("contexto.png", dpi=200)
plt.show()

# ---------- Números para el informe ----------
print("\n=== CORRELACIONES CON EL TIPO DE CAMBIO ===")
print(matriz["Tipo_Cambio"].round(2))

print("\n=== TIPO DE CAMBIO, ÚLTIMOS 6 MESES ===")
ultimos = pd.DataFrame({
    "nivel": niveles["Tipo_Cambio"],
    "prom_movil_3m": pm3["Tipo_Cambio"],
    "var_interanual_%": var_ia["Tipo_Cambio"],
}).dropna(subset=["nivel"]).tail(6).round(1)
print(ultimos)

print("\n=== CONTEXTO, ÚLTIMOS 6 MESES ===")
print(niveles[["Precio_cobre", "Indice_Dolar", "Indice_VIX", "TPM", "Tasa_FED_EEUU", "Diferencial_Tasas"]]
      .dropna(how="all").tail(6).round(2))

conn.close()
