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