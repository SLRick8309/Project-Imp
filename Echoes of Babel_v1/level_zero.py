# level_zero.py
import pygame
import config
import threading
import queue
import time
import random
import json
import math
from scenes import Scene, CURRENT_SESSION, AUDIO_AVAILABLE
from entities import Player

try:
    import pyaudio
    from vosk import Model, KaldiRecognizer
except ImportError:
    pass

class LevelZeroScene(Scene):
    def __init__(self, screen):
        super().__init__(screen)
        # ESTADO DEL PRÓLOGO
        self.phase = "SETUP" 
        self.dialogue_queue = [] 
        
        # Configuración Visual: LABORATORIO LIMPIO (Antes del accidente)
        self.lab_color = (200, 200, 220) # Gris clínico brillante
        self.floor_color = (230, 230, 240)
        
        # Aris Thorne (Jugador) - Sin vendas, bata limpia
        self.player = Player(config.SCREEN_WIDTH//2, config.SCREEN_HEIGHT//2 + 100)
        self.player.set_character("cero") 
        
        self.command_queue = queue.Queue()
        self.audio_running = True
        
        # Efectos
        self.glitch_intensity = 0.0
        self.shake_screen = 0
        self.energy_pulse = 0
        self.blackout = False
        self.end_timer = 0
        
        # Iniciar secuencia narrativa
        self.start_prologue()
        
        if AUDIO_AVAILABLE:
            threading.Thread(target=self.listener, daemon=True).start()

    def start_prologue(self):
        # Fase 1: Calibración
        self.phase = "CALIBRATION"
        self.trigger_dialogue("Dr. Thorne, iniciemos la prueba de voz del Vox Dei.", "elena", 300)
        self.trigger_dialogue("Por favor, diga 'SINTAXIS' para calibrar el emisor.", "elena", 300, delay=120)

    def listener(self):
        while self.audio_running:
            stream = None
            p = None
            try:
                model = Model("model")
                # Gramática específica para el prólogo
                grammar = '["sintaxis", "iniciar", "secuencia", "detener", "abortar", "elena", "hola", "[unk]"]'
                rec = KaldiRecognizer(model, 16000, grammar)
                p = pyaudio.PyAudio()
                stream = p.open(format=pyaudio.paInt16, channels=1, rate=16000, input=True, frames_per_buffer=4096)
                stream.start_stream()
                
                while self.audio_running:
                    data = stream.read(4096, exception_on_overflow=False)
                    if rec.AcceptWaveform(data): pass
                    else:
                        partial = json.loads(rec.PartialResult()).get("partial", "")
                        if partial:
                            words = partial.split()
                            for w in words:
                                self.command_queue.put(w)
                            rec.Reset()
            except Exception: time.sleep(0.5)
            finally:
                if stream: 
                    try: stream.stop_stream(); stream.close()
                    except: pass
                if p:
                    try: p.terminate()
                    except: pass

    def trigger_dialogue(self, text, speaker="elena", duration=240, delay=0):
        """Sistema de diálogo con delay opcional"""
        if delay > 0:
            threading.Timer(delay / 60.0, lambda: self._add_dialogue(text, speaker, duration)).start()
        else:
            self._add_dialogue(text, speaker, duration)

    def _add_dialogue(self, text, speaker, duration):
        color = config.LIGHT_BLUE if speaker == "elena" else config.DARK_GRAY
        label = "DRA. ELENA VANCE" if speaker == "elena" else "DR. ARIS THORNE"
        
        # Audio feedback simulado
        import scenes
        if scenes.voice_engine: scenes.voice_engine.speak(text, speaker)
            
        self.dialogue_queue.append({
            "text": text, 
            "color": color, 
            "timer": duration, 
            "speaker": label
        })

    def update(self):
        self.update_fade()
        
        # Efecto de pulso de energía (La máquina)
        self.energy_pulse = (math.sin(pygame.time.get_ticks() * 0.005) + 1) * 0.5
        
        # Gestión de diálogos
        if self.dialogue_queue:
            self.dialogue_queue[0]["timer"] -= 1
            if self.dialogue_queue[0]["timer"] <= 0:
                self.dialogue_queue.pop(0)

        # Procesar Comandos de Voz Narrativos
        while not self.command_queue.empty():
            cmd = self.command_queue.get()
            
            if self.phase == "CALIBRATION" and cmd == "sintaxis":
                self.phase = "ARGUMENT"
                self.trigger_dialogue("Calibración al 100%. Resonancia estable.", "elena")
                self.trigger_dialogue("Aris... los escáneres del Sector 9 muestran anomalías graves.", "elena", delay=180)
                self.trigger_dialogue("No importa. Estamos a punto de reescribir la historia.", "aris", delay=360)
                self.trigger_dialogue("Diga 'INICIAR SECUENCIA' para activar el Núcleo.", "elena", delay=540)
            
            elif self.phase == "ARGUMENT" and (cmd == "iniciar" or cmd == "secuencia"):
                self.phase = "THE_EVENT"
                # Inicio del Caos
                self.trigger_dialogue("Activando Vox Dei... ¡Espera! ¡La lectura es infinita!", "elena")
                self.trigger_dialogue("¡ARIS, DETENLO! ¡VA A ESTALLAR!", "elena", delay=120)
                self.shake_screen = 5
                self.glitch_intensity = 0.2
            
            elif self.phase == "THE_EVENT":
                # Cualquier sonido acelera el colapso
                self.shake_screen += 2
                self.glitch_intensity += 0.1
                if self.shake_screen > 20:
                    self.phase = "COLLAPSE"

        # Lógica de Colapso Visual
        if self.phase == "THE_EVENT":
            if random.random() < 0.05:
                self.trigger_dialogue("ERROR CRÍTICO. CONTENCIÓN FALLIDA.", "sistema", 60)
            if self.shake_screen < 50:
                self.shake_screen += 0.1
            else:
                self.phase = "COLLAPSE"

        if self.phase == "COLLAPSE":
            self.blackout = True
            self.end_timer += 1
            if self.end_timer > 180: # 3 segundos de oscuridad
                self.change_scene(config.STATE_DEMO) # Transición al juego real (despertar ciego)

    def draw_lab_environment(self, cx, cy):
        # Fondo limpio (Clínico)
        self.screen.fill(self.lab_color)
        
        # Suelo con reflejo
        pygame.draw.rect(self.screen, self.floor_color, (0, cy + 100, config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        
        # La Máquina (Vox Dei Prototype) - Centro
        machine_x = config.SCREEN_WIDTH // 2
        machine_y = cy - 100
        
        # Anillos giratorios (Estado normal vs Caos)
        color_ring = (50, 50, 50) if self.phase != "THE_EVENT" else (200, 0, 0)
        width_ring = 2 if self.phase != "THE_EVENT" else 5
        
        for i in range(3):
            radius = 100 + i * 40 + (self.energy_pulse * 20 if self.phase == "THE_EVENT" else 0)
            pygame.draw.circle(self.screen, color_ring, (machine_x, machine_y), int(radius), width_ring)
        
        # Núcleo
        core_color = (0, 200, 255) if self.phase != "THE_EVENT" else (255, 255, 255)
        if self.phase == "THE_EVENT" and random.random() < 0.5: core_color = (0, 0, 0) # Parpadeo
        pygame.draw.circle(self.screen, core_color, (machine_x, machine_y), 50)

    def draw(self):
        # Shake effect
        off_x = random.randint(-int(self.shake_screen), int(self.shake_screen))
        off_y = random.randint(-int(self.shake_screen), int(self.shake_screen))
        
        bg_surf = pygame.Surface((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
        
        # Dibujar entorno
        cx, cy = config.SCREEN_WIDTH // 2, config.SCREEN_HEIGHT // 2
        self.draw_lab_environment(cx, cy)
        
        # Dibujar a Aris (Limpio)
        # Nota: Usamos una versión simplificada aquí ya que Player() dibuja la versión "enferma"
        # Esto es solo un placeholder visual para la cinemática
        p_rect = pygame.Rect(cx - 20, cy + 50, 40, 90)
        pygame.draw.rect(self.screen, (255, 255, 255), p_rect) # Bata blanca limpia
        pygame.draw.circle(self.screen, (200, 180, 170), (cx, cy + 40), 15) # Cabeza normal
        
        # Aplicar Shake copiando la pantalla
        if self.shake_screen > 0:
            screen_copy = self.screen.copy()
            self.screen.fill((0,0,0))
            self.screen.blit(screen_copy, (off_x, off_y))
            
        # Glitch overlay
        if self.glitch_intensity > 0:
            for _ in range(int(self.glitch_intensity * 10)):
                gx = random.randint(0, config.SCREEN_WIDTH)
                gy = random.randint(0, config.SCREEN_HEIGHT)
                gw = random.randint(10, 100)
                gh = random.randint(2, 10)
                pygame.draw.rect(self.screen, (random.randint(0,255), 0, 0), (gx, gy, gw, gh))

        # UI de Diálogo (Estilo limpio/futurista)
        if self.dialogue_queue:
            d = self.dialogue_queue[0]
            bw, bh = 1000, 150
            bx = (config.SCREEN_WIDTH - bw) // 2
            by = config.SCREEN_HEIGHT - 200
            
            # Caja blanca semitransparente
            s = pygame.Surface((bw, bh), pygame.SRCALPHA)
            s.fill((255, 255, 255, 230))
            self.screen.blit(s, (bx, by))
            
            # Borde azul clínico
            pygame.draw.rect(self.screen, (0, 100, 200), (bx, by, bw, bh), 2)
            
            # Nombre
            name_surf = self.font_medium.render(d["speaker"], True, (0, 50, 100))
            self.screen.blit(name_surf, (bx + 20, by - 30))
            
            # Texto
            text_surf = self.font_sub.render(d["text"], True, (10, 10, 10))
            self.screen.blit(text_surf, (bx + 30, by + 50))

        # Blackout final
        if self.blackout:
            self.screen.fill((0, 0, 0))
            
        self.draw_fade()