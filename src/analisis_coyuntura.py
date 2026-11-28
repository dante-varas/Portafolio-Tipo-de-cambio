# ==========================================
# src/analisis_coyuntura.py
# Diagnóstico y análisis de coyuntura macroeconómica (Hito 2 / Hito 3)
# ==========================================
import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns

# Asegurar que exista el directorio de salida para evitar fallos en ejecuciones limpias.
os.makedirs("figuras", exist_ok=True)

# Conectamos a coyuntura.db porque es la base consolidada del pipeline SQL
# y garantiza consistencia de datos entre el diagnóstico, el pronóstico y el dashboard.
conn = sqlite3.connect("coyuntura.db")

# ---------- 1. Datos desde la vista ----------
# Usamos vista_monitor en lugar de consultar observaciones en bruto para aprovechar
# la agregación mensual y los indicadores derivados ya estandarizados en SQL.
datos_sql = pd.read_sql_query(
    "SELECT mes AS fecha, nombre_serie, valor, var_interanual_pct, promedio_movil_3m "
    "FROM vista_monitor",
    conn,
)
datos_sql["fecha"] = pd.to_datetime(datos_sql["fecha"])

# Pivotamos a formato ancho con fecha como índice para alinear series de distinta
# frecuencia original y facilitar cálculos entre variables y análisis temporal.
niveles = datos_sql.pivot(index="fecha", columns="nombre_serie", values="valor")
var_ia = datos_sql.pivot(index="fecha", columns="nombre_serie", values="var_interanual_pct")
pm3 = datos_sql.pivot(index="fecha", columns="nombre_serie", values="promedio_movil_3m")

# Calculamos el diferencial de tasas (Chile - EE. UU.) en puntos porcentuales porque
# el atractivo relativo de las tasas locales frente a la FED influye en los flujos
# financieros y en la presión sobre el tipo de cambio nominal.
niveles["Diferencial_Tasas"] = niveles["TPM"] - niveles["Tasa_FED_EEUU"]

# ---------- Gráfico 1: Tipo de cambio vs cobre ----------
# Usamos doble eje porque el CLP/USD (cientos de pesos) y el precio del cobre
# (USD/lb) tienen escalas distintas; graficarlos juntos permite evaluar la
# relación histórica entre un determinante externo clave y el tipo de cambio.
fig, ax1 = plt.subplots(figsize=(10, 5))
ax1.plot(niveles.index, niveles["Tipo_Cambio"], color="blue", label="Tipo de cambio")
ax1.set_ylabel("Pesos por dólar (CLP / USD)", color="blue")
ax2 = ax1.twinx()
ax2.plot(niveles.index, niveles["Precio_cobre"], color="orange", linestyle="--", label="Cobre")
ax2.set_ylabel("Cobre (USD/lb)", color="orange")
plt.title(
    "Tipo de cambio vs precio del cobre\n(Frecuencia mensual, 2013 -- 2026)",
    fontsize=11,
    fontweight="bold",
)
ax1.grid(True, alpha=0.3)
fig.text(
    0.01,
    0.01,
    "Fuente: Elaboración propia a partir de datos del BCCh y FRED.",
    fontsize=8,
    style="italic",
)
plt.tight_layout()
plt.savefig("figuras/tc_cobre.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Gráfico 2: Matriz de correlaciones ----------
# Seleccionamos estas cinco variables porque sintetizan los principales canales
# macroeconómicos del USD/CLP: términos de intercambio (cobre), fortaleza global
# del dólar (DXY), aversión al riesgo (VIX) y diferencial de tasas de política.
variables = ["Tipo_Cambio", "Diferencial_Tasas", "Precio_cobre", "Indice_VIX", "Indice_Dolar"]
matriz = niveles[variables].corr()

fig, ax = plt.subplots(figsize=(7, 5))
sns.heatmap(matriz, annot=True, cmap="coolwarm", fmt=".2f", vmin=-1, vmax=1, ax=ax)
ax.set_title(
    "Matriz de correlación entre variables clave\n(Niveles mensuales, 2013 -- 2026)",
    fontsize=11,
    fontweight="bold",
)
fig.text(
    0.01,
    0.01,
    "Fuente: Elaboración propia a partir de datos del BCCh y FRED.",
    fontsize=8,
    style="italic",
)
plt.tight_layout()
plt.savefig("figuras/correlaciones.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Gráfico 3: Tipo de cambio en nivel y variación interanual ----------
# Acotamos desde 2022 para observar con mayor claridad la coyuntura reciente y
# combinamos promedio móvil de 3 meses (filtra ruido mensual) con variación
# interanual (muestra el ritmo de depreciación o apreciación anual).
desde = "2022-01-01"
tc = niveles.loc[desde:, "Tipo_Cambio"]
tc3 = pm3.loc[desde:, "Tipo_Cambio"]
tcia = var_ia.loc[desde:, "Tipo_Cambio"]

fig, (a1, a2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
a1.plot(tc.index, tc, color="blue", label="Tipo de cambio")
a1.plot(tc3.index, tc3, color="gray", linestyle="--", label="Promedio móvil 3 meses")
a1.set_ylabel("CLP / USD")
a1.legend()
a1.grid(True, alpha=0.3)
a1.set_title("Tipo de cambio: nivel y variación interanual (2022 -- 2026)", fontsize=11, fontweight="bold")

colores = ["red" if v > 0 else "green" for v in tcia.fillna(0)]
a2.bar(tcia.index, tcia, width=20, color=colores)
a2.axhline(0, color="black", linewidth=0.8)
a2.set_ylabel("Var. interanual (%)")
a2.grid(True, alpha=0.3)
fig.text(
    0.01,
    0.01,
    "Fuente: Elaboración propia a partir de datos del BCCh y FRED.",
    fontsize=8,
    style="italic",
)
plt.tight_layout()
plt.savefig("figuras/tc_nivel_variacion.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Gráfico 4: Indicadores de contexto ----------
# Agrupamos en 2x2 para contrastar el entorno externo (cobre, DXY, VIX) con el
# diferencial de tasas en la misma ventana reciente (desde 2022) y detectar
# cambios de régimen que expliquen movimientos bruscos del tipo de cambio.
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
    ax.set_title(titulo, fontsize=10, fontweight="bold")
    ax.grid(True, alpha=0.3)

fig.text(
    0.01,
    0.01,
    "Fuente: Elaboración propia a partir de datos del BCCh y FRED.",
    fontsize=8,
    style="italic",
)
plt.tight_layout()
plt.savefig("figuras/contexto.png", dpi=200, bbox_inches="tight")
plt.close(fig)

# ---------- Números para el informe ----------
# Imprimimos resúmenes tabulados para tener cifras exactas y reproducibles al
# redactar el diagnóstico en el informe y la presentación.
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
print(
    niveles[["Precio_cobre", "Indice_Dolar", "Indice_VIX", "TPM", "Tasa_FED_EEUU", "Diferencial_Tasas"]]
    .dropna(how="all")
    .tail(6)
    .round(2)
)

conn.close()
