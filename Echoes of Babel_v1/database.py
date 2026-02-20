import sqlite3
import os
import time

# Nombre del archivo de base de datos (binario, no editable fácilmente)
DB_NAME = "echoes_save.db"

def init_db():
    """Inicializa la estructura de la base de datos si no existe."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Creamos una tabla simple pero robusta
    # slot_id: 1, 2 o 3
    # progress: Porcentaje (0-100)
    # play_time: Timestamp de guardado
    # player_data: Una cadena codificada con los datos vitales (X, Y, Estado)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS save_slots (
            slot_id INTEGER PRIMARY KEY,
            progress INTEGER,
            timestamp TEXT,
            player_data TEXT
        )
    ''')
    conn.commit()
    conn.close()
    print(f"[SISTEMA] Base de datos {DB_NAME} verificada.")

def save_game(slot_id, progress, x, y, char_type):
    """Guarda o sobrescribe una ranura."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    # Formato de tiempo legible
    current_time = time.strftime("%Y-%m-%d %H:%M")
    
    # Empaquetamos los datos del jugador en una cadena simple (X,Y,TYPE)
    # Esto se podría encriptar en el futuro para más seguridad
    data_payload = f"{x},{y},{char_type}"
    
    # UPSERT: Insertar o Reemplazar si ya existe la ID
    cursor.execute('''
        INSERT OR REPLACE INTO save_slots (slot_id, progress, timestamp, player_data)
        VALUES (?, ?, ?, ?)
    ''', (slot_id, progress, current_time, data_payload))
    
    conn.commit()
    conn.close()
    print(f"[SISTEMA] Partida guardada en Ranura {slot_id} - Progreso: {progress}%")

def load_game(slot_id):
    """Carga los datos de una ranura específica."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    cursor.execute('SELECT progress, player_data FROM save_slots WHERE slot_id = ?', (slot_id,))
    row = cursor.fetchone()
    conn.close()
    
    if row:
        # Desempaquetamos
        progress = row[0]
        data_str = row[1]
        x, y, char_type = data_str.split(',')
        return {
            "exists": True,
            "progress": progress,
            "x": float(x),
            "y": float(y),
            "char_type": char_type
        }
    else:
        return {"exists": False}

def get_slots_info():
    """Obtiene un resumen de todas las ranuras para mostrar en el menú."""
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    
    slots = {}
    # Inicializamos vacíos
    for i in range(1, 4):
        slots[i] = {"empty": True, "progress": 0, "date": "---"}
        
    cursor.execute('SELECT slot_id, progress, timestamp FROM save_slots')
    rows = cursor.fetchall()
    
    for row in rows:
        s_id, prog, date = row
        slots[s_id] = {"empty": False, "progress": prog, "date": date}
        
    conn.close()
    return slots