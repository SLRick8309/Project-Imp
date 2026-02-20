# entities.py
import pygame
import math
import random
import config

class Player:
    def __init__(self, x, y):
        self.x = x
        self.y = y
        self.vx = 0
        self.vy = 0
        
        # Dirección de la mirada
        self.facing_x = 0
        self.facing_y = 1
        
        # Estados
        self.speed_mode = "caminar"
        self.is_crouching = False 
        self.is_moving = False
        
        self.pulse_timer = 0.0
        self.char_type = "cero" # "cero" o "sombra"
        
        # Animación
        self.anim_frame = 0
        self.anim_timer = 0

    def set_direction(self, dx, dy):
        self.vx = dx
        self.vy = dy
        if dx != 0 or dy != 0:
            self.facing_x = dx
            self.facing_y = dy
        self.is_moving = True

    def set_speed_mode(self, mode):
        self.speed_mode = mode
        if mode == "correr": self.is_crouching = False
        elif mode == "caminar": self.is_crouching = False
        # Si es lento, no necesariamente es crouch, pero asumimos sigilo

    def crouch(self):
        self.is_crouching = True
        self.speed_mode = "lento"

    def stand_up(self):
        self.is_crouching = False
        self.speed_mode = "caminar"

    def stop(self):
        self.vx = 0
        self.vy = 0
        self.is_moving = False

    def set_character(self, char_type):
        self.char_type = char_type

    def update(self):
        # Velocidad base
        speed = config.SPEED_WALK
        if self.speed_mode == "correr": speed = config.SPEED_RUN
        elif self.speed_mode == "lento": speed = config.SPEED_SLOW
        
        if self.is_crouching: speed = config.SPEED_SLOW

        # Movimiento
        self.x += self.vx * speed
        self.y += self.vy * speed

        # Límites del mundo
        self.x = max(50, min(self.x, config.WORLD_WIDTH - 50))
        self.y = max(50, min(self.y, config.WORLD_HEIGHT - 50))

        # Animación (Pulsación del implante / Glitch de sombra)
        self.pulse_timer += 0.1
        if self.is_moving:
            self.anim_timer += 1
        
    def draw(self, surface, cam_x, cam_y):
        cx, cy = int(self.x - cam_x), int(self.y - cam_y)
        
        if self.char_type == "cero":
            self._draw_zero(surface, cx, cy)
        else:
            self._draw_shadow(surface, cx, cy)

    def _draw_zero(self, surface, cx, cy):
        """Dibuja al Sujeto Cero: Paciente con vendas e implante brillante"""
        
        # 1. Cuerpo (Bata de hospital) - Verde pálido / Azulado
        # Ajuste de altura si está agachado
        height_mod = 0.7 if self.is_crouching else 1.0
        
        # Efecto de caminar (pequeño balanceo)
        bobbing = math.sin(self.anim_timer * 0.2) * 3 if self.is_moving else 0
        
        # Bata (Polígono simple para dar forma de ropa holgada)
        gown_color = (100, 130, 120)
        points = [
            (cx - 15, cy - 20 * height_mod + bobbing), # Hombro Izq
            (cx + 15, cy - 20 * height_mod + bobbing), # Hombro Der
            (cx + 20, cy + 25 * height_mod + bobbing), # Base Der
            (cx - 20, cy + 25 * height_mod + bobbing)  # Base Izq
        ]
        pygame.draw.polygon(surface, gown_color, points)
        
        # 2. Cabeza (Círculo color piel pálida)
        head_y = cy - 30 * height_mod + bobbing
        pygame.draw.circle(surface, (200, 190, 180), (cx, int(head_y)), 12)
        
        # 3. Vendas en los ojos (Franja blanca/gris)
        pygame.draw.rect(surface, (220, 220, 220), (cx - 13, int(head_y) - 4, 26, 8))
        
        # 4. Implante "Vox Dei" (Garganta) - Brillo Cian
        throat_y = head_y + 15
        pulse_size = 3 + math.sin(self.pulse_timer * 0.2) * 2
        
        # Luz del implante (con blend para que brille)
        glow_surf = pygame.Surface((40, 40), pygame.SRCALPHA)
        pygame.draw.circle(glow_surf, (0, 255, 255, 100), (20, 20), int(6 + pulse_size * 2)) # Halo
        pygame.draw.circle(glow_surf, (200, 255, 255, 255), (20, 20), int(3)) # Núcleo
        surface.blit(glow_surf, (cx - 20, int(throat_y) - 20), special_flags=pygame.BLEND_RGB_ADD)

    def _draw_shadow(self, surface, cx, cy):
        """Dibuja a La Sombra: Silueta oscura con glitch y ojos rojos"""
        
        # Efecto Glitch: Dibujar copias desplazadas con baja opacidad
        for i in range(3):
            off_x = random.randint(-5, 5)
            off_y = random.randint(-5, 5)
            
            # Silueta distorsionada
            ghost_surf = pygame.Surface((50, 80), pygame.SRCALPHA)
            points = [
                (25, 0 + random.randint(0,5)), 
                (50, 20), 
                (40 + random.randint(-5,5), 80), 
                (10 + random.randint(-5,5), 80), 
                (0, 20)
            ]
            # Color rojo oscuro semi-transparente para el glitch
            pygame.draw.polygon(ghost_surf, (50, 0, 0, 50), points)
            surface.blit(ghost_surf, (cx - 25 + off_x, cy - 40 + off_y))

        # Cuerpo Principal (Negro Absoluto)
        main_body_points = [
            (cx, cy - 45), # Cabeza
            (cx + 15, cy - 10), # Hombro
            (cx + 10, cy + 30), # Pie
            (cx - 10, cy + 30), # Pie
            (cx - 15, cy - 10)  # Hombro
        ]
        pygame.draw.polygon(surface, (0, 0, 0), main_body_points)
        
        # Ojos (Dos puntos rojos brillantes)
        eye_y = cy - 35
        # Parpadeo random
        if random.random() > 0.05:
            pygame.draw.circle(surface, (255, 0, 0), (cx - 5, eye_y), 2)
            pygame.draw.circle(surface, (255, 0, 0), (cx + 5, eye_y), 2)
            
        # Aura de distorsión (Líneas horizontales)
        for _ in range(5):
            ly = random.randint(cy - 40, cy + 40)
            lx = random.randint(cx - 30, cx + 30)
            w = random.randint(5, 20)
            pygame.draw.line(surface, config.GLITCH_COLOR, (lx, ly), (lx + w, ly), 1)