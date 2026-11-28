import os
import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

os.makedirs("figuras", exist_ok=True)

conn = sqlite3.connect("coyuntura.db")
df_sql = pd.read_sql_query(
    "SELECT mes, nombre_serie, valor, var_interanual_pct, promedio_movil_3m FROM vista_monitor",
    conn,
)
conn.close()

df_sql["mes"] = pd.to_datetime(df_sql["mes"])
tc_df = (
    df_sql[df_sql["nombre_serie"] == "Tipo_Cambio"]
    .sort_values("mes")
    .set_index("mes")
)

ultimo_mes = tc_df.index[-1]
ultimo_valor = float(tc_df["valor"].iloc[-1])

pron = pd.read_csv("data/pronostico_resultados.csv", index_col=0, parse_dates=True).sort_index()

fig, axes = plt.subplots(3, 1, figsize=(11, 9), sharex=False)

# 1. Serie principal + dato mas reciente destacado
axes[0].plot(tc_df.index, tc_df["valor"], color="#1f4e78", linewidth=1.8, label="Tipo de cambio (CLP/USD)")
axes[0].scatter([ultimo_mes], [ultimo_valor], color="#d9534f", zorder=5, label=f"Ultimo dato ({ultimo_mes.strftime('%Y-%m')}): {ultimo_valor:.1f}")
axes[0].set_title("Monitor Tipo de Cambio: Historia y Dato Mas Reciente", fontsize=11, fontweight="bold")
axes[0].set_ylabel("CLP / USD")
axes[0].legend(loc="upper left")
axes[0].grid(True, alpha=0.3)

# 2. Indicador derivado (variacion interanual % y promedio movil 3m)
axes[1].plot(tc_df.index, tc_df["promedio_movil_3m"], color="#2e7d32", linewidth=1.6, label="Promedio movil 3m (CLP/USD)")
axes[1].set_ylabel("PM 3m (CLP/USD)", color="#2e7d32")
axes[1].grid(True, alpha=0.3)
axes[1].set_title("Indicadores Derivados: Promedio Movil 3M y Variacion Interanual (%)", fontsize=11, fontweight="bold")

ax1_twin = axes[1].twinx()
ax1_twin.bar(tc_df.index, tc_df["var_interanual_pct"], width=18, alpha=0.35, color="#f57c00", label="Var. interanual (%)")
ax1_twin.axhline(0, color="black", linewidth=0.8)
ax1_twin.set_ylabel("Var. interanual (%)", color="#f57c00")

# 3. Pronostico vs benchmark ingenuo e intervalos
axes[2].plot(pron.index, pron["pred_modelo"], color="#0b5394", linewidth=2, label="Pronostico modelo")
axes[2].plot(pron.index, pron["pred_ingenuo"], color="#666666", linestyle="--", linewidth=1.5, label="Benchmark ingenuo")
if {"ic_inf", "ic_sup"}.issubset(pron.columns):
    axes[2].fill_between(pron.index, pron["ic_inf"], pron["ic_sup"], color="#0b5394", alpha=0.18, label="Banda pronostico")
axes[2].set_title("Pronostico vs. Benchmark Ingenuo", fontsize=11, fontweight="bold")
axes[2].set_ylabel("CLP / USD")
axes[2].legend(loc="upper left")
axes[2].grid(True, alpha=0.3)

fig.text(0.01, 0.005, "Fuente: Elaboracion propia desde coyuntura.db (vista_monitor) y pronostico_resultados.csv.", fontsize=8, style="italic")
plt.tight_layout(rect=[0, 0.02, 1, 1])
plt.savefig("figuras/dashboard_tc.png", dpi=200, bbox_inches="tight")
plt.close(fig)
print("[OK] Dashboard generado en figuras/dashboard_tc.png")
