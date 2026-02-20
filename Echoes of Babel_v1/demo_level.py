# demo_level.py
import pygame
import config
import threading
import queue
import time
import random
import database
import math
import array
import struct
import json
from scenes import Scene, CURRENT_SESSION, AUDIO_AVAILABLE
from entities import Player

try:
    import pyaudio
    from vosk import Model, KaldiRecognizer
except ImportError:
    pass

class DemoScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.world_width = config.WORLD_WIDTH
        self.world_height = config.WORLD_HEIGHT
        
        # Inicializar jugador
        self.player = Player(self.world_width // 2, self.world_height // 2)
        
        # --- CARGA DE DATOS (Integración con Database) ---
        if CURRENT_SESSION["should_load"]:
            data = database.load_game(CURRENT_SESSION["slot"])
            if data["exists"]:
                self.player.x = data["x"]
                self.player.y = data["y"]
                self.player.set_character(data["char_type"])
                print(f"[DEMO] Partida cargada: Slot {CURRENT_SESSION['slot']}")

        # Cámara y Efectos
        self.camera_x = 0
        self.camera_y = 0
        self.particles = []
        self.pulses = [] 
        
        # Entidades Fantasma (Lore)
        self.ghosts = [
            {"x": self.world_width//2 + 300, "y": self.world_height//2 - 200, "phrase": "", "timer": 0},
            {"x": self.world_width//2 - 300, "y": self.world_height//2 + 300, "phrase": "", "timer": 0}
        ]
        self.lore_phrases = ["No es aire... es vibración.", "Elena... ¿dónde estás?", "El Pozo nos traga a todos.", "Silencio... ellos escuchan.", "La frecuencia de Dios duele."]
        
        # Mecánicas de Visión y Castigo
        self.base_vision = 80
        self.vision_radius = self.base_vision
        self.light_timer = 0
        self.last_cmd_str = ""
        self.repetition_count = 0
        self.punishment_mode = 0 
        self.last_cmd_display = ""
        
        # Audio y Comandos
        self.command_queue = queue.Queue()
        self.audio_running = False
        self.db_level = -60
        self.echo_sound = self._generate_ping_sound()
        
        # Estados de Guardado
        self.is_paused = False
        self.saving_timer = 0
        
        if AUDIO_AVAILABLE:
            self.audio_running = True
            threading.Thread(target=self.listener, daemon=True).start()

    def _generate_ping_sound(self):
        sample_rate = 44100
        duration = 0.5
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)
        for i in range(n_samples):
            t = float(i) / sample_rate
            value = int(32767.0 * math.sin(2 * math.pi * 800 * t) * math.exp(-6 * t))
            buf[i] = value
        return pygame.mixer.Sound(buffer=buf)

    def listener(self):
        try:
            model = Model("model")
            # Gramática expandida con comandos de menú y guardado
            grammar = '["luz", "fuego", "camino de fuego", "eco", "menu", "arriba", "abajo", "derecha", "izquierda", "caminar", "correr", "parar", "detenerse", "agacharse", "levantarse", "pie", "cambiar a sombra", "cambiar a cero", "lento", "guardar", "pausa", "salir", "[unk]"]'
            rec = KaldiRecognizer(model, 16000, grammar)
            p = pyaudio.PyAudio()
            stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=512)
            stream.start_stream()
            
            while self.audio_running:
                data = stream.read(512, exception_on_overflow=False)
                # Cálculo de DB para efectos visuales si se desea
                shorts = struct.unpack(f"<{len(data)//2}h", data)
                rms = math.sqrt(sum(s**2 for s in shorts) / len(shorts)) if shorts else 0
                self.db_level = (20 * math.log10(rms) - 90) if rms > 0 else -60
                
                if rec.AcceptWaveform(data): pass 
                else:
                    partial = json.loads(rec.PartialResult()).get("partial", "")
                    if partial:
                        words = ["arriba", "abajo", "derecha", "izquierda", "correr", "caminar", "parar", "luz", "fuego", "menu", "cambiar a sombra", "cambiar a cero", "camino de fuego", "agacharse", "levantarse", "pie", "eco", "lento", "guardar", "pausa", "salir"]
                        for w in words:
                            if w in partial:
                                self.command_queue.put(w)
                                rec.Reset()
                                break
        except Exception as e:
            print(f"Error Audio: {e}")

    def trigger_echo(self):
        """Mecánica de Ecolocalización"""
        nearest_dist = float('inf')
        nearest_ghost = None
        for g in self.ghosts:
            dist = math.hypot(g["x"] - self.player.x, g["y"] - self.player.y)
            if dist < nearest_dist:
                nearest_dist = dist
                nearest_ghost = g
        
        # Audio Panning (Sonido 3D simulado)
        if nearest_ghost:
            dx = nearest_ghost["x"] - self.player.x
            dy = nearest_ghost["y"] - self.player.y
            angle = math.atan2(dy, dx)
            pan = math.cos(angle) # -1 izquierda, 1 derecha
            vol_left = max(0.1, min(1.0, 1.0 - max(0, pan) + 0.2))
            vol_right = max(0.1, min(1.0, 1.0 + min(0, pan) + 0.2))
            channel = self.echo_sound.play()
            if channel: channel.set_volume(vol_left, vol_right)
            
            # Efecto Visual de Onda
            self.pulses.append({"x": self.player.x, "y": self.player.y, "radius": 0, "max_radius": 600, "color": config.LIGHT_BLUE})

    def execute_command(self, cmd):
        # Comandos que no castigan por repetición
        ignore_list = ["arriba", "abajo", "izquierda", "derecha", "parar", "caminar", "correr", "agacharse", "levantarse", "pie", "eco", "lento", "guardar"]
        
        if cmd not in ignore_list:
            if cmd == self.last_cmd_str:
                self.repetition_count += 1
            else:
                self.repetition_count = 1
                self.last_cmd_str = cmd
            
            # Castigo por spam de comandos poderosos
            if self.repetition_count >= 4:
                self.trigger_punishment()
                self.last_cmd_display = "¡SOBRECARGA!"
                return 

        self.last_cmd_display = cmd.upper()

        # --- NAVEGACIÓN ---
        if cmd == "arriba": self.player.set_direction(0, -1)
        elif cmd == "abajo": self.player.set_direction(0, 1)
        elif cmd == "derecha": self.player.set_direction(1, 0)
        elif cmd == "izquierda": self.player.set_direction(-1, 0)
        elif cmd == "parar" or cmd == "detenerse": self.player.stop()
        elif cmd == "correr": self.player.set_speed_mode("correr")
        elif cmd == "caminar": self.player.set_speed_mode("caminar")
        elif cmd == "lento": self.player.set_speed_mode("lento")
        elif cmd == "agacharse": self.player.crouch()
        elif cmd == "levantarse" or cmd == "pie": self.player.stand_up()
        
        # --- HABILIDADES ---
        elif cmd == "eco": 
            if self.player.char_type == "cero": self.trigger_echo()
            else: self.last_cmd_display = "SOLO CERO USA ECO"
        
        elif cmd == "cambiar a sombra":
            self.player.set_character("sombra")
            self.particles.append({"x": self.player.x, "y": self.player.y, "vx": 0, "vy": 0, "life": 60, "size": 100, "color": (100, 0, 0), "type": "morph"})
        
        elif cmd == "cambiar a cero":
            self.player.set_character("cero")
            self.particles.append({"x": self.player.x, "y": self.player.y, "vx": 0, "vy": 0, "life": 60, "size": 100, "color": (0, 200, 255), "type": "morph"})
        
        elif cmd == "luz":
            self.light_timer = 180 
        
        elif cmd == "fuego":
            # Efecto de explosión de partículas
            for _ in range(60):
                angle = random.uniform(0, 6.28)
                speed = random.uniform(2, 8)
                self.particles.append({
                    "x": self.player.x, "y": self.player.y, 
                    "vx": math.cos(angle)*speed, "vy": math.sin(angle)*speed, 
                    "life": random.randint(40, 80), "size": random.randint(8, 18), 
                    "color": config.RED_BLOOD, "type": "fire"
                })
        
        elif cmd == "camino de fuego":
            dx, dy = self.player.facing_x, self.player.facing_y
            for i in range(25):
                offset_x = random.uniform(-15, 15)
                offset_y = random.uniform(-15, 15)
                self.particles.append({
                    "x": self.player.x + offset_x, "y": self.player.y + offset_y, 
                    "vx": dx * 8 + random.uniform(-1, 1), "vy": dy * 8 + random.uniform(-1, 1), 
                    "life": 100, "size": random.randint(10, 22), 
                    "color": (255, 100, 0), "type": "fire"
                })
        
        # --- SISTEMA ---
        elif cmd == "guardar":
            database.save_game(CURRENT_SESSION["slot"], 15, self.player.x, self.player.y, self.player.char_type)
            self.last_cmd_display = "JUEGO GUARDADO"
            self.saving_timer = 60
            
        elif cmd == "menu" or cmd == "salir":
            self.audio_running = False
            self.change_scene(config.STATE_MENU)

    def trigger_punishment(self):
        """Reduce la visión y crea un efecto de sacudida"""
        self.punishment_mode = 60
        self.repetition_count = 0
        self.vision_radius = 20
        self.light_timer = 0 

    def update(self):
        self.update_fade()
        
        while not self.command_queue.empty():
            self.execute_command(self.command_queue.get())
        
        # Mensajes de guardado
        if self.saving_timer > 0:
            self.saving_timer -= 1
            
        self.player.update()
        
        # Lógica de Fantasmas
        if self.player.char_type == "sombra":
            for g in self.ghosts:
                dist = math.hypot(g["x"] - self.player.x, g["y"] - self.player.y)
                if dist < 250:
                    if g["phrase"] == "" or g["timer"] <= 0:
                        g["phrase"] = random.choice(self.lore_phrases)
                        g["timer"] = 180
                    else:
                        g["timer"] -= 1
                else:
                    g["phrase"] = ""
        
        # Lógica de Luz y Visión
        if self.light_timer > 0:
            self.light_timer -= 1
            if self.vision_radius < 300: self.vision_radius += 10 
        else:
            if self.vision_radius > self.base_vision: self.vision_radius -= 2
            if self.vision_radius < self.base_vision: self.vision_radius = self.base_vision
        
        # Modo Castigo (Sacudida de cámara)
        if self.punishment_mode > 0: self.punishment_mode -= 1
        
        # Cámara Suave
        target_cam_x = self.player.x - config.SCREEN_WIDTH // 2
        target_cam_y = self.player.y - config.SCREEN_HEIGHT // 2
        
        shake = random.randint(-20, 20) if self.punishment_mode > 0 else 0
        
        # Clamp camera a los límites del mundo
        target_cam_x = max(0, min(target_cam_x, self.world_width - config.SCREEN_WIDTH)) + shake
        target_cam_y = max(0, min(target_cam_y, self.world_height - config.SCREEN_HEIGHT)) + shake
        
        self.camera_x += (target_cam_x - self.camera_x) * 0.1
        self.camera_y += (target_cam_y - self.camera_y) * 0.1
        
        # Actualizar Partículas
        for p in self.particles: 
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["life"] -= 2
            if p["type"] == "fire":
                p["size"] *= 0.95
                p["vy"] -= 0.1 
        self.particles = [p for p in self.particles if p["life"] > 0]

    def draw_world_text_glitch(self, font, text, world_x, world_y, cam_x, cam_y, color, intensity=1.0):
        """Dibuja texto glitcheado en coordenadas del mundo"""
        screen_x = world_x - cam_x
        screen_y = world_y - cam_y
        self.draw_text_glitch(font, text, screen_x, screen_y, color, intensity)

    def _draw_ghost(self, g, cam_x, cam_y):
        x, y = g["x"], g["y"]
        t = pygame.time.get_ticks() * 0.005
        off_x = math.sin(t * 10) * 3
        
        points = [(x - 20 + off_x, y - 50), (x + 20 + off_x, y - 50), (x + 5, y + 40), (x - 5, y + 40)]
        
        s = pygame.Surface((150, 150), pygame.SRCALPHA)
        # Dibujar silueta fantasmal
        pygame.draw.polygon(s, (150, 255, 200, 80), [(p[0]-x+75, p[1]-y+75) for p in points])
        pygame.draw.circle(s, (150, 255, 200, 100), (75 + int(off_x), 40), 25)
        
        # Ojos vacíos
        pygame.draw.circle(s, (0, 0, 0, 150), (75 + int(off_x) - 10, 35), 4)
        pygame.draw.circle(s, (0, 0, 0, 150), (75 + int(off_x) + 10, 35), 4)
        pygame.draw.ellipse(s, (0, 0, 0, 150), (75 + int(off_x) - 5, 50, 10, 20)) # Boca grito
        
        self.screen.blit(s, (x - cam_x - 75, y - cam_y - 75), special_flags=pygame.BLEND_RGB_ADD)
        
        if g["phrase"]:
            self.draw_world_text_glitch(self.font_small, g["phrase"], x, y - 80, cam_x, cam_y, (150, 255, 150), intensity=0.8)

    def draw(self):
        self.screen.fill(config.BLACK)
        cam_x, cam_y = int(self.camera_x), int(self.camera_y)
        
        # Grid Holográfico de fondo
        grid_size = 100
        start_x = (cam_x // grid_size) * grid_size
        start_y = (cam_y // grid_size) * grid_size
        
        for x in range(start_x, cam_x + config.SCREEN_WIDTH + grid_size, grid_size):
            pygame.draw.line(self.screen, (30, 30, 40), (x - cam_x, 0), (x - cam_x, config.SCREEN_HEIGHT))
        for y in range(start_y, cam_y + config.SCREEN_HEIGHT + grid_size, grid_size):
            pygame.draw.line(self.screen, (30, 30, 40), (0, y - cam_y), (config.SCREEN_WIDTH, y - cam_y))
            
        # Muros del mundo
        border_rect = pygame.Rect(0 - cam_x, 0 - cam_y, self.world_width, self.world_height)
        pygame.draw.rect(self.screen, config.WALL_COLOR, border_rect, 20)
        
        # Dibujar Fantasmas (Solo si Sombra)
        if self.player.char_type == "sombra":
            for g in self.ghosts: self._draw_ghost(g, cam_x, cam_y)
            
        # Dibujar Partículas
        for p in self.particles:
            color = p["color"]
            if p["type"] == "fire":
                if p["life"] > 60: color = (255, 255, 100) 
                elif p["life"] > 30: color = (255, 100, 0)
                else: color = (80, 0, 0) 
            
            surf = pygame.Surface((int(p["size"])*2, int(p["size"])*2), pygame.SRCALPHA)
            pygame.draw.circle(surf, (*color, 200), (int(p["size"]), int(p["size"])), int(p["size"]))
            self.screen.blit(surf, (p["x"] - cam_x - p["size"], p["y"] - cam_y - p["size"]), special_flags=pygame.BLEND_RGB_ADD)
            
        # Dibujar Jugador
        self.player.draw(self.screen, cam_x, cam_y)
        
        # Efecto de Castigo (Pantalla Roja)
        if self.punishment_mode > 0 and self.punishment_mode % 4 < 2:
            self.screen.fill(config.RED_BLOOD) 
        else:
            # --- SISTEMA DE ILUMINACIÓN ACÚSTICA ---
            darkness = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            darkness.fill((0, 0, 0, 250)) # Casi oscuridad total
            
            # Recortar visión del jugador
            pygame.draw.circle(darkness, (0, 0, 0, 0), (int(self.player.x - cam_x), int(self.player.y - cam_y)), int(self.vision_radius))
            
            # Recortar luz de fuego
            for p in self.particles:
                if p["type"] == "fire":
                    pygame.draw.circle(darkness, (0, 0, 0, 0), (int(p["x"] - cam_x), int(p["y"] - cam_y)), int(p["size"] * 2.5))
            
            # Recortar pulsos de eco
            for p in self.pulses:
                pygame.draw.circle(darkness, (0, 0, 0, 0), (int(p["x"] - cam_x), int(p["y"] - cam_y)), int(p["radius"]))
                
            # Sombra ve fantasmas en la oscuridad
            if self.player.char_type == "sombra":
                for g in self.ghosts:
                    pygame.draw.circle(darkness, (0, 0, 0, 0), (g["x"]-cam_x, g["y"]-cam_y), 30)
            
            self.screen.blit(darkness, (0, 0))
        
        # Dibujar las ondas de Eco sobre la oscuridad
        for p in self.pulses:
            p["radius"] += 10
            surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
            # Desvanecer borde
            alpha = max(0, 200 - int(p["radius"] * 0.5))
            pygame.draw.circle(surf, (*p["color"], alpha), (int(p["x"] - cam_x), int(p["y"] - cam_y)), int(p["radius"]), 5)
            self.screen.blit(surf, (0, 0), special_flags=pygame.BLEND_RGB_ADD)
            
        self.pulses = [p for p in self.pulses if p["radius"] < p["max_radius"]]
        
        # UI
        self.draw_text_shadow(self.font_small, f"COMANDO: {self.last_cmd_display}", config.LIGHT_BLUE, 10, 10)
        if self.saving_timer > 0:
             self.draw_centered_text(self.font_medium, "GUARDANDO...", config.YELLOW_ICON, config.SCREEN_WIDTH//2, config.SCREEN_HEIGHT - 50)
             
        self.screen.blit(self.vignette_surf, (0, 0))
        self.draw_fade()