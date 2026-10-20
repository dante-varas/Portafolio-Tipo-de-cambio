import argparse
import datetime
import os
import pandas as pd
import pandas_datareader.data as web
import requests
from dotenv import load_dotenv
from config import SERIES_BCCH, SERIES_FRED

# Cargar credencales privadas de .env
load_dotenv()

USER_BCCH = os.getenv("USER_BCCH")
PASS_BCCH = os.getenv("PASS_BCCH")

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

if __name__ == "__main__":
    print("Iniciando extracción... (extracción guardada bien)")
    
    # Leer el parametro de la fecha
    parser = argparse.ArgumentParser()
    parser.add_argument("-hasta", type=str, default=datetime.datetime.now().strftime("%Y-%m-%d"))
    args = parser.parse_args()
    
    start_date_fred = datetime.datetime(2013, 1, 1)
    end_date_fred = datetime.datetime.strptime(args.hasta, "%Y-%m-%d")
    
    lista_obs = []

    # Extraccion BCCH
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

    # Extraccion FRED
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

    #Concatenando y mostrando el resultado
    if len(lista_obs) > 0:
        df_obs = pd.concat(lista_obs, ignore_index=True).dropna()
        print(f"\nExtraccion terminada. Total registros: {len(df_obs)}")
    else:
        print("\nFallo la extraccion.")