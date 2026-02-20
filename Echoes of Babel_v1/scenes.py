# scenes.py
import pygame
import config
import time
import random
import threading
import queue
import json
import struct
import math
import array
import os 
import database 
from entities import Player

try:
    import pyaudio
    from vosk import Model, KaldiRecognizer
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# --- MOTOR DE AUDIO HÍBRIDO ---
class VoiceEngine:
    def __init__(self):
        self.channels = {}
        try:
            pygame.mixer.set_reserved(2)
            self.channels['sombra'] = pygame.mixer.Channel(0)
            self.channels['elena'] = pygame.mixer.Channel(1)
        except:
            print("Error inicializando canales de voz")

        self.sound_cache = {}

    def _generate_noise_sound(self, duration=1.5, pitch=100, volume=0.5, style="shadow"):
        sample_rate = 44100
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)
        
        for i in range(n_samples):
            t = i / sample_rate
            if style == "shadow":
                envelope = 1.0 + 0.5 * math.sin(t * 10) 
                raw_noise = random.uniform(-1, 1)
                saw_wave = (i % int(sample_rate/pitch)) / (sample_rate/pitch) * 2 - 1
                val = (raw_noise * 0.8 + saw_wave * 0.2) * envelope
                val = int(val * 32767 * volume * 0.8) 
            else:
                freq = 400 + math.sin(t * 5) * 50
                sine_wave = math.sin(2 * math.pi * freq * t)
                digital_break = 1.0 if (i % 4000) < 3500 else 0.0
                val = int(sine_wave * 32767 * volume * 0.6 * digital_break)
            buf[i] = max(-32767, min(32767, val))
        return pygame.mixer.Sound(buffer=buf)

    def speak(self, text, character):
        cache_key = f"{character}_generic"
        if cache_key not in self.sound_cache:
            if character == "sombra":
                self.sound_cache[cache_key] = self._generate_noise_sound(1.5, 60, 0.8, "shadow")
            else:
                self.sound_cache[cache_key] = self._generate_noise_sound(0.8, 440, 0.4, "elena")
        
        sound = self.sound_cache[cache_key]
        if character in self.channels:
            vol_var = random.uniform(0.8, 1.0)
            self.channels[character].set_volume(vol_var)
            self.channels[character].play(sound)

voice_engine = None

CURRENT_SESSION = {
    "slot": 1,
    "should_load": False
}

