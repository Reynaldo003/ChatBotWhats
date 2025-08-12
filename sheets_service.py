import gspread
from google.oauth2.service_account import Credentials

# Define el alcance que se requiere para acceder a Google Sheets
SCOPES = ['https://www.googleapis.com/auth/spreadsheets']

# Ruta al archivo JSON de credenciales
CREDS_FILE = 'credentials.json'

# ID de la hoja de cálculo (de la URL de tu Google Sheet)
SPREADSHEET_ID = 'TU_ID_DE_SHEET_AQUI'

# Conectar a la hoja
def conectar_sheets():
    creds = Credentials.from_service_account_file(CREDS_FILE, scopes=SCOPES)
    cliente = gspread.authorize(creds)
    hoja = cliente.open_by_key(SPREADSHEET_ID).sheet1
    return hoja

# Leer todas las citas (suponiendo estructura: ['Nombre', 'Teléfono', 'Fecha', 'Hora'])
def obtener_citas():
    hoja = conectar_sheets()
    datos = hoja.get_all_records()
    return datos

# Agregar una nueva cita
def agregar_cita(nombre, telefono, fecha, hora):
    hoja = conectar_sheets()
    fila = [nombre, telefono, fecha, hora]
    hoja.append_row(fila)
