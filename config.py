# src/config.py
SERIES_BCCH = {
    "F073.TCO.PRE.HIST.M": "Tipo_Cambio",
    "F022.TPM.TIN.D001.NO.Z.M": "TPM",
    "F074.IPC.IND.Z.EP09.C.M": "IPC",
    "F032.IMC.IND.Z.Z.EP18.Z.Z.0.M": "IMACEC",
    "F019.PPB.PRE.40.M": "Precio_cobre",
    "F073.TCR.IND.199101.M": "TCR",
    "F051.H121.STO.H.C.CLP.M": "Reservas_internacionales",
    "F049.DES.TAS.INE9.10.M": "Desempleo",
}

SERIES_FRED = {
    "FEDFUNDS": "Tasa_FED_EEUU",
    "CPIAUCSL": "IPC_EEUU",
    "DTWEXBGS": "Indice_Dolar",
    "VIXCLS": "Indice_VIX",
}

# 1. Tipo de Cambio (F073.TCO.PRE.HIST.M)
# Descripción: Precio del dólar observado en pesos chilenos (USD/CLP).
# Razón económica: Variable principal a explicar; refleja el equilibrio de divisas local e internacional.

# 2. TPM (F022.TPM.TIN.D001.NO.Z.M)
# Descripción: Tasa de interés de referencia del Banco Central de Chile.
# Razón económica: Si sube, atrae capitales a Chile, aprecia el peso y hace bajar el dólar.

# 3. IPC Chile (F074.IPC.IND.Z.EP09.C.M)
# Descripción: Medida de la inflación en Chile.
# Razón económica: Inflación alta devalúa el peso y presiona alzas en la TPM para contenerla.

# 4. IMACEC (F032.IMC.IND.Z.Z.EP18.Z.Z.0.M)
# Descripción: Indicador de la actividad económica mensual chilena.
# Razón económica: Economía fuerte atrae inversión extranjera y fortalece la moneda local.

# 5. Precio del Cobre (F019.PPB.PRE.40.M)
# Descripción: Precio spot internacional del cobre (USD/lb).
# Razón económica: Principal exportación; si sube, entran más dólares a Chile y cae el USD/CLP.

# 6. TCR (F073.TCR.IND.199101.M)
# Descripción: Índice de Tipo de Cambio Real multilateral.
# Razón económica: Mide la competitividad comercial de Chile ajustada por inflación internacional.

# 7. Reservas Internacionales (F051.H121.STO.H.C.CLP.M)
# Descripción: Stock de dólares en poder del Banco Central de Chile.
# Razón económica: Respaldo financiero para realizar intervenciones y frenar disparadas del dólar.

# 8. Desempleo (F049.DES.TAS.INE9.10.M)
# Descripción: Tasa de desocupación laboral en Chile.
# Razón económica: Desempleo alto refleja debilidad económica y resta atractivo al peso.

# 9. Tasa FED (FEDFUNDS)
# Descripción: Tasa de interés de la Reserva Federal de EE.UU.
# Razón económica: Si sube, los capitales migran a EE.UU., fuga divisas de Chile y sube el dólar.

# 10. IPC EE.UU. (CPIAUCSL)
# Descripción: Medida de la inflación estadounidense.
# Razón económica: Inflación alta en EE.UU. obliga a la FED a subir tasas, fortaleciendo el dólar.

# 11. Índice Dólar - DXY (DTWEXBGS)
# Descripción: Valor global del dólar frente a una canasta de monedas.
# Razón económica: Un dólar fuerte a nivel mundial sube directamente el tipo de cambio en Chile.

# 12. Índice VIX (VIXCLS)
# Descripción: Índice de volatilidad e incertidumbre de los mercados globales.
# Razón económica: Miedo global hace que inversionistas huyan a activos refugio en EE.UU., depreciando el peso.