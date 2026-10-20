# Portafolio Tipo de Cambio

Proyecto semestral del curso **Ciencia de Datos para Economía (ICO09425)**, Universidad Diego Portales.

Construimos un **Monitor de Coyuntura y Proyección Macroeconómica** cuya variable objetivo es el **tipo de cambio observado (pesos por dólar)**. Los datos se descargan desde las APIs del Banco Central de Chile y de FRED, se guardan en una base SQLite y se consultan con SQL para el análisis en Python y el monitor en Power BI.

**Flujo de trabajo:** API → Python → SQLite → SQL → Python / Power BI

---

## Estructura del repositorio

```
Portafolio-Tipo-de-cambio/
├── .vscode/
│   └── settings.json        # configuración del editor
├── sql/
│   ├── chequeo.sql          # revisa que la carga esté completa
│   ├── consolidacion.sql    # crea la vista vista_monitor
│   └── consultas.sql        # consultas de resumen
├── src/
│   ├── config.py            # códigos y nombres de las series
│   └── carga_db.py          # descarga los datos y crea coyuntura.db
├── .env.example             # modelo para las credenciales
├── .gitignore               # excluye .env y la base de datos
└── README.md
```

---

## Cómo ejecutar el proyecto

### 1. Requisitos

- Python 3.12 o superior
- Una cuenta en la Base de Datos Estadísticos del Banco Central de Chile, con el acceso a la API activado

### 2. Clonar el repositorio

```
git clone https://github.com/dante-varas/Portafolio-Tipo-de-cambio.git
cd Portafolio-Tipo-de-cambio
```

### 3. Instalar las librerías

```
python -m pip install pandas requests pandas_datareader python-dotenv matplotlib seaborn
```

### 4. Configurar las credenciales

Copiar el archivo modelo y completar el nuevo con el usuario y la clave propios del Banco Central:

```
copy .env.example .env
```

Contenido del `.env`:

```
USER_BCCH="correo@mail.com"
PASS_BCCH="clave"
```

El archivo `.env` está en el `.gitignore`, así que **las credenciales nunca se suben al repositorio**. No hay que modificar `.env.example`.

### 5. Descargar los datos y crear la base

```
python src/carga_db.py
```

Cada serie descargada muestra `[OK]` en la terminal. Si una falla, aparece `[ERROR]` y el script sigue con las demás. Al terminar se crea el archivo `coyuntura.db`.

Opcionalmente se puede indicar una fecha de corte con el parámetro `-hasta`. Si no se indica, se usa la fecha del día.

### 6. Crear la vista para el análisis

```
python -c "import sqlite3; c=sqlite3.connect('coyuntura.db'); c.executescript(open('sql/consolidacion.sql',encoding='utf-8').read()); c.commit()"
```

---

## Datos

12 series mensuales desde enero de 2013.

| Serie | Código | Fuente | Tema |
|---|---|---|---|
| Tipo de cambio observado | F073.TCO.PRE.HIST.M | BCCh | Tipo de cambio |
| Tipo de cambio real | F073.TCR.IND.199101.M | BCCh | Tipo de cambio |
| Índice dólar (amplio) | DTWEXBGS | FRED | Tipo de cambio |
| Tasa de Política Monetaria | F022.TPM.TIN.D001.NO.Z.M | BCCh | Tasas de interés |
| Tasa FED | FEDFUNDS | FRED | Tasas de interés |
| IPC | F074.IPC.IND.Z.EP09.C.M | BCCh | Precios |
| IPC EE.UU. | CPIAUCSL | FRED | Precios |
| Imacec | F032.IMC.IND.Z.Z.EP18.Z.Z.0.M | BCCh | Actividad y empleo |
| Tasa de desempleo | F049.DES.TAS.INE9.10.M | BCCh | Actividad y empleo |
| Precio del cobre | F019.PPB.PRE.40.M | BCCh | Sector externo |
| Reservas internacionales | F051.H121.STO.H.C.CLP.M | BCCh | Sector externo |
| Índice VIX | VIXCLS | FRED | Sector externo |

El VIX y el índice dólar son diarios. En la vista se llevan a frecuencia mensual con el promedio del mes.

---

## Base de datos (`coyuntura.db`)

| Tabla | Columnas | Llaves |
|---|---|---|
| `temas` | id_tema, tema | PK: id_tema |
| `series` | id_serie, nombre, fuente, id_tema | PK: id_serie · FK: id_tema → temas |
| `observaciones` | id_serie, fecha, valor | PK: (id_serie, fecha) · FK: id_serie → series |

La vista **`vista_monitor`** une las tres tablas y agrega, para cada serie y mes, la variación interanual y el promedio móvil de 3 meses. Es la fuente del análisis en Python y del monitor en Power BI.

La base no se sube al repositorio: cada integrante la genera en su computador con `carga_db.py`.

---

## Integrantes

| Integrante | Aporte en el Hito 2 |
|---|---|
| Dante Varas | Extracción de datos y consultas (`consultas.sql`) |
| Cristóbal Villanueva | Chequeo de la carga (`chequeo.sql`) |
| Kimberly Cerda | Base SQLite y vista de consolidación (`consolidacion.sql`) |
| Micaela Villarroel | Documentación del repositorio (`README.md`) |

**Profesor:** Luis Cuevas Parra
