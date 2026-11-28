import os
import sqlite3
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

# DEFINICION DE COLORES Y ESTILO
plt.rcParams.update({
    'figure.dpi': 120,
    'font.size': 10,
    'axes.grid': True,
    'grid.alpha': 0.3,
    'axes.spines.top': False,
    'axes.spines.right': False
})

COLOR_UDP   = '#800020'   # Serie principal (burdeo UDP)
COLOR_TREND = '#1f77b4'   # Promedio móvil / tendencia
COLOR_OK    = '#2ca02c'   # Variación negativa (apreciación del peso)
COLOR_ALERT = '#d62728'   # Variación positiva / alertas
COLOR_ALT   = '#ff7f0e'   # Pronóstico del modelo
COLOR_GRAY  = '#7f7f7f'   # Benchmark ingenuo / referencias

#EXTRACCION DE DATOS
DB_PATH = "coyuntura.db"
RUTA_PRONOSTICO = "data/pronostico_resultados.csv"
SALIDA_DASHBOARD = "dashboard/dashboard_hito3.png"

conn = sqlite3.connect(DB_PATH)
query = """
SELECT mes, nombre_serie, valor, var_interanual_pct, promedio_movil_3m
FROM vista_monitor
WHERE nombre_serie = 'Tipo_Cambio'
ORDER BY mes ASC
"""
df_tc = pd.read_sql_query(query, conn)
conn.close()

# Convertir fecha a índice temporal.
df_tc['mes'] = pd.to_datetime(df_tc['mes'])
df_tc = df_tc.set_index('mes')

tc = df_tc['valor'].dropna()
tc_pm3 = df_tc['promedio_movil_3m'].dropna()
tc_var_ia = df_tc['var_interanual_pct'].dropna()

# Estadísticos históricos para poner en contexto el último dato
ultimo_fecha = tc.index[-1]
ultimo_valor = tc.iloc[-1]
ultima_var_ia = tc_var_ia.iloc[-1]
prom_hist = tc.mean()
p75_hist = tc.quantile(0.75)

# cargar pronóstico fuera de la muestra (calculado mientras con benchmark hasta que suban el pronostico)

if os.path.exists(RUTA_PRONOSTICO):
    df_pron = pd.read_csv(RUTA_PRONOSTICO, index_col=0, parse_dates=True)
    subtitulo_pron = "Modelo seleccionado vs. Benchmark ingenuo (fuera de muestra)"
else:
    sigma_mensual = tc.diff().dropna().std()

#último doce meses observados para comparar contra el Benchmark ingenuo   
    fechas_eval = tc.index[-12:]
    pred_ingenuo_eval = tc.shift(1).loc[fechas_eval]  

#proximos 6 meses pronosticados con Benchmark (caminata aleatoria al 95%)
    fechas_fut = pd.date_range(start=ultimo_fecha + pd.offsets.MonthBegin(1), periods=6, freq='MS')
    h = np.arange(1, 7)
    pred_fut = np.repeat(ultimo_valor, 6)

    df_eval = pd.DataFrame({
            'pred_modelo': pred_ingenuo_eval,
            'pred_ingenuo': pred_ingenuo_eval,
            'ic_inf': pred_ingenuo_eval - 1.96 * sigma_mensual,
            'ic_sup': pred_ingenuo_eval + 1.96 * sigma_mensual
            }, index=fechas_eval)

    df_fut = pd.DataFrame({
            'pred_modelo': pred_fut,
            'pred_ingenuo': pred_fut,
            'ic_inf': pred_fut - 1.96 * sigma_mensual * np.sqrt(h),
            'ic_sup': pred_fut + 1.96 * sigma_mensual * np.sqrt(h)
            }, index=fechas_fut)

    df_pron = pd.concat([df_eval, df_fut])
    subtitulo_pron = "Proyección preliminar Benchmark ingenuo ± IC 95%"

#CONSTRUIMOS AHORA EL DASHBOARD CON 3 PANELES VERTICALES.

fig, axes = plt.subplots(3, 1, figsize=(12, 10))

fig.suptitle(
    f"Monitor de Tipo de Cambio (USD/CLP) | Último dato ({ultimo_fecha:%Y-%m}): "
    f"${ultimo_valor:,.1f} ({ultima_var_ia:+.1f}% interanual)",
    fontsize=13, fontweight='bold', y=0.97
)

#PANEL 1 TENEMOS LA SERIE COMPLETA Y EL ÚLTIMO DATO DESTACADO
axes[0].plot(tc.index, tc, color=COLOR_UDP, lw=2, label='Tipo de cambio observado (USD/CLP)')
axes[0].plot(tc_pm3.index, tc_pm3, color=COLOR_TREND, lw=1.5, ls='--', label='Promedio móvil 3 meses')
axes[0].axhline(prom_hist, color=COLOR_GRAY, ls=':', lw=1.2, label=f'Promedio histórico (${prom_hist:,.0f})')
axes[0].axhspan(p75_hist, tc.max() * 1.02, color=COLOR_ALERT, alpha=0.08, label='Sobre percentil 75 histórico')

# ultimo dato destacado con un punto rojo y etiqueta
axes[0].scatter([ultimo_fecha], [ultimo_valor], color=COLOR_ALERT, s=60, zorder=5,
                label=f'Último cierre: ${ultimo_valor:,.1f}')
axes[0].set_title('1. Historia del Tipo de Cambio (2013–2026) y Tendencia Reciente', fontweight='bold', loc='left')
axes[0].set_ylabel('CLP por USD')
axes[0].legend(loc='upper left', ncol=2, fontsize=8.5)

# PANEL 2 VARIACION INTERANUAL PORCENTUAL (INDICADOR DERIVADO)
var_reciente = tc_var_ia.loc['2020-01-01':]
colores_var = [COLOR_ALERT if v >= 0 else COLOR_OK for v in var_reciente]

axes[1].bar(var_reciente.index, var_reciente, width=20, color=colores_var, alpha=0.85)
axes[1].axhline(0, color='black', lw=0.9)
axes[1].set_title(f'2. Indicador Derivado: Variación Interanual % (Actual: {ultima_var_ia:+.1f}%)',
                  fontweight='bold', loc='left')
axes[1].set_ylabel('Variación 12 meses (%)')

# TERCER PANEL PRONOSTICO VS BERCHMARK FUERA DE LA MUESTRA E INTERVALO AL 95%

tc_zoom = tc.loc['2024-01-01':]
axes[2].plot(tc_zoom.index, tc_zoom, color=COLOR_UDP, lw=2, label='Observado')
axes[2].plot(df_pron.index, df_pron['pred_modelo'], color=COLOR_ALT, marker='o', markersize=4, lw=2,
             label='Pronóstico modelo')
axes[2].plot(df_pron.index, df_pron['pred_ingenuo'], color=COLOR_GRAY, ls='--', lw=1.5,
             label='Benchmark ingenuo (RW)')
axes[2].fill_between(df_pron.index, df_pron['ic_inf'], df_pron['ic_sup'],
                     color=COLOR_ALT, alpha=0.15, label='Intervalo de confianza 95%')
axes[2].axvline(ultimo_fecha, color=COLOR_GRAY, ls='-.', lw=1)

axes[2].set_title(f'3. Random Forest vs. Benchmark ingenuo',
                  fontweight='bold', loc='left', pad=8)
axes[2].set_ylabel('CLP por USD')
axes[2].legend(loc='upper left', ncol=2, fontsize=8.5)

# LEVE AJUSTE
plt.subplots_adjust(top=0.90, bottom=0.06, left=0.08, right=0.97, hspace=0.40)

os.makedirs('dashboard', exist_ok=True)
plt.savefig(SALIDA_DASHBOARD, dpi=200)
print(f"[OK] Dashboard guardado en {SALIDA_DASHBOARD}")
plt.show()