# --- CLASE BASE ---
class Scene:
    def __init__(self, screen):
        global voice_engine
        if voice_engine is None:
            voice_engine = VoiceEngine()
            
        self.screen = screen
        self.update_fonts()
        self.next_state = None
        self.alpha = 255
        self.fade_state = "IN" 
        self.target_state = None 
        
        self.fog_particles = []
        for _ in range(40): 
            self.fog_particles.append(self._create_fog())

        self.vignette_surf = None
        self.noise_surf = None
        self._generate_vignette()
        self._generate_noise()
        self.click_sound = self._generate_mechanical_click()
        self.grid_offset_y = 0

    def update_fonts(self):
        self.font_large = pygame.font.SysFont("courier new", 70, bold=True)
        self.font_medium = pygame.font.SysFont("courier new", 36, bold=True)
        self.font_small = pygame.font.SysFont("courier new", 22, bold=True)
        self.font_sub = pygame.font.SysFont("courier new", 26, italic=True, bold=True)

    def _create_fog(self):
        return {
            "x": random.randint(-200, config.SCREEN_WIDTH + 200),
            "y": random.randint(-200, config.SCREEN_HEIGHT + 200),
            "radius": random.randint(200, 600),
            "speed_x": random.uniform(-0.2, 0.2),
            "speed_y": random.uniform(-0.1, 0.1),
            "alpha": random.randint(2, 8)
        }

    def _generate_vignette(self):
        self.vignette_surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        self.vignette_surf.fill((0, 0, 0, 255))
        hole = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        hole.fill((0, 0, 0, 0))
        pygame.draw.circle(hole, (0, 0, 0, 255), 
                           (config.SCREEN_WIDTH//2, config.SCREEN_HEIGHT//2), 
                           int(config.SCREEN_HEIGHT * 0.65)) 
        self.vignette_surf.blit(hole, (0, 0), special_flags=pygame.BLEND_RGBA_SUB)

    def _generate_noise(self):
        self.noise_surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(3000): 
            x = random.randint(0, config.SCREEN_WIDTH)
            y = random.randint(0, config.SCREEN_HEIGHT)
            alpha = random.randint(10, 60)
            self.noise_surf.set_at((x, y), (200, 200, 200, alpha))

    def _generate_mechanical_click(self):
        sample_rate = 44100
        duration = 0.04
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)
        for i in range(n_samples):
            t = i / n_samples
            val = int((random.random() - 0.5) * 10000 * (1-t))
            buf[i] = val
        return pygame.mixer.Sound(buffer=buf)

    def update_atmosphere(self):
        for fog in self.fog_particles:
            fog["x"] += fog["speed_x"]
            fog["y"] += fog["speed_y"]
            if fog["x"] < -600 or fog["x"] > config.SCREEN_WIDTH + 600:
                fog["x"] = random.randint(0, config.SCREEN_WIDTH)
            if fog["y"] < -600 or fog["y"] > config.SCREEN_HEIGHT + 600:
                fog["y"] = random.randint(0, config.SCREEN_HEIGHT)

    def draw_atmosphere(self, color_tint=None):
        bg_color = (5, 5, 8) if not color_tint else color_tint
        self.screen.fill(bg_color) 
        self.draw_tech_background()
        for fog in self.fog_particles:
            surf = pygame.Surface((fog["radius"]*2, fog["radius"]*2), pygame.SRCALPHA)
            color = (0, 0, 0, fog["alpha"]) if not color_tint else (30, 0, 0, fog["alpha"])
            pygame.draw.circle(surf, color, (fog["radius"], fog["radius"]), fog["radius"])
            self.screen.blit(surf, (fog["x"] - fog["radius"], fog["y"] - fog["radius"]))
        
        noise_x = random.randint(-50, 50)
        noise_y = random.randint(-50, 50)
        self.screen.blit(self.noise_surf, (noise_x, noise_y), special_flags=pygame.BLEND_RGBA_ADD)

    def draw_centered_text(self, font, text, color, cx, cy, shadow=True, glitch=False):
        surf = font.render(text, True, color)
        rect = surf.get_rect(center=(cx, cy))
        
        if shadow:
            shadow_surf = font.render(text, True, (0,0,0))
            shadow_rect = shadow_surf.get_rect(center=(cx+3, cy+3))
            self.screen.blit(shadow_surf, shadow_rect)
        
        if glitch and random.random() < 0.1:
            off_x = random.randint(-3, 3)
            off_y = random.randint(-3, 3)
            self.screen.blit(surf, (rect.x + off_x, rect.y + off_y))
        else:
            self.screen.blit(surf, rect)

    def draw_text_glitch(self, font, text, x, y, color=(255, 255, 255), intensity=1.0):
        t = pygame.time.get_ticks()
        offset_x = (random.random() - 0.5) * 15 * intensity if intensity > 0.5 else 0
        offset_y = (random.random() - 0.5) * 8 * intensity if intensity > 0.5 else 0
        
        if intensity > 0.1:
            r_surf = font.render(text, True, (255, 0, 0))
            self.screen.blit(r_surf, (x - 5 + offset_x, y + offset_y))
            b_surf = font.render(text, True, (0, 255, 255))
            self.screen.blit(b_surf, (x + 5 - offset_x, y - offset_y))
        
        main_surf = font.render(text, True, color)
        self.screen.blit(main_surf, (x + offset_x/2, y + offset_y/2))

    def draw_text_shadow(self, font, text, color, x, y):
        shadow = font.render(text, True, (0, 0, 0))
        self.screen.blit(shadow, (x + 4, y + 4))
        main_text = font.render(text, True, color)
        self.screen.blit(main_text, (x, y))
        
    def draw_tech_background(self):
        self.grid_offset_y = (self.grid_offset_y + 0.5) % 40
        color_grid = (20, 40, 50)
        for x in range(0, config.SCREEN_WIDTH, 40): 
            pygame.draw.line(self.screen, color_grid, (x, 0), (x, config.SCREEN_HEIGHT))
        for y in range(int(self.grid_offset_y) - 40, config.SCREEN_HEIGHT, 40): 
            pygame.draw.line(self.screen, color_grid, (0, y), (config.SCREEN_WIDTH, y))
        scan_y = (pygame.time.get_ticks() * 0.2) % config.SCREEN_HEIGHT
        pygame.draw.line(self.screen, (0, 50, 50), (0, scan_y), (config.SCREEN_WIDTH, scan_y), 2)

    def update_fade(self):
        if self.fade_state == "IN":
            self.alpha -= config.TRANSITION_SPEED
            if self.alpha <= 0:
                self.alpha = 0
                self.fade_state = "IDLE"
        elif self.fade_state == "OUT":
            self.alpha += config.TRANSITION_SPEED
            if self.alpha >= 255:
                self.alpha = 255
                self.next_state = self.target_state

    def draw_fade(self):
        if self.alpha > 0:
            veil = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
            veil.fill((0, 0, 0))
            veil.set_alpha(self.alpha)
            self.screen.blit(veil, (0, 0))

    def change_scene(self, new_state):
        self.target_state = new_state
        self.fade_state = "OUT"
    
    def process_events(self, events): pass
    def update(self): pass
    def draw(self): pass

# --- CLASES DE ESCENAS ---

class BootSequence(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.target_lines = [
            "REGISTRO DE AUTOPSIA PSÍQUICA #99",
            "SUJETO: PACIENTE CERO",
            "---------------------------",
            "EL PACIENTE SE HA ARRANCADO LOS OJOS.",
            "AFIRMA QUE LA LUZ ES RUIDO.",
            "DICE QUE PUEDE VER CON LA VOZ.",
            "...",
            "LA OSCURIDAD ESTÁ VIVA.",
            "ELLOS VIENEN POR MÍ.",
            "NO... NO... NO...",
            "¡¡¡TE ENCONTRÉ!!!"
        ]
        self.current_lines = [""] * len(self.target_lines)
        self.line_idx = 0
        self.char_idx = 0
        self.char_timer = 0
        self.typing_complete = False
        self.finish_timer = 0
        self.jumpscare_active = False
        self.blackout_active = False
        self.screaming_sound = self._generate_scream_sound()

    def _generate_scream_sound(self):
        sample_rate = 44100
        duration = 0.8
        n_samples = int(sample_rate * duration)
        buf = array.array('h', [0] * n_samples)
        for i in range(n_samples):
            t = i/sample_rate
            saw = (i % 100) / 100.0 * 2 - 1
            noise = random.uniform(-1, 1)
            val = int((saw * 0.7 + noise * 0.3) * 30000 * (1-t))
            buf[i] = val
        return pygame.mixer.Sound(buffer=buf)

    def update(self):
        self.update_atmosphere()
        self.update_fade()
        if self.fade_state == "IDLE":
            if not self.typing_complete:
                self.char_timer += 1
                if self.char_timer >= 2: 
                    self.char_timer = 0
                    target = self.target_lines[self.line_idx]
                    if self.char_idx < len(target):
                        char = target[self.char_idx]
                        self.current_lines[self.line_idx] += char
                        if len(self.current_lines[self.line_idx]) > 1:
                            last_char = self.current_lines[self.line_idx][-2]
                            if last_char not in target:
                                correct_char = target[self.char_idx - 1]
                                self.current_lines[self.line_idx] = self.current_lines[self.line_idx][:-2] + correct_char + char
                        self.char_idx += 1
                        if char != " ":
                            self.click_sound.set_volume(random.uniform(0.6, 0.9))
                            self.click_sound.play()
                    else:
                        self.line_idx += 1
                        self.char_idx = 0
                        if self.line_idx >= len(self.target_lines):
                            self.typing_complete = True
            else:
                self.finish_timer += 1
                if self.finish_timer == 30: 
                    self.jumpscare_active = True
                    self.screaming_sound.play()
                if self.finish_timer == 70:
                    self.jumpscare_active = False
                    self.blackout_active = True
                if self.finish_timer > 120:
                    self.change_scene(config.STATE_WARNING)

    def draw_jumpscare_face(self):
        cx, cy = config.SCREEN_WIDTH//2, config.SCREEN_HEIGHT//2
        off_x = random.randint(-20, 20)
        off_y = random.randint(-20, 20)
        
        if random.random() < 0.5: 
            self.screen.fill((255, 255, 255)) 
        else: 
            self.screen.fill((50, 0, 0)) 
            
        pygame.draw.ellipse(self.screen, config.BLACK, (cx - 300 + off_x, cy - 400 + off_y, 600, 800))
        pygame.draw.circle(self.screen, config.RED_BLOOD, (cx - 150 + off_x, cy - 100 + off_y), 80)
        pygame.draw.circle(self.screen, config.RED_BLOOD, (cx + 150 + off_x, cy - 100 + off_y), 80)
        pygame.draw.circle(self.screen, config.BLACK, (cx - 150 + off_x, cy - 100 + off_y), 40)
        pygame.draw.circle(self.screen, config.BLACK, (cx + 150 + off_x, cy - 100 + off_y), 40)
        pygame.draw.ellipse(self.screen, config.RED_BLOOD, (cx - 100 + off_x, cy + 100 + off_y, 200, 400))

    def draw(self):
        if self.blackout_active:
            self.screen.fill(config.BLACK)
            return
        if self.jumpscare_active and self.finish_timer < 80:
            self.draw_jumpscare_face()
            return 
        self.draw_atmosphere()
        start_y = config.SCREEN_HEIGHT // 2 - (len(self.target_lines) * 20)
        start_x = config.SCREEN_WIDTH // 2 - 400
        for i, line in enumerate(self.current_lines):
            color = config.WHITE
            if "NO ESCUCHES" in self.target_lines[i] or "TE ENCONTRÉ" in self.target_lines[i]:
                color = config.RED_BLOOD
            elif "REGISTRO" in self.target_lines[i] or "SUJETO" in self.target_lines[i]:
                color = config.YELLOW_ICON
            offset = 0
            if "NO ESCUCHES" in line or "TE ENCONTRÉ" in line:
                offset = random.randint(-3, 3)
            txt = self.font_small.render(line, True, color)
            self.screen.blit(txt, (start_x + offset, start_y + i * 40))
        self.draw_fade()

class WarningScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        if pygame.mixer.get_init():
            pygame.mixer.music.stop()
        self.pulse_val = 0
        self.command_queue = queue.Queue()
        self.audio_running = False
        self.mic_status = "Di 'CONFIRMAR'..." 
        self.exit_timer = 0
        self.exiting = False
        self.target_lines = ["EXPERIENCIA DE TERROR AUDITIVO (+13)", "", "La supervivencia depende de tu oído.", "El audio 3D revelará enemigos invisibles.", "Jugar sin audífonos es imposible.", "", "Tu voz es tu única arma.", "", "> Di 'CONFIRMAR' <"] 
        if AUDIO_AVAILABLE:
            self.audio_running = True
            threading.Thread(target=self.audio_task, daemon=True).start()

    def audio_task(self):
        while self.audio_running:
            stream = None
            p = None
            try:
                model = Model("model")
                grammar = '["confirmar", "[unk]"]'
                rec = KaldiRecognizer(model, 16000, grammar)
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
                stream.start_stream()
                while self.audio_running:
                    data = stream.read(4096, exception_on_overflow=False) 
                    if rec.AcceptWaveform(data): pass
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if "confirmar" in partial:
                            self.command_queue.put("confirmar")
                            rec.Reset() 
            except Exception:
                time.sleep(0.5)
            finally:
                if stream: 
                    try: stream.stop_stream(); stream.close()
                    except Exception: pass
                if p: 
                    try: p.terminate()
                    except Exception: pass

    def update(self):
        self.update_atmosphere()
        self.update_fade()
        self.pulse_val = (math.sin(pygame.time.get_ticks() * 0.003) + 1) * 0.5 
        while not self.command_queue.empty():
            cmd = self.command_queue.get()
            if cmd == "confirmar" and not self.exiting:
                self.exiting = True
                self.exit_timer = 15 
        if self.exiting:
            self.exit_timer -= 1
            if self.exit_timer <= 0:
                self.audio_running = False
                if pygame.mixer.get_init():
                    try: pygame.mixer.music.play(-1, fade_ms=3000) 
                    except Exception: pass
                self.change_scene(config.STATE_MENU)

    def draw_headphones(self, cx, cy):
        color = config.WHITE
        scale = 1.8 
        pygame.draw.arc(self.screen, color, (cx - 50*scale, cy - 50*scale, 100*scale, 90*scale), 0, 3.14, 10)
        pygame.draw.rect(self.screen, (30,30,30), (cx - 65*scale, cy - 10*scale, 30*scale, 45*scale), border_radius=10)
        pygame.draw.rect(self.screen, color, (cx - 65*scale, cy - 10*scale, 30*scale, 45*scale), 4, border_radius=10)
        pygame.draw.rect(self.screen, (30,30,30), (cx + 35*scale, cy - 10*scale, 30*scale, 45*scale), border_radius=10)
        pygame.draw.rect(self.screen, color, (cx + 35*scale, cy - 10*scale, 30*scale, 45*scale), 4, border_radius=10)

    def draw(self):
        self.draw_atmosphere()
        cx = config.SCREEN_WIDTH // 2
        cy = config.SCREEN_HEIGHT // 2
        total_h = 350
        start_y = (config.SCREEN_HEIGHT - total_h) // 2
        icon_y = start_y + 50
        alpha_wave = int(150 * (1 - self.pulse_val))
        for i in range(3):
            off = i * 20 + (self.pulse_val * 10)
            pygame.draw.arc(self.screen, (200, 200, 200, alpha_wave), (cx - 150 - off, icon_y - 50, 50, 100), 1.5, 4.7, 3)
            pygame.draw.arc(self.screen, (200, 200, 200, alpha_wave), (cx + 100 + off, icon_y - 50, 50, 100), -1.5, 1.5, 3)
        self.draw_headphones(cx, icon_y)
        text_y = icon_y + 120
        for i, line in enumerate(self.target_lines):
            color = config.YELLOW_ICON if i == 0 else (config.LIGHT_BLUE if "CONFIRMAR" in line else config.WHITE)
            font = self.font_medium if i == 0 else self.font_small
            txt = font.render(line, True, color)
            txt_x = cx - txt.get_width() // 2
            if "CONFIRMAR" in line:
                alpha = abs(math.sin(pygame.time.get_ticks() * 0.005)) * 255
                txt.set_alpha(int(alpha))
            self.screen.blit(txt, (txt_x, text_y + i * 35))
        self.draw_fade()


# --- MENÚ PRINCIPAL ---
class MenuScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        self.command_queue = queue.Queue()
        self.audio_running = False
        self.mic_status = "Iniciando..."
        
        self.menu_state = "title" 
        self.glitch_level = 0 
        self.glitch_timer = 0
        self.glitch_cooldown = 30 
        self.shadow_whispers = ["AYÚDAME", "NO ME DEJES", "ARIS...", "¿ESCUCHAS?", "EL POZO", "ELLOS VIENEN", "SÁCAME DE AQUÍ", "ERROR", "NO HAY SALIDA"]
        self.current_whisper = ""
        self.corrupt_options = {"Nueva Partida": ["NO ENTRES", "HUYE", "YA ES TARDE", "MUERTE"], "Salir": ["NO PUEDES", "QUÉDATE", "JAMÁS", "CERRADO"]}
        
        self.test_db_level = -60.0
        self.last_detected_text = ""
        self.current_volume = 1.0 
        self.current_graphics_mode = "Ventana"
        
        # Gestión de partidas
        self.slots_data = {}
        self.target_slot = 0
        self.waiting_confirmation = False
        self.loading_progress = 0.0 
        self.loading_complete = False 
        self.loading_text_timer = 0
        self.loading_lines = ["INICIANDO NEURAL_LINK...", "CONECTANDO A VOX_DEI...", "SINCRONIZANDO ECOS...", "DESENCRIPTANDO REALIDAD...", "LEYES FISICAS: OVERRIDE", "MEMORIA: OK"]
        self.current_loading_line = ""
        self.has_saves = False
        self.auto_start_timer = 0 
        
        # LÓGICA CÓDIGO SECRETO (Konami por voz)
        self.cheat_sequence = []
        self.target_sequence = ["arriba", "arriba", "abajo", "abajo", "izquierda", "derecha", "izquierda", "derecha", "b", "a", "empezar"]
        self.cheat_active = False
        self.cheat_timer = 0
        self.show_hint_timer = 0  # Timer para mostrar la pista "¿Di el código?"

        self._check_saves()
        if AUDIO_AVAILABLE:
            self.audio_running = True
            threading.Thread(target=self.audio_task, daemon=True).start()

    def _check_saves(self):
        all_slots = database.get_slots_info()
        self.has_saves = False
        for s_id, data in all_slots.items():
            if not data["empty"]:
                self.has_saves = True
                break

    def calculate_decibels(self, data):
        count = len(data) // 2
        if count == 0: return -60.0
        try:
            shorts = struct.unpack(f"<{count}h", data)
            sum_squares = sum(s**2 for s in shorts)
            rms = math.sqrt(sum_squares / count)
            if rms > 0: return 20 * math.log10(rms) - 90
        except Exception: pass
        return -60.0

    def audio_task(self):
        while self.audio_running:
            stream = None
            p = None
            try:
                model = Model("model")
                # AÑADIDO: "código", "codigo", "secreto", "clave" para activar la pista
                grammar = '["iniciar", "nueva partida", "cargar partida", "configuración", "opciones", "salir", "audio", "sonido", "gráficos", "pantalla", "ventana", "completa", "bordes", "atrás", "finalizar", "prueba", "microfono", "volumen", "subir", "bajar", "diez", "veinte", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa", "cien", "uno", "dos", "tres", "confirmar", "cancelar", "continuar", "arriba", "abajo", "izquierda", "derecha", "b", "a", "empezar", "start", "código", "codigo", "secreto", "clave", "[unk]"]'
                rec = KaldiRecognizer(model, 16000, grammar)
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
                stream.start_stream()
                self.mic_status = "Listo"
                
                while self.audio_running:
                    data = stream.read(4096, exception_on_overflow=False)
                    self.test_db_level = self.calculate_decibels(data)
                    
                    if rec.AcceptWaveform(data): pass
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if partial:
                            self.last_detected_text = partial
                            cmd = ""
                            
                            words_priority = [
                                "uno", "dos", "tres", "confirmar", "cancelar", "continuar",
                                "atrás", "salir", "finalizar", "iniciar", "nueva partida", "cargar partida",
                                "configuración", "opciones", "audio", "sonido", "gráficos", "pantalla",
                                "ventana", "completa", "bordes", "prueba", "microfono",
                                "subir", "bajar", "volumen",
                                # Konami + Triggers
                                "arriba", "abajo", "izquierda", "derecha", "b", "a", "empezar", "start",
                                "código", "codigo", "secreto", "clave"
                            ]
                            
                            for w in words_priority:
                                if w in partial:
                                    if w == "finalizar": cmd = "atrás"
                                    elif w == "opciones": cmd = "configuración"
                                    elif w == "sonido": cmd = "audio"
                                    elif w == "pantalla": cmd = "gráficos"
                                    elif w == "start": cmd = "empezar"
                                    elif w in ["código", "codigo", "secreto", "clave"]: cmd = "trigger_hint"
                                    else: cmd = w
                                    break 
                            
                            if not cmd:
                                 if "volumen" in partial:
                                     if "diez" in partial: cmd = "vol 10"
                                     elif "cincuenta" in partial: cmd = "vol 50"
                                     elif "cien" in partial: cmd = "vol 100"
                                     elif "subir" in partial: cmd = "subir volumen"
                                     elif "bajar" in partial: cmd = "bajar volumen"
                                 elif "subir" in partial: cmd = "subir volumen"
                                 elif "bajar" in partial: cmd = "bajar volumen"

                            if cmd:
                                self.command_queue.put(cmd)
                                rec.Reset()
            except Exception:
                time.sleep(0.5)
            finally:
                if stream: 
                    try: stream.stop_stream(); stream.close()
                    except Exception: pass
                if p: 
                    try: p.terminate()
                    except Exception: pass

    def process_events(self, events):
        for e in events:
            if e.type == pygame.KEYDOWN and e.key == pygame.K_RETURN: 
                self.audio_running = False
                self.change_scene(config.STATE_LEVEL_ZERO)

    def _update_resolution(self, mode):
        new_surface = None
        if mode == "fullscreen":
            info = pygame.display.Info()
            w, h = info.current_w, info.current_h
            new_surface = pygame.display.set_mode((w, h), pygame.FULLSCREEN)
        elif mode == "window":
            os.environ['SDL_VIDEO_CENTERED'] = '1'
            w, h = 1280, 720
            new_surface = pygame.display.set_mode((w, h))
        elif mode == "noframe":
            info = pygame.display.Info()
            w, h = info.current_w, info.current_h
            new_surface = pygame.display.set_mode((w, h), pygame.NOFRAME)
            
        if new_surface:
            config.SCREEN_WIDTH = w
            config.SCREEN_HEIGHT = h
            self.screen = new_surface
            self._generate_vignette()
            self.update_fonts() 

    def update(self):
        self.update_atmosphere()
        self.update_fade()

        # Glitch Logic
        if "settings" not in self.menu_state:
            if self.glitch_cooldown > 0: self.glitch_cooldown -= 1
            else:
                if random.randint(0, 100) < 5:
                    roll = random.randint(0, 100)
                    if roll < 50: self.glitch_level = 1; self.current_whisper = random.choice(self.shadow_whispers); self.glitch_timer = random.randint(20, 60)
                    elif roll < 85: self.glitch_level = 2; self.current_whisper = "ERROR CRÍTICO"; self.glitch_timer = random.randint(10, 30)
                    else: self.glitch_level = 3; self.current_whisper = "¡TE VEO!"; self.glitch_timer = random.randint(5, 15) 
                    self.glitch_cooldown = random.randint(60, 200)
            if self.glitch_timer > 0:
                self.glitch_timer -= 1
                if self.glitch_timer <= 0: self.glitch_level = 0 
        else:
            self.glitch_level = 0 
        
        # --- ESTADO DE CARGA ---
        if self.menu_state == "loading":
            if not self.loading_complete:
                if random.random() < 0.2: self.loading_progress += random.uniform(2, 8)
                else: self.loading_progress += 0.2 
                
                self.loading_text_timer += 1
                if self.loading_text_timer > 30:
                    self.loading_text_timer = 0
                    self.current_loading_line = random.choice(self.loading_lines)

                if self.loading_progress >= 100:
                    self.loading_progress = 100
                    self.loading_complete = True 
                    self.auto_start_timer = 40 
                    if self.cheat_active: pass
                    elif not CURRENT_SESSION["should_load"]:
                        database.save_game(CURRENT_SESSION["slot"], 0, 1500, 1500, "cero")
            else:
                self.auto_start_timer -= 1
                if self.auto_start_timer <= 0:
                    self.audio_running = False
                    if self.cheat_active: self.change_scene(config.STATE_DEMO)
                    elif CURRENT_SESSION["should_load"]: self.change_scene(config.STATE_LEVEL_ZERO)
                    else: self.change_scene(config.STATE_LEVEL_ZERO)
            return

        # Timers de UI Secreta
        if self.cheat_timer > 0:
            self.cheat_timer -= 1
            if self.cheat_timer <= 0: self.cheat_active = False
        
        if self.show_hint_timer > 0:
            self.show_hint_timer -= 1

        while not self.command_queue.empty():
            cmd = self.command_queue.get()
            
            # --- DETECCIÓN DE CÓDIGO KONAMI ---
            if self.menu_state in ["title", "options"]:
                # Trigger de Pista
                if cmd == "trigger_hint":
                    self.show_hint_timer = 240 # 4 segundos de mensaje (aumentado para que dé tiempo de leer)
                    self.click_sound.play()
                
                # Secuencia
                if cmd in ["arriba", "abajo", "izquierda", "derecha", "b", "a", "empezar"]:
                    self.cheat_sequence.append(cmd)
                    if len(self.cheat_sequence) > len(self.target_sequence):
                        self.cheat_sequence.pop(0)
                    
                    if self.cheat_sequence == self.target_sequence:
                        self.cheat_active = True
                        self.cheat_timer = 180
                        self.mic_status = "¡MODO DIOS DESBLOQUEADO!"
                        self.show_hint_timer = 0 # Ocultar pista si ya salió
            
            # Comandos normales
            if self.menu_state == "title":
                if cmd == "iniciar": self.menu_state = "options"
            
            elif self.menu_state == "options":
                if cmd == "nueva partida":
                    self.menu_state = "slot_selection_new"
                    self.slots_data = database.get_slots_info()
                elif cmd == "cargar partida" and self.has_saves:
                    self.menu_state = "slot_selection_load"
                    self.slots_data = database.get_slots_info()
                elif cmd == "configuración" or cmd == "opciones":
                    self.menu_state = "settings_main"
                elif cmd == "salir":
                    self.audio_running = False
                    self.change_scene("quit")
            
            elif self.menu_state == "slot_selection_new":
                if self.waiting_confirmation:
                    if cmd == "confirmar":
                        CURRENT_SESSION["slot"] = self.target_slot
                        CURRENT_SESSION["should_load"] = False
                        self.menu_state = "loading"
                    elif cmd == "cancelar": self.waiting_confirmation = False
                else:
                    if cmd == "atrás" or cmd == "cancelar": self.menu_state = "options"
                    elif cmd == "uno": self.target_slot = 1; self._check_overwrite(1)
                    elif cmd == "dos": self.target_slot = 2; self._check_overwrite(2)
                    elif cmd == "tres": self.target_slot = 3; self._check_overwrite(3)

            elif self.menu_state == "slot_selection_load":
                if cmd == "atrás" or cmd == "cancelar": self.menu_state = "options"
                else:
                    t = 0
                    if cmd == "uno": t = 1
                    elif cmd == "dos": t = 2
                    elif cmd == "tres": t = 3
                    if t > 0 and not self.slots_data[t]["empty"]:
                        CURRENT_SESSION["slot"] = t; CURRENT_SESSION["should_load"] = True; self.menu_state = "loading"
            
            elif self.menu_state == "settings_main":
                if cmd == "audio" or cmd == "sonido": self.menu_state = "settings_audio"
                elif cmd == "gráficos" or cmd == "pantalla": self.menu_state = "settings_graphics"
                elif cmd == "atrás": self.menu_state = "options"
            
            elif self.menu_state == "settings_audio":
                if cmd == "atrás": self.menu_state = "settings_main"
                if cmd == "prueba" or cmd == "microfono": self.menu_state = "settings_audio_test"
                if "vol" in cmd:
                    try: val = int(cmd.split(" ")[1]); self.current_volume = val / 100.0; pygame.mixer.music.set_volume(self.current_volume)
                    except Exception: pass
            
            elif self.menu_state == "settings_audio_test":
                 if cmd == "atrás": self.menu_state = "settings_audio"

            elif self.menu_state == "settings_graphics":
                if cmd == "atrás": self.menu_state = "settings_main"
                if cmd == "ventana": self._update_resolution("window")
                elif cmd == "pantalla completa": self._update_resolution("fullscreen")
                elif cmd == "sin bordes": self._update_resolution("noframe")

    def _check_overwrite(self, slot_id):
        if not self.slots_data[slot_id]["empty"]: self.waiting_confirmation = True
        else: CURRENT_SESSION["slot"] = slot_id; CURRENT_SESSION["should_load"] = False; self.menu_state = "loading"

    def draw_audio_meter(self, cx, cy):
        bar_width = 400
        bar_height = 40 
        pygame.draw.rect(self.screen, (20, 20, 20), (cx - bar_width//2, cy, bar_width, bar_height))
        normalized = max(0, min(1, (self.test_db_level + 60) / 60))
        fill_width = int(normalized * bar_width)
        color = (int(255 * normalized), int(255 * (1-normalized)), 0)
        pygame.draw.rect(self.screen, color, (cx - bar_width//2, cy, fill_width, bar_height))
        pygame.draw.rect(self.screen, config.WHITE, (cx - bar_width//2, cy, bar_width, bar_height), 2)
    
    def draw_scary_face(self):
        cx, cy = config.SCREEN_WIDTH//2, config.SCREEN_HEIGHT//2
        surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT), pygame.SRCALPHA)
        for i in range(3):
            pygame.draw.ellipse(surf, (80, 0, 0, 180), (cx - 150, cy - 100, 100, 200)) 
            pygame.draw.ellipse(surf, (80, 0, 0, 180), (cx + 50, cy - 100, 100, 200)) 
            pygame.draw.ellipse(surf, (40, 0, 0, 200), (cx - 100, cy + 100, 200, 300)) 
        self.screen.blit(surf, (0, 0))

    def draw(self):
        tint = None
        if self.glitch_level == 2: tint = (80, 0, 0)
        elif self.glitch_level == 3: tint = (0, 0, 0)
        self.draw_atmosphere(tint)
        
        if self.glitch_level > 0:
            shake_screen_x = random.randint(-10, 10) * self.glitch_level
            shake_screen_y = random.randint(-10, 10) * self.glitch_level
            current_screen = self.screen.copy()
            self.screen.fill(config.BLACK)
            self.screen.blit(current_screen, (shake_screen_x, shake_screen_y))
        
        if self.glitch_level == 3: self.draw_scary_face()
        
        cx = config.SCREEN_WIDTH // 2
        cy = config.SCREEN_HEIGHT // 2
        
        # --- PANTALLA DE CARGA ---
        if self.menu_state == "loading":
            self.draw_centered_text(self.font_large, "ACCEDIENDO MEMORIA...", config.WHITE, cx, cy - 100, glitch=True)
            bar_w = 600; bar_h = 30; bar_x = cx - bar_w // 2; bar_y = cy
            pygame.draw.rect(self.screen, config.DARK_GRAY, (bar_x, bar_y, bar_w, bar_h))
            fill_w = int(bar_w * (self.loading_progress / 100.0))
            pygame.draw.rect(self.screen, config.LIGHT_BLUE, (bar_x, bar_y, fill_w, bar_h))
            pygame.draw.rect(self.screen, config.WHITE, (bar_x, bar_y, bar_w, bar_h), 2)
            perc_text = f"{int(self.loading_progress)}%"
            self.draw_centered_text(self.font_medium, perc_text, config.WHITE, cx, cy + 50)
            self.draw_centered_text(self.font_small, f"> {self.current_loading_line}", config.TERMINAL_GREEN, cx, cy + 100)
            if self.cheat_active:
                self.draw_centered_text(self.font_medium, ">> PROTOCOLO KONAMI ACTIVADO <<", config.RED_BLOOD, cx, cy + 150, glitch=True)
            return

        # --- VISUALIZACIÓN DE SECRETOS (LAYER SUPERIOR) ---
        # 1. Mensaje de éxito del código (Top)
        if self.cheat_active:
            self.draw_text_glitch(self.font_medium, ">> ACCESO DE ADMINISTRADOR CONCEDIDO <<", cx, 80, config.GREEN_GLOW, 2.0)
        
        # 2. Pista de "Di la secuencia" (Bottom-Center, muy visible)
        if self.show_hint_timer > 0:
            # Fondo oscuro para resaltar
            hint_w = 1000
            hint_h = 80
            bg_rect = pygame.Rect(cx - hint_w//2, config.SCREEN_HEIGHT - 150, hint_w, hint_h)
            pygame.draw.rect(self.screen, (0, 0, 0, 230), bg_rect)
            pygame.draw.rect(self.screen, config.TERMINAL_AMBER, bg_rect, 3)
            # Dibuja la pista EXACTA requerida
            self.draw_centered_text(self.font_medium, "SECUENCIA REQUERIDA: [ ARRIBA ARRIBA ABAJO ABAJO... ]", config.TERMINAL_AMBER, cx, config.SCREEN_HEIGHT - 110, glitch=True)

        # --- TITULO ---
        if self.menu_state == "title":
            title_text = "ECHOES OF BABEL"
            title_color = config.WHITE
            glitch_int = 0.0
            if self.glitch_level == 1:
                glitch_int = 1.0 
                if random.random() < 0.2: title_text = self.current_whisper
            elif self.glitch_level == 2:
                glitch_int = 3.0; title_color = config.RED_BLOOD; title_text = random.choice(self.shadow_whispers)
            elif self.glitch_level == 3:
                glitch_int = 8.0; title_color = (150, 0, 0); title_text = "SINTAXIS ROTA"
            self.draw_text_glitch(self.font_large, title_text, cx - 350, 150, title_color, glitch_int)
            self.draw_centered_text(self.font_medium, "DI 'INICIAR'", config.LIGHT_BLUE, cx, cy + 100, glitch=True)

        # --- OPCIONES ---
        elif self.menu_state == "options":
            self.draw_text_glitch(self.font_large, "ECHOES OF BABEL", cx - 350, 150, config.WHITE, 0)
            self.draw_centered_text(self.font_medium, "NUEVA PARTIDA", config.WHITE, cx, cy - 60)
            c_load = config.WHITE if self.has_saves else config.DARK_GRAY
            self.draw_centered_text(self.font_medium, "CARGAR PARTIDA", c_load, cx, cy + 20)
            self.draw_centered_text(self.font_medium, "CONFIGURACIÓN", config.WHITE, cx, cy + 100)
            self.draw_centered_text(self.font_medium, "SALIR", config.RED_BLOOD, cx, cy + 180)
        
        # --- SLOTS ---
        elif "slot_selection" in self.menu_state:
            self.draw_centered_text(self.font_medium, "SELECCIONA RANURA", config.LIGHT_BLUE, cx, 100)
            card_w = 300; gap = 20; total_width = (card_w * 3) + (gap * 2); start_x = cx - (total_width // 2)
            for i in range(1, 4):
                current_x = start_x + (i-1) * (card_w + gap)
                rect = pygame.Rect(current_x, cy - 100, card_w, 200)
                color = config.SLOT_FILLED if not self.slots_data[i]["empty"] else config.SLOT_EMPTY
                if self.menu_state == "slot_selection_new" and self.waiting_confirmation and self.target_slot == i:
                    color = config.SLOT_WARNING 
                pygame.draw.rect(self.screen, color, rect, border_radius=5)
                pygame.draw.rect(self.screen, config.WHITE, rect, 2, border_radius=5)
                self.draw_centered_text(self.font_medium, str(i), config.WHITE, rect.centerx, rect.centery)
                if not self.slots_data[i]["empty"]:
                    self.draw_centered_text(self.font_small, f"{self.slots_data[i]['progress']}%", config.WHITE, rect.centerx, rect.bottom - 30)
                else:
                    self.draw_centered_text(self.font_small, "VACÍA", (150,150,150), rect.centerx, rect.bottom - 30)
            if self.waiting_confirmation:
                 self.draw_centered_text(self.font_medium, "¿SOBRESCRIBIR? DI 'CONFIRMAR'", config.RED_BLOOD, cx, cy + 200, glitch=True)
            else:
                 self.draw_centered_text(self.font_small, "DI 'UNO', 'DOS' O 'TRES'", config.WHITE, cx, cy + 200)

        elif self.menu_state == "settings_main":
            self.draw_centered_text(self.font_medium, "CONFIGURACIÓN", config.LIGHT_BLUE, cx, 100)
            self.draw_centered_text(self.font_medium, "AUDIO", config.WHITE, cx, cy - 50)
            self.draw_centered_text(self.font_medium, "GRÁFICOS", config.WHITE, cx, cy + 50)
            self.draw_centered_text(self.font_medium, "ATRÁS", config.YELLOW_ICON, cx, cy + 150)
        
        elif self.menu_state == "settings_audio":
            self.draw_centered_text(self.font_medium, "AUDIO", config.LIGHT_BLUE, cx, 100)
            vol_perc = int(self.current_volume * 100)
            self.draw_centered_text(self.font_medium, f"Volumen General: {vol_perc}%", config.WHITE, cx, cy - 50)
            self.draw_centered_text(self.font_medium, "PRUEBA MICRÓFONO", config.WHITE, cx, cy + 50)
            self.draw_centered_text(self.font_medium, "ATRÁS", config.YELLOW_ICON, cx, cy + 150)

        elif self.menu_state == "settings_audio_test":
            self.draw_centered_text(self.font_medium, "PRUEBA ACTIVA", config.GREEN_GLOW, cx, 150)
            self.draw_centered_text(self.font_small, "Habla fuerte...", config.WHITE, cx, 250)
            self.draw_audio_meter(cx, 350)
            self.draw_centered_text(self.font_small, f"Detectado: '{self.last_detected_text}'", config.WHITE, cx, 420)
            self.draw_centered_text(self.font_medium, "ATRÁS", config.YELLOW_ICON, cx, 550)
            
        elif self.menu_state == "settings_graphics":
            self.draw_centered_text(self.font_medium, "GRÁFICOS", config.LIGHT_BLUE, cx, 100)
            self.draw_centered_text(self.font_medium, "VENTANA", config.WHITE, cx, cy - 60)
            self.draw_centered_text(self.font_medium, "COMPLETA", config.WHITE, cx, cy + 20)
            self.draw_centered_text(self.font_medium, "BORDES", config.WHITE, cx, cy + 100)
            self.draw_centered_text(self.font_medium, "ATRÁS", config.YELLOW_ICON, cx, cy + 200)
            
        if self.mic_status:
            self.draw_text_shadow(self.font_small, f"Mic: {self.mic_status}", (150, 150, 150), 40, config.SCREEN_HEIGHT - 50)
        
        self.screen.blit(self.vignette_surf, (0, 0))
        self.draw_fade()