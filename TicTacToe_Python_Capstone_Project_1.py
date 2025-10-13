# main.py -- Tic Tac Toe with sound + persistent settings menu + RGB sliders + numeric input boxes
# Single-file runnable. Put in the project folder and run with Python 3.9+ and pygame installed.

import os
import sys
import random
import json
import pygame
from typing import Optional, Dict, Tuple

# -------------------------
# Basic setup
# -------------------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.font.init()
pygame.mixer.set_num_channels(8)

# Files & defaults
SETTINGS_FILE = os.path.join(BASE_DIR, "settings.json")
SOUND_DIR = os.path.join(BASE_DIR, "assets", "sounds")

DEFAULT_EFFECT_VOLUME = 0.9
DEFAULT_MUSIC_VOLUME = 0.25
DEFAULT_X_COLOR = (0, 255, 120)
DEFAULT_O_COLOR = (0, 200, 230)

# Runtime globals (will be loaded/saved)
EFFECT_VOLUME = DEFAULT_EFFECT_VOLUME
MUSIC_VOLUME = DEFAULT_MUSIC_VOLUME
X_COLOR = DEFAULT_X_COLOR
O_COLOR = DEFAULT_O_COLOR

# Screen constants
WIDTH, HEIGHT = 600, 600
LINE_WIDTH = 10
BOARD_ROWS = 3
BOARD_COLS = 3
SQUARE_SIZE = WIDTH // BOARD_COLS
CIRCLE_RADIUS = SQUARE_SIZE // 3
CIRCLE_WIDTH = 15
CROSS_WIDTH = 25
SPACE = SQUARE_SIZE // 4

BG_COLOR = (10, 10, 10)
LINE_COLOR = (150, 150, 150)
TEXT_COLOR = (255, 255, 255)
MENU_BG = (30, 30, 30)
END_BG = (10, 10, 10)
END_TEXT = (255, 255, 255)

HIGHLIGHT_COLOR = (255, 50, 50)
HIGHLIGHT_WIDTH = 12
HIGHLIGHT_FLASHES = 6
HIGHLIGHT_DELAY_MS = 120
PULSE_STEPS = 6
PULSE_PULSES = 3
PULSE_TOTAL_MS = 500
PULSE_LINE_WIDTH = 8

# Fonts
FONT_SMALL = pygame.font.SysFont(None, 18)
FONT = pygame.font.SysFont(None, 28)
FONT_MED = pygame.font.SysFont(None, 36)
FONT_LARGE = pygame.font.SysFont(None, 60)

# Pygame display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic Tac Toe")

# Game state
board: list[list[Optional[str]]] = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
game_mode = None  # "PVP", "AI_EASY", "AI_HARD"
player = "X"
running = False

x_wins = 0
o_wins = 0
draws = 0

_volume_changed_time = 0
_VOLUME_HUD_DURATION_MS = 1500

# -------------------------
# Sound loading helpers (robust)
# -------------------------
SOUNDS: Dict[str, Optional[pygame.mixer.Sound]] = {}

def candidates_for(name: str):
    # try various likely filename variants (handles files like move.wav.wav)
    base = os.path.join(SOUND_DIR, name)
    exts = ['', '.wav', '.ogg', '.wav.wav', '.ogg.ogg']
    return [base + e for e in exts]

def safe_load_sound_by_name(name: str) -> Optional[pygame.mixer.Sound]:
    for path in candidates_for(name):
        if os.path.exists(path):
            try:
                return pygame.mixer.Sound(path)
            except Exception as e:
                print(f"Warning loading sound {path}: {e}")
    return None

def verify_sounds_exist(sound_dir, expected_files):
    print("\n🔊 Verifying sound assets...")
    for filename in expected_files:
        ok = False
        for cand in candidates_for(filename):
            if os.path.exists(cand):
                ok = True
                break
        print(f"  {'✅' if ok else '⚠️'} {filename}")

