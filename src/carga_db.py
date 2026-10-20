import argparse
import datetime
import os
import sqlite3  # NUEVO: para crear la base de datos
import pandas as pd
import pandas_datareader.data as web
import requests
from dotenv import load_dotenv
from config import SERIES_BCCH, SERIES_FRED

# Cargar credenciales privadas de .env
load_dotenv()

USER_BCCH = os.getenv("USER_BCCH")
PASS_BCCH = os.getenv("PASS_BCCH")

# NUEVO: nombre del archivo de la base de datos
DB_PATH = "coyuntura.db"

# NUEVO: clasificación temática de los indicadores
TEMAS = {
    1: "Tipo de cambio",
    2: "Tasas de interés",
    3: "Precios",
    4: "Actividad y empleo",
    5: "Sector externo",
}

# NUEVO: a qué tema pertenece cada serie
TEMA_POR_SERIE = {
    "Tipo_Cambio": 1,
    "TCR": 1,
    "Indice_Dolar": 1,
    "TPM": 2,
    "Tasa_FED_EEUU": 2,
    "IPC": 3,
    "IPC_EEUU": 3,
    "IMACEC": 4,
    "Desempleo": 4,
    "Precio_cobre": 5,
    "Reservas_internacionales": 5,
    "Indice_VIX": 5,
}


def get_bcch_data(serie, user, password, start_date="2013-01-01"):
    url = f"https://si3.bcentral.cl/SieteRestWS/SieteRestWS.ashx?user={user}&pass={password}&firstdate={start_date}&timeseries={serie}&function=GetSeries"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            data = response.json()["Series"]["Obs"]
            df = pd.DataFrame(data)
            df["indexDateString"] = pd.to_datetime(df["indexDateString"], format="%d-%m-%Y")
            df.set_index("indexDateString", inplace=True)
            df.rename(columns={"value": "valor"}, inplace=True)
            df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
            return df[["valor"]]
    except Exception:
        pass
    return pd.DataFrame()


# NUEVO: guarda los datos en SQLite con 3 tablas relacionadas
def guardar_en_db(df_obs):
    # Tabla temas
    df_temas = pd.DataFrame(list(TEMAS.items()), columns=["id_tema", "tema"])

    # Tabla series (catálogo con fuente y tema)
    filas = []
    for codigo, nombre in SERIES_BCCH.items():
        filas.append([codigo, nombre, "BCCH", TEMA_POR_SERIE.get(nombre)])
    for codigo, nombre in SERIES_FRED.items():
        filas.append([codigo, nombre, "FRED", TEMA_POR_SERIE.get(nombre)])
    df_series = pd.DataFrame(filas, columns=["id_serie", "nombre", "fuente", "id_tema"])

    # Tabla observaciones (fecha como texto AAAA-MM-DD para usar strftime en SQL)
    df_obs = df_obs[["id_serie", "fecha", "valor"]].copy()
    df_obs["fecha"] = pd.to_datetime(df_obs["fecha"]).dt.strftime("%Y-%m-%d")

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Crear las tablas con sus llaves (se reemplazan en cada corrida)
    cur.executescript("""
        DROP TABLE IF EXISTS observaciones;
        DROP TABLE IF EXISTS series;
        DROP TABLE IF EXISTS temas;

        CREATE TABLE temas (
            id_tema INTEGER PRIMARY KEY,
            tema    TEXT NOT NULL
        );

        CREATE TABLE series (
            id_serie TEXT PRIMARY KEY,
            nombre   TEXT NOT NULL,
            fuente   TEXT,
            id_tema  INTEGER REFERENCES temas(id_tema)
        );

        CREATE TABLE observaciones (
            id_serie TEXT REFERENCES series(id_serie),
            fecha    TEXT NOT NULL,
            valor    REAL,
            PRIMARY KEY (id_serie, fecha)
        );
    """)

    df_temas.to_sql("temas", conn, if_exists="append", index=False)
    df_series.to_sql("series", conn, if_exists="append", index=False)
    df_obs.to_sql("observaciones", conn, if_exists="append", index=False)

    conn.commit()
    conn.close()
    print(f"Base de datos guardada en {DB_PATH}")


if __name__ == "__main__":
    print("Iniciando extracción...")

    # Leer el parámetro de la fecha
    parser = argparse.ArgumentParser()
    parser.add_argument("-hasta", type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()

    start_date_fred = datetime.datetime(2013, 1, 1)
    end_date_fred = datetime.datetime.strptime(args.hasta, "%Y-%m-%d")

    lista_obs = []

    # Extracción BCCH
    for codigo, nombre in SERIES_BCCH.items():
        df_temp = get_bcch_data(codigo, USER_BCCH, PASS_BCCH, "2013-01-01")
        if not df_temp.empty:
            df_temp = df_temp.reset_index()
            df_temp.columns = ["fecha", "valor"]
            df_temp["id_serie"] = codigo

            # Filtrar por el argumento -hasta
            df_temp = df_temp[df_temp["fecha"] <= end_date_fred]
            lista_obs.append(df_temp)
            print(f"[OK] Serie BCCH: {nombre}")
        else:
            print(f"[ERROR] Serie BCCH: {nombre}")

    # Extracción FRED
    for codigo, nombre in SERIES_FRED.items():
        try:
            df_temp = web.DataReader(codigo, "fred", start_date_fred, end_date_fred)
            if not df_temp.empty:
                df_temp = df_temp.reset_index()
                df_temp = df_temp[["DATE", codigo]]
                df_temp.columns = ["fecha", "valor"]
                df_temp["id_serie"] = codigo
                lista_obs.append(df_temp)
                print(f"[OK] Serie FRED: {nombre}")
            else:
                print(f"[ERROR] Serie FRED: {nombre}")
        except Exception:
            print(f"[ERROR] Serie FRED: {nombre}")

    # Concatenar y guardar
    if len(lista_obs) > 0:
        df_obs = pd.concat(lista_obs, ignore_index=True).dropna()
        print(f"\nExtracción terminada. Total registros: {len(df_obs)}")
        guardar_en_db(df_obs)  # NUEVO
    else:
        print("\nFalló la extracción.")