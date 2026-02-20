# main.py
import pygame
import sys
import os
import config
import database
# Importamos escenas desde sus archivos respectivos
from scenes import BootSequence, WarningScene, MenuScene
from level_zero import LevelZeroScene
from demo_level import DemoScene

def main():
    database.init_db()
    
    # Inicializar Pygame y Audio
    # Frecuencia 44100Hz, 16bit, stereo, buffer 2048
    pygame.mixer.pre_init(44100, -16, 2, 2048)
    pygame.init()
    pygame.mixer.init()

    screen = pygame.display.set_mode((config.SCREEN_WIDTH, config.SCREEN_HEIGHT))
    pygame.display.set_caption(config.TITLE)
    clock = pygame.time.Clock()

    music_file = "menu_theme.mp3" 
    if not os.path.exists(music_file): music_file = "menu_theme.ogg"
    if os.path.exists(music_file):
        try:
            pygame.mixer.music.load(music_file)
            pygame.mixer.music.set_volume(0.6)
        except Exception as e: print(f"Error musica: {e}")

    # Diccionario de Escenas
    scenes_dict = {
        config.STATE_BOOT: BootSequence,      
        config.STATE_WARNING: WarningScene,
        config.STATE_MENU: MenuScene,
        config.STATE_LEVEL_ZERO: LevelZeroScene, # Viene de level_zero.py
        config.STATE_DEMO: DemoScene             # Viene de demo_level.py
    }

    current_state = config.STATE_BOOT 
    active_scene = scenes_dict[current_state](screen)

    running = True
    while running:
        events = pygame.event.get()
        for event in events:
            if event.type == pygame.QUIT:
                running = False

        # Música dinámica
        if (current_state == config.STATE_DEMO or current_state == config.STATE_LEVEL_ZERO) and pygame.mixer.music.get_busy():
            pygame.mixer.music.fadeout(1500)

        active_scene.process_events(events)
        active_scene.update()

        if active_scene.next_state is not None:
            if active_scene.next_state == config.STATE_QUIT:
                running = False
                continue

            # Gestión de música al volver al menú
            if (current_state == config.STATE_DEMO or current_state == config.STATE_LEVEL_ZERO) and active_scene.next_state == config.STATE_MENU:
                if os.path.exists(music_file):
                     try: pygame.mixer.music.play(loops=-1, fade_ms=1000)
                     except: pass

            current_state = active_scene.next_state
            active_scene = scenes_dict[current_state](screen)

        active_scene.draw()
        pygame.display.flip()
        clock.tick(config.FPS)

    pygame.mixer.quit()
    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()