def init_sounds():
    expected_files = ["move", "move_ai", "win", "draw", "menu_select", "lose", "bgm"]
    verify_sounds_exist(SOUND_DIR, expected_files)
    SOUNDS['move'] = safe_load_sound_by_name("move")
    SOUNDS['move_ai'] = safe_load_sound_by_name("move_ai") or SOUNDS['move']
    SOUNDS['win'] = safe_load_sound_by_name("win")
    SOUNDS['draw'] = safe_load_sound_by_name("draw")
    SOUNDS['menu'] = safe_load_sound_by_name("menu_select")
    SOUNDS['lose'] = safe_load_sound_by_name("lose")
    # set volumes
    for s in SOUNDS.values():
        if s:
            try:
                s.set_volume(EFFECT_VOLUME)
            except Exception:
                pass
    # bgm
    for cand in candidates_for("bgm"):
        if os.path.exists(cand):
            try:
                pygame.mixer.music.load(cand)
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
            except Exception as e:
                print(f"Warning: couldn't load bgm: {e}")
            break

def play_sound(key, rel_volume=1.0):
    snd = SOUNDS.get(key)
    if snd:
        try:
            snd.set_volume(max(0.0, min(1.0, EFFECT_VOLUME * rel_volume)))
            snd.play()
        except Exception as e:
            print(f"Sound play error for {key}: {e}")

def start_bgm(loop=True):
    try:
        if pygame.mixer.music.get_busy():
            return
        loops = -1 if loop else 0
        pygame.mixer.music.play(loops=loops, fade_ms=300)
    except Exception as e:
        print("BGM play error:", e)

def stop_bgm(fade_ms=300):
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except Exception:
        pass

# -------------------------
# Settings persistence
# -------------------------
def load_settings():
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR, x_wins, o_wins, draws
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            EFFECT_VOLUME = float(data.get("effect_volume", DEFAULT_EFFECT_VOLUME))
            MUSIC_VOLUME = float(data.get("music_volume", DEFAULT_MUSIC_VOLUME))
            X_COLOR = tuple(data.get("x_color", DEFAULT_X_COLOR))
            O_COLOR = tuple(data.get("o_color", DEFAULT_O_COLOR))
            x_wins = int(data.get("x_wins", 0))
            o_wins = int(data.get("o_wins", 0))
            draws = int(data.get("draws", 0))
        except Exception as e:
            print("Warning: couldn't load settings:", e)

def save_settings():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump({
                "effect_volume": EFFECT_VOLUME,
                "music_volume": MUSIC_VOLUME,
                "x_color": X_COLOR,
                "o_color": O_COLOR,
                "x_wins": x_wins,
                "o_wins": o_wins,
                "draws": draws
            }, f, indent=2)
    except Exception as e:
        print("Warning: couldn't save settings:", e)

# -------------------------
# Game helpers (drawing & logic)
# -------------------------
def draw_text_center(text, font, color, surf, x, y):
    surf_text = font.render(text, True, color)
    rect = surf_text.get_rect(center=(x, y))
    surf.blit(surf_text, rect)

def reset_board():
    global board, player, running
    board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
    player = "X"
    running = True
    screen.fill(BG_COLOR)
    draw_lines()
    display_scoreboard()
    pygame.display.update()

def draw_lines():
    screen.fill(BG_COLOR)
    pygame.draw.line(screen, LINE_COLOR, (0, SQUARE_SIZE), (WIDTH, SQUARE_SIZE), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (0, 2 * SQUARE_SIZE), (WIDTH, 2 * SQUARE_SIZE), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (SQUARE_SIZE, 0), (SQUARE_SIZE, HEIGHT), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (2 * SQUARE_SIZE, 0), (2 * SQUARE_SIZE, HEIGHT), LINE_WIDTH)

def draw_figures():
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            if board[r][c] == "O":
                pygame.draw.circle(screen, O_COLOR, (int(c * SQUARE_SIZE + SQUARE_SIZE // 2),
                                                    int(r * SQUARE_SIZE + SQUARE_SIZE // 2)),
                                   CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif board[r][c] == "X":
                pygame.draw.line(screen, X_COLOR,
                                 (c * SQUARE_SIZE + SPACE, r * SQUARE_SIZE + SPACE),
                                 (c * SQUARE_SIZE + SQUARE_SIZE - SPACE, r * SQUARE_SIZE + SQUARE_SIZE - SPACE),
                                 CROSS_WIDTH)
                pygame.draw.line(screen, X_COLOR,
                                 (c * SQUARE_SIZE + SPACE, r * SQUARE_SIZE + SQUARE_SIZE - SPACE),
                                 (c * SQUARE_SIZE + SQUARE_SIZE - SPACE, r * SQUARE_SIZE + SPACE),
                                 CROSS_WIDTH)

def mark_square(row, col, mark):
    board[row][col] = mark

def available_square(row, col):
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS and board[row][col] is None

def is_board_full():
    return all(board[r][c] is not None for r in range(BOARD_ROWS) for c in range(BOARD_COLS))

def get_winning_line(player_mark):
    for r in range(BOARD_ROWS):
        if board[r][0] == board[r][1] == board[r][2] == player_mark:
            return [(r, 0), (r, 1), (r, 2)]
    for c in range(BOARD_COLS):
        if board[0][c] == board[1][c] == board[2][c] == player_mark:
            return [(0, c), (1, c), (2, c)]
    if board[0][0] == board[1][1] == board[2][2] == player_mark:
        return [(0, 0), (1, 1), (2, 2)]
    if board[0][2] == board[1][1] == board[2][0] == player_mark:
        return [(0, 2), (1, 1), (2, 0)]
    return None

def cell_center(rc):
    r, c = rc
    return (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2)

def draw_winning_line(cells, flash_times=HIGHLIGHT_FLASHES, flash_delay=HIGHLIGHT_DELAY_MS):
    if not cells: return
    start = cell_center(cells[0])
    end = cell_center(cells[-1])
    for i in range(flash_times):
        draw_lines(); draw_figures(); display_scoreboard()
        if i % 2 == 0:
            pygame.draw.line(screen, HIGHLIGHT_COLOR, start, end, HIGHLIGHT_WIDTH)
        pygame.display.update(); pygame.time.delay(flash_delay)

def draw_pulsing_circles(cells, pulses=PULSE_PULSES, total_ms=PULSE_TOTAL_MS, steps=PULSE_STEPS, line_width=PULSE_LINE_WIDTH):
    if not cells: return
    centers = [cell_center(c) for c in cells]
    min_r = CIRCLE_RADIUS + 6
    max_r = int(SQUARE_SIZE * 0.45)
    ms_per_half = max(10, total_ms // 2)
    ms_per_step = max(10, ms_per_half // max(1, steps - 1))
    for _ in range(pulses):
        for s in range(steps):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines(); draw_figures(); display_scoreboard()
            for c in centers: pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update(); pygame.time.delay(ms_per_step)
        for s in reversed(range(steps)):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines(); draw_figures(); display_scoreboard()
            for c in centers: pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update(); pygame.time.delay(ms_per_step)

def check_win(player_mark):
    return get_winning_line(player_mark) is not None

def display_scoreboard():
    txt = f"X Wins: {x_wins}   O Wins: {o_wins}   Draws: {draws}"
    screen.blit(FONT.render(txt, True, TEXT_COLOR), (10, 10))

def display_volume_hud_if_needed():
    global _volume_changed_time
    if _volume_changed_time == 0:
        return
    elapsed = pygame.time.get_ticks() - _volume_changed_time
    if elapsed > _VOLUME_HUD_DURATION_MS:
        return
    hud_w, hud_h = 210, 56
    hud_surf = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
    hud_surf.fill((0, 0, 0, 170))
    screen.blit(hud_surf, (WIDTH - hud_w - 10, 10))
    ev_text = FONT_SMALL.render(f"Effects: {int(EFFECT_VOLUME*100)}%", True, (255,255,255))
    mv_text = FONT_SMALL.render(f"Music:   {int(MUSIC_VOLUME*100)}%", True, (255,255,255))
    screen.blit(ev_text, (WIDTH - hud_w + 8, 18))
    screen.blit(mv_text, (WIDTH - hud_w + 8, 36))

# -------------------------
# Win/draw handlers
# -------------------------
def handle_win(player_mark):
    global x_wins, o_wins
    if player_mark == "X":
        x_wins += 1
        play_sound('win')
    else:
        o_wins += 1
        # play lose.wav when AI wins
        if SOUNDS.get('lose'):
            play_sound('lose')
        else:
            play_sound('win')  # fallback

def handle_draw():
    global draws
    draws += 1
    play_sound('draw')

# -------------------------
# AI
# -------------------------
def ai_move_easy():
    empty = [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None]
    if empty:
        r, c = random.choice(empty)
        mark_square(r, c, "O")
        play_sound('move_ai')

def evaluate():
    if check_win("O"): return 1
    if check_win("X"): return -1
    return 0

def minimax(depth, is_maximizing):
    score = evaluate()
    if score != 0: return score
    if is_board_full(): return 0
    if is_maximizing:
        best = -999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "O"
                    best = max(best, minimax(depth+1, False))
                    board[r][c] = None
        return best
    else:
        best = 999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "X"
                    best = min(best, minimax(depth+1, True))
                    board[r][c] = None
        return best

def ai_move_hard():
    best_score = -999; best_move = None
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            if board[r][c] is None:
                board[r][c] = "O"
                score = minimax(0, False)
                board[r][c] = None
                if score > best_score:
                    best_score = score
                    best_move = (r, c)
    if best_move:
        mark_square(best_move[0], best_move[1], "O")
        play_sound('move_ai')

# -------------------------
# Menu & screens
# -------------------------
def draw_menu():
    screen.fill(MENU_BG)
    draw_text_center("Tic Tac Toe", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, 60)
    options = [
        "1. Player vs Player",
        "2. Player vs AI (Easy)",
        "3. Player vs AI (Hard)",
        "4. Quit",
        "5. Settings"
    ]
    y = 160
    for o in options:
        draw_text_center(o, FONT, TEXT_COLOR, screen, WIDTH//2, y)
        y += 44
    pygame.display.update()

def menu_loop():
    global game_mode
    while True:
        draw_menu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
                elif event.key == pygame.K_1:
                    play_sound('menu'); game_mode = "PVP"; return
                elif event.key == pygame.K_2:
                    play_sound('menu'); game_mode = "AI_EASY"; return
                elif event.key == pygame.K_3:
                    play_sound('menu'); game_mode = "AI_HARD"; return
                elif event.key == pygame.K_4:
                    play_sound('menu'); save_settings(); pygame.quit(); sys.exit()
                elif event.key == pygame.K_5:
                    play_sound('menu'); settings_screen()

# -------------------------
# Settings UI (RGB sliders + numeric inputs + preview)
# -------------------------
def clamp01(x): return max(0.0, min(1.0, x))

def change_volume(delta: float):
    global EFFECT_VOLUME, MUSIC_VOLUME, _volume_changed_time
    EFFECT_VOLUME = clamp01(EFFECT_VOLUME + delta)
    MUSIC_VOLUME = clamp01(MUSIC_VOLUME + delta)
    try:
        for k in SOUNDS:
            if SOUNDS[k]:
                SOUNDS[k].set_volume(EFFECT_VOLUME)
    except Exception:
        pass
    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass
    _volume_changed_time = pygame.time.get_ticks()
    save_settings()

def settings_screen():
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR
    running = True
    dragging = None
    selected_input = None  # ("X" or "O", channel_index)
    input_text = ""
    active_color = None

    DEFAULT_X_COLOR = (255, 105, 180)
    DEFAULT_O_COLOR = (0, 255, 120)

    color_presets = {
        "Red": (255, 0, 0),
        "Green": (0, 255, 0),
        "Blue": (0, 100, 255),
        "Yellow": (255, 255, 0),
        "Pink": (255, 105, 180),
        "White": (255, 255, 255)
    }

    margin_top = HEIGHT * 0.08
    section_gap = HEIGHT * 0.08
    slider_gap = HEIGHT * 0.06
    col_x_left = WIDTH * 0.25
    col_x_right = WIDTH * 0.75
    slider_width = WIDTH * 0.25
    slider_height = 12

    def update_color(target, index, mouse_x, base_x):
        rel = max(0, min(1, (mouse_x - base_x) / slider_width))
        val = int(rel * 255)
        if target == "X":
            c = list(X_COLOR)
            c[index] = val
            return tuple(c)
        else:
            c = list(O_COLOR)
            c[index] = val
            return tuple(c)

    def clamp(v):
        return max(0, min(255, v))

    def apply_input(target, idx, text):
        nonlocal X_COLOR, O_COLOR
        if text.isdigit():
            val = clamp(int(text))
            if target == "X":
                c = list(X_COLOR)
                c[idx] = val
                X_COLOR = tuple(c)
            else:
                c = list(O_COLOR)
                c[idx] = val
                O_COLOR = tuple(c)

    while running:
        screen.fill((20, 20, 20))
        draw_text("Settings", font_large, (255, 255, 255), screen, WIDTH // 2, margin_top)

        # --- Volume Controls ---
        vol_y = margin_top + section_gap
        draw_text(f"Effects: {int(EFFECT_VOLUME * 100)}%", font_medium, (255, 255, 255), screen, col_x_left, vol_y)
        draw_text(f"Music:  {int(MUSIC_VOLUME * 100)}%", font_medium, (255, 255, 255), screen, col_x_right, vol_y)

        pygame.draw.rect(screen, (100, 200, 100),
                         (col_x_left - slider_width // 2, vol_y + 30, slider_width * EFFECT_VOLUME, slider_height))
        pygame.draw.rect(screen, (100, 200, 100),
                         (col_x_right - slider_width // 2, vol_y + 30, slider_width * MUSIC_VOLUME, slider_height))

        # --- Color Section ---
        color_y = vol_y + section_gap * 1.5
        draw_text("X Color", font_medium, X_COLOR, screen, col_x_left, color_y)
        draw_text("O Color", font_medium, O_COLOR, screen, col_x_right, color_y)

        slider_rects = {"X": [], "O": []}
        input_boxes = {"X": [], "O": []}

        # --- RGB Sliders and Numeric Inputs ---
        for i, (label, idx) in enumerate(zip(["R", "G", "B"], range(3))):
            y_pos = color_y + 50 + i * slider_gap

            # Left side (X)
            base_x_left = col_x_left - 150
            pygame.draw.rect(screen, (100, 100, 100), (base_x_left, y_pos, slider_width, slider_height))
            fill_x = int(slider_width * (X_COLOR[idx] / 255))
            pygame.draw.rect(screen, X_COLOR, (base_x_left, y_pos, fill_x, slider_height))
            pygame.draw.circle(screen, (255, 255, 255),
                               (base_x_left + fill_x, y_pos + slider_height // 2), 6)
            draw_text(label, font_small, (255, 255, 255), screen, base_x_left - 30, y_pos + 5)
            val_rect_x = pygame.Rect(col_x_left + 120, y_pos - 4, 50, 24)
            pygame.draw.rect(screen, (60, 60, 60), val_rect_x)
            pygame.draw.rect(screen, (200, 200, 200), val_rect_x, 1)
            val_text = str(X_COLOR[idx]) if not (selected_input == ("X", idx) and input_text) else input_text
            draw_text(val_text, font_small, (255, 255, 255), screen, val_rect_x.centerx, val_rect_x.centery)
            slider_rects["X"].append(pygame.Rect(base_x_left, y_pos, slider_width, slider_height))
            input_boxes["X"].append(val_rect_x)

            # Right side (O)
            base_x_right = col_x_right - 150
            pygame.draw.rect(screen, (100, 100, 100), (base_x_right, y_pos, slider_width, slider_height))
            fill_o = int(slider_width * (O_COLOR[idx] / 255))
            pygame.draw.rect(screen, O_COLOR, (base_x_right, y_pos, fill_o, slider_height))
            pygame.draw.circle(screen, (255, 255, 255),
                               (base_x_right + fill_o, y_pos + slider_height // 2), 6)
            draw_text(label, font_small, (255, 255, 255), screen, base_x_right - 30, y_pos + 5)
            val_rect_o = pygame.Rect(col_x_right + 120, y_pos - 4, 50, 24)
            pygame.draw.rect(screen, (60, 60, 60), val_rect_o)
            pygame.draw.rect(screen, (200, 200, 200), val_rect_o, 1)
            val_text = str(O_COLOR[idx]) if not (selected_input == ("O", idx) and input_text) else input_text
            draw_text(val_text, font_small, (255, 255, 255), screen, val_rect_o.centerx, val_rect_o.centery)
            slider_rects["O"].append(pygame.Rect(base_x_right, y_pos, slider_width, slider_height))
            input_boxes["O"].append(val_rect_o)

        # --- Preview Boxes ---
        preview_y = color_y + slider_gap * 3.2
        preview_size = WIDTH * 0.12
        pygame.draw.rect(screen, X_COLOR, (col_x_left - preview_size / 2, preview_y, preview_size, 40))
        pygame.draw.rect(screen, O_COLOR, (col_x_right - preview_size / 2, preview_y, preview_size, 40))
        draw_text("X preview", font_small, (255, 255, 255), screen, col_x_left, preview_y + 50)
        draw_text("O preview", font_small, (255, 255, 255), screen, col_x_right, preview_y + 50)

        # --- Color Presets ---
        preset_y = preview_y + 90
        preset_rects = []
        x_offset = WIDTH // 2 - (len(color_presets) * 60) // 2
        for i, (name, col) in enumerate(color_presets.items()):
            rect = pygame.Rect(x_offset + i * 60, preset_y, 50, 25)
            pygame.draw.rect(screen, col, rect)
            pygame.draw.rect(screen, (255, 255, 255), rect, 1)
            draw_text(name[0], font_small, (0, 0, 0), screen, rect.centerx, rect.centery)
            preset_rects.append((rect, col))

        # --- Buttons ---
        save_rect = pygame.Rect(WIDTH // 2 - 150, HEIGHT - 100, 90, 40)
        reset_rect = pygame.Rect(WIDTH // 2 - 45, HEIGHT - 100, 90, 40)
        back_rect = pygame.Rect(WIDTH // 2 + 60, HEIGHT - 100, 90, 40)

        pygame.draw.rect(screen, (60, 180, 60), save_rect)
        pygame.draw.rect(screen, (80, 80, 200), reset_rect)
        pygame.draw.rect(screen, (180, 60, 60), back_rect)
        draw_text("Save", font_small, (255, 255, 255), screen, save_rect.centerx, save_rect.centery)
        draw_text("Reset", font_small, (255, 255, 255), screen, reset_rect.centerx, reset_rect.centery)
        draw_text("Back", font_small, (255, 255, 255), screen, back_rect.centerx, back_rect.centery)

        # --- Events ---
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                dragging = None
                selected_input = None
                input_text = ""

                for target in ["X", "O"]:
                    for i, rect in enumerate(slider_rects[target]):
                        if rect.collidepoint(mx, my):
                            dragging = (target, i)

                    for i, rect in enumerate(input_boxes[target]):
                        if rect.collidepoint(mx, my):
                            selected_input = (target, i)
                            input_text = ""
                            play_sound("menu")

                for rect, col in preset_rects:
                    if rect.collidepoint(mx, my):
                        if active_color == "O":
                            O_COLOR = col
                        else:
                            X_COLOR = col
                        play_sound("menu")

                if save_rect.collidepoint(mx, my):
                    save_settings()
                    play_sound("menu")
                elif reset_rect.collidepoint(mx, my):
                    X_COLOR = DEFAULT_X_COLOR
                    O_COLOR = DEFAULT_O_COLOR
                    play_sound("menu")
                elif back_rect.collidepoint(mx, my):
                    play_sound("menu")
                    running = False

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = None

            elif event.type == pygame.MOUSEMOTION and dragging:
                target, i = dragging
                base_x = col_x_left - 150 if target == "X" else col_x_right - 150
                if target == "X":
                    X_COLOR = update_color("X", i, event.pos[0], base_x)
                else:
                    O_COLOR = update_color("O", i, event.pos[0], base_x)

            elif event.type == pygame.KEYDOWN and selected_input:
                if event.key == pygame.K_RETURN:
                    target, idx = selected_input
                    apply_input(target, idx, input_text)
                    selected_input = None
                elif event.key == pygame.K_BACKSPACE:
                    input_text = input_text[:-1]
                elif event.unicode.isdigit() and len(input_text) < 3:
                    input_text += event.unicode

        pygame.display.flip()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                # Volume clicks: simple region clicks to adjust
                if eff_rect.collidepoint(event.pos):
                    EFFECT_VOLUME = clamp01((event.pos[0]-eff_rect.x)/eff_rect.w)
                    _volume_changed_time = pygame.time.get_ticks()
                    try:
                        for k in SOUNDS:
                            if SOUNDS[k]:
                                SOUNDS[k].set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                    save_settings()
                elif mus_rect.collidepoint(event.pos):
                    MUSIC_VOLUME = clamp01((event.pos[0]-mus_rect.x)/mus_rect.w)
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    _volume_changed_time = pygame.time.get_ticks()
                    save_settings()

                # Start dragging slider for X
                for i, rect in enumerate(x_slider_rects):
                    if rect.collidepoint(event.pos):
                        dragging = ('x', i)
                        # update immediately
                        x_rel[i] = clamp01((event.pos[0] - rect.x) / rect.w)
                        X_COLOR = rel_to_rgb(x_rel)
                        save_settings()
                # Start dragging slider for O
                for i, rect in enumerate(o_slider_rects):
                    if rect.collidepoint(event.pos):
                        dragging = ('o', i)
                        o_rel[i] = clamp01((event.pos[0] - rect.x) / rect.w)
                        O_COLOR = rel_to_rgb(o_rel)
                        save_settings()

                # Click numeric input boxes: set active_input for typing
                for i, rct in enumerate(x_input_rects):
                    if rct.collidepoint(event.pos):
                        active_input = ('x', i)
                        input_buffers['x'][i] = ''
                for i, rct in enumerate(o_input_rects):
                    if rct.collidepoint(event.pos):
                        active_input = ('o', i)
                        input_buffers['o'][i] = ''

                # Reset/back
                if reset_rect.collidepoint(event.pos):
                    X_COLOR = DEFAULT_X_COLOR
                    O_COLOR = DEFAULT_O_COLOR
                    x_rel = rgb_to_rel(X_COLOR)
                    o_rel = rgb_to_rel(O_COLOR)
                    EFFECT_VOLUME = DEFAULT_EFFECT_VOLUME
                    MUSIC_VOLUME = DEFAULT_MUSIC_VOLUME
                    try:
                        for k in SOUNDS:
                            if SOUNDS[k]:
                                SOUNDS[k].set_volume(EFFECT_VOLUME)
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    save_settings()
                    play_sound('menu')
                if back_rect.collidepoint(event.pos):
                    play_sound('menu')
                    save_settings()
                    running = False

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = None

            elif event.type == pygame.MOUSEMOTION and dragging:
                who, idx = dragging
                if who == 'x':
                    rect = x_slider_rects[idx]
                    x_rel[idx] = clamp01((event.pos[0] - rect.x) / rect.w)
                    X_COLOR = rel_to_rgb(x_rel)
                    save_settings()
                else:
                    rect = o_slider_rects[idx]
                    o_rel[idx] = clamp01((event.pos[0] - rect.x) / rect.w)
                    O_COLOR = rel_to_rgb(o_rel)
                    save_settings()

            elif event.type == pygame.KEYDOWN:
                # If we're typing into numeric box
                if active_input:
                    who, idx = active_input
                    if event.key == pygame.K_BACKSPACE:
                        buf = input_buffers[who][idx]
                        input_buffers[who][idx] = buf[:-1]
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        # commit typed value
                        buf = input_buffers[who][idx]
                        try:
                            v = int(buf)
                            v = max(0, min(255, v))
                        except Exception:
                            v = int( (x_rel[idx] if who=='x' else o_rel[idx]) * 255 )
                        if who == 'x':
                            x_vals = [int(x_rel[i]*255) for i in range(3)]
                            x_vals[idx] = v
                            x_rel = [vv/255.0 for vv in x_vals]
                            X_COLOR = rel_to_rgb(x_rel)
                        else:
                            o_vals = [int(o_rel[i]*255) for i in range(3)]
                            o_vals[idx] = v
                            o_rel = [vv/255.0 for vv in o_vals]
                            O_COLOR = rel_to_rgb(o_rel)
                        input_buffers[who][idx] = ''
                        active_input = None
                        save_settings()
                    else:
                        # accept digits only
                        char = event.unicode
                        if char.isdigit() and len(input_buffers[active_input[0]][active_input[1]]) < 3:
                            input_buffers[active_input[0]][active_input[1]] += char
                else:
                    # keys when not typing: ESC to go back
                    if event.key == pygame.K_ESCAPE:
                        save_settings()
                        running = False

        clock.tick(60)

# -------------------------
# Play loop
# -------------------------
def play_one_game():
    reset_board()
    global player, _volume_changed_time
    while running:
        start_bgm()
        draw_lines(); draw_figures(); display_scoreboard()
        display_volume_hud_if_needed()
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX = event.pos[0] // SQUARE_SIZE
                mouseY = event.pos[1] // SQUARE_SIZE
                if game_mode == "PVP":
                    if available_square(mouseY, mouseX):
                        mark_square(mouseY, mouseX, player)
                        play_sound('move')
                        if check_win(player):
                            win_cells = get_winning_line(player)
                            draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                            handle_win(player)
                            draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop(f"Player {player} Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop("It's a Draw!")
                        else:
                            player = "O" if player == "X" else "X"
                elif game_mode in ("AI_EASY", "AI_HARD"):
                    if available_square(mouseY, mouseX):
                        mark_square(mouseY, mouseX, player)
                        play_sound('move')
                        if check_win("X"):
                            win_cells = get_winning_line("X")
                            draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                            handle_win("X")
                            draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop("Player X Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop("It's a Draw!")
                        # AI turn
                        if game_mode == "AI_EASY":
                            ai_move_easy()
                        else:
                            ai_move_hard()
                        if check_win("O"):
                            win_cells = get_winning_line("O")
                            draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                            handle_win("O")
                            draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop("Player O Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            save_settings(); return end_screen_loop("It's a Draw!")
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
        pygame.time.delay(8)
    return False

# -------------------------
# End screen
# -------------------------
def display_end_options(message):
    screen.fill(END_BG)
    result = FONT_LARGE.render(message, True, END_TEXT)
    screen.blit(result, (WIDTH//2 - result.get_width()//2, HEIGHT//2 - 100))
    restart = FONT.render("Press R to Restart", True, END_TEXT)
    menu_txt = FONT.render("Press M for Menu", True, END_TEXT)
    screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2))
    screen.blit(menu_txt, (WIDTH//2 - menu_txt.get_width()//2, HEIGHT//2 + 60))
    pygame.display.update()

def end_screen_loop(message):
    global game_mode
    display_end_options(message)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:
                    reset_board(); return True
                elif event.key == pygame.K_m:
                    game_mode = None; return False
                elif event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)

# -------------------------
# Entry point
# -------------------------
def main():
    load_settings()
    init_sounds()
    # apply volumes to already loaded sound objects
    try:
        for s in SOUNDS.values():
            if s: s.set_volume(EFFECT_VOLUME)
    except Exception:
        pass
    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass

    global game_mode, running
    while True:
        if game_mode is None:
            menu_loop()
        restart_same = play_one_game()
        if restart_same:
            continue
        else:
            continue

if __name__ == "__main__":
    main()

