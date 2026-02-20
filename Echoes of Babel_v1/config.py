# config.py
# Configuraciones de Pantalla (Full HD por defecto para inmersión)
SCREEN_WIDTH = 1920
SCREEN_HEIGHT = 1080
FPS = 60
TITLE = "Echoes of Babel: La Sintaxis de Dios"

# Configuraciones del MUNDO
WORLD_WIDTH = 3000
WORLD_HEIGHT = 3000

# Definición de Colores (RGB)
BLACK = (5, 5, 5)        # Oscuridad casi total
WHITE = (240, 240, 240)
RED_BLOOD = (180, 0, 0)  # Color sangre
DARK_GRAY = (20, 20, 20)
WALL_COLOR = (40, 40, 50) 
LIGHT_BLUE = (100, 200, 255)
YELLOW_ICON = (255, 200, 50) 
GLITCH_COLOR = (0, 255, 255) 
GREEN_GLOW = (50, 255, 50)   

# --- COLORES DE LA INTERFAZ NARRATIVA ---
TERMINAL_GREEN = (0, 255, 100)
TERMINAL_AMBER = (255, 180, 0)
HEX_CYAN = (0, 255, 255)

# --- COLORES DE PAUSA Y GUARDADO ---
PAUSE_OVERLAY = (0, 0, 0, 230)
SLOT_EMPTY = (50, 50, 50)
SLOT_FILLED = (0, 100, 200)
SLOT_SELECTED = (200, 200, 200)
SLOT_WARNING = (200, 50, 0)

# Velocidades
SPEED_SLOW = 2   
SPEED_WALK = 5   
SPEED_RUN = 9    
TRANSITION_SPEED = 8 

# Estados del Juego
STATE_BOOT = "boot"       # Secuencia de carga
STATE_WARNING = "warning" # Pantalla de audífonos
STATE_MENU = "menu"       # Menú principal
STATE_LEVEL_ZERO = "level_zero" # PRÓLOGO (NUEVO - Agregado)
STATE_DEMO = "demo"       # Nivel 1 (Juego Principal)
STATE_QUIT = "quit"       # Salir