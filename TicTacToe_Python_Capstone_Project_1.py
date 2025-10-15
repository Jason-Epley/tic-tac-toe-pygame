# tic_tac_toe.py
# Single-file Tic Tac Toe with robust settings screen and features requested by the user.
# Requirements: Python 3.8+, pygame installed.
# Place in project folder. Sound files optional (assets/sounds). settings.json will be created.

import os
import sys
import json
import random
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

# Defaults requested: volumes 100% by default per requirements
DEFAULT_EFFECT_VOLUME = 1.0
DEFAULT_MUSIC_VOLUME = 1.0
DEFAULT_X_COLOR = (0, 255, 120)
DEFAULT_O_COLOR = (0, 200, 230)
DEFAULT_BG_COLOR = (30, 30, 30)
DEFAULT_TEXT_COLOR = (255, 255, 255)

# Runtime globals (will be loaded/saved)
EFFECT_VOLUME = DEFAULT_EFFECT_VOLUME
MUSIC_VOLUME = DEFAULT_MUSIC_VOLUME
X_COLOR = DEFAULT_X_COLOR
O_COLOR = DEFAULT_O_COLOR
BG_COLOR = DEFAULT_BG_COLOR
TEXT_COLOR = DEFAULT_TEXT_COLOR

# Stats
x_wins = 0
o_wins = 0
draws = 0

# Window size (widened)
WIDTH, HEIGHT = 1100, 720

# Board layout margins (these control the visible board size)
BOARD_MARGIN_TOP = 110  # space above board (room for scoreboard)
BOARD_SIDE_MARGIN = 120
BOARD_BOTTOM_MARGIN = 140

# Colors & appearance
LINE_COLOR = (150, 150, 150)
END_BG = (10, 10, 10)
END_TEXT = (255, 255, 255)

# Visual constants
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
FONT_LARGE = pygame.font.SysFont(None, 56)

# Pygame display
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic Tac Toe")

# Game grid params computed so board fits
BOARD_ROWS = 3
BOARD_COLS = 3

def compute_board_layout():
    max_board_w = WIDTH - 2 * BOARD_SIDE_MARGIN
    max_board_h = HEIGHT - BOARD_MARGIN_TOP - BOARD_BOTTOM_MARGIN
    board_size = min(max_board_w, max_board_h)
    square = max(60, board_size // 3)  # ensure readable
    board_pix_w = square * 3
    board_left = (WIDTH - board_pix_w) // 2
    board_top = BOARD_MARGIN_TOP
    circle_radius = max(16, square // 3)
    # O stroke halved relative to previous wide value -> choose moderate
    circle_width = max(4, circle_radius // 4)  # half as thick (reduced)
    cross_width = max(8, square // 12)
    return {
        'SQUARE_SIZE': square,
        'BOARD_LEFT': board_left,
        'BOARD_TOP': board_top,
        'BOARD_PIX_W': board_pix_w,
        'CIRCLE_RADIUS': circle_radius,
        'CIRCLE_WIDTH': circle_width,
        'CROSS_WIDTH': cross_width
    }

# Display helpers: allow resize and fullscreen toggling
fullscreen = False
screen = None

def set_display_mode(w: int, h: int, full: bool = False):
    """Set the global display mode and recompute layout-related globals."""
    global screen, WIDTH, HEIGHT, SQUARE_SIZE, BOARD_LEFT, BOARD_TOP, CIRCLE_RADIUS, CIRCLE_WIDTH, CROSS_WIDTH, SPACE
    WIDTH = int(w); HEIGHT = int(h)
    flags = pygame.FULLSCREEN if full else pygame.RESIZABLE
    screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption("Tic Tac Toe")
    layout = compute_board_layout()
    SQUARE_SIZE = layout['SQUARE_SIZE']
    BOARD_LEFT = layout['BOARD_LEFT']
    BOARD_TOP = layout['BOARD_TOP']
    CIRCLE_RADIUS = layout['CIRCLE_RADIUS']
    CIRCLE_WIDTH = layout['CIRCLE_WIDTH']
    CROSS_WIDTH = layout['CROSS_WIDTH']
    SPACE = max(8, SQUARE_SIZE // 10)

def toggle_fullscreen():
    global fullscreen
    fullscreen = not fullscreen
    set_display_mode(WIDTH, HEIGHT, full=fullscreen)

# initialize screen and layout
set_display_mode(WIDTH, HEIGHT, full=fullscreen)

# Game state
board: list[list[Optional[str]]] = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
game_mode = None  # "PVP", "AI_EASY", "AI_HARD"
player = "X"
running = False

# Volume HUD helper
_volume_changed_time = 0
_VOLUME_HUD_DURATION_MS = 1500

# -------------------------
# Sound loading helpers
# -------------------------
SOUNDS: Dict[str, Optional[pygame.mixer.Sound]] = {}

def candidates_for(name: str):
    base = os.path.join(SOUND_DIR, name)
    exts = ['', '.wav', '.ogg', '.mp3']
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
        ok = any(os.path.exists(cand) for cand in candidates_for(filename))
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

    # Initial effect volumes
    for k, s in SOUNDS.items():
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
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR, BG_COLOR, TEXT_COLOR, x_wins, o_wins, draws
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            EFFECT_VOLUME = float(data.get("effect_volume", DEFAULT_EFFECT_VOLUME))
            MUSIC_VOLUME = float(data.get("music_volume", DEFAULT_MUSIC_VOLUME))
            X_COLOR = tuple(data.get("x_color", DEFAULT_X_COLOR))
            O_COLOR = tuple(data.get("o_color", DEFAULT_O_COLOR))
            BG_COLOR = tuple(data.get("bg_color", DEFAULT_BG_COLOR))
            TEXT_COLOR = tuple(data.get("text_color", DEFAULT_TEXT_COLOR))
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
                "bg_color": BG_COLOR,
                "text_color": TEXT_COLOR,
                "x_wins": x_wins,
                "o_wins": o_wins,
                "draws": draws
            }, f, indent=2)
    except Exception as e:
        print("Warning: couldn't save settings:", e)

# -------------------------
# Helpers (drawing/logic)
# -------------------------
def draw_text_center(text, font, color, surface, x, y):
    surf_text = font.render(text, True, color)
    rect = surf_text.get_rect(center=(x, y))
    surface.blit(surf_text, rect)

def reset_board():
    global board, player, running
    board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
    player = "X"
    running = True
    screen.fill(BG_COLOR)
    draw_lines()
    display_scoreboard()

def draw_lines():
    # fill bg, draw grid lines in center area
    screen.fill(BG_COLOR)
    # horizontal lines
    for r in range(1, 3):
        y = BOARD_TOP + r * SQUARE_SIZE
        pygame.draw.line(screen, LINE_COLOR, (BOARD_LEFT, y), (BOARD_LEFT + 3 * SQUARE_SIZE, y), max(6, SQUARE_SIZE//14))
    # vertical
    for c in range(1, 3):
        x = BOARD_LEFT + c * SQUARE_SIZE
        pygame.draw.line(screen, LINE_COLOR, (x, BOARD_TOP), (x, BOARD_TOP + 3 * SQUARE_SIZE), max(6, SQUARE_SIZE//14))

def draw_figures():
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            x_center = BOARD_LEFT + c * SQUARE_SIZE + SQUARE_SIZE // 2
            y_center = BOARD_TOP + r * SQUARE_SIZE + SQUARE_SIZE // 2
            if board[r][c] == "O":
                pygame.draw.circle(screen, O_COLOR, (x_center, y_center), CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif board[r][c] == "X":
                pad = max(12, SQUARE_SIZE // 8)
                pygame.draw.line(screen, X_COLOR,
                                 (x_center - SQUARE_SIZE//2 + pad, y_center - SQUARE_SIZE//2 + pad),
                                 (x_center + SQUARE_SIZE//2 - pad, y_center + SQUARE_SIZE//2 - pad),
                                 CROSS_WIDTH)
                pygame.draw.line(screen, X_COLOR,
                                 (x_center - SQUARE_SIZE//2 + pad, y_center + SQUARE_SIZE//2 - pad),
                                 (x_center + SQUARE_SIZE//2 - pad, y_center - SQUARE_SIZE//2 + pad),
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
    return (BOARD_LEFT + c * SQUARE_SIZE + SQUARE_SIZE // 2, BOARD_TOP + r * SQUARE_SIZE + SQUARE_SIZE // 2)

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
    ms_per_half = max(8, total_ms // 2)
    ms_per_step = max(8, ms_per_half // max(1, steps - 1))
    for _ in range(pulses):
        for s in range(steps):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines(); draw_figures(); display_scoreboard()
            for c in centers:
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update(); pygame.time.delay(ms_per_step)
        for s in reversed(range(steps)):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines(); draw_figures(); display_scoreboard()
            for c in centers:
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update(); pygame.time.delay(ms_per_step)

def check_win(player_mark):
    return get_winning_line(player_mark) is not None

def display_scoreboard():
    # Centered top scoreboard as requested
    txt = f"X Wins: {x_wins}    O Wins: {o_wins}    Draws: {draws}"
    draw_text_center(txt, FONT_MED, TEXT_COLOR, screen, WIDTH // 2, 36)

def display_volume_hud_if_needed():
    global _volume_changed_time
    if _volume_changed_time == 0:
        return
    elapsed = pygame.time.get_ticks() - _volume_changed_time
    if elapsed > _VOLUME_HUD_DURATION_MS:
        return
    hud_w, hud_h = 240, 56
    hud_surf = pygame.Surface((hud_w, hud_h), pygame.SRCALPHA)
    hud_surf.fill((0, 0, 0, 180))
    screen.blit(hud_surf, (WIDTH - hud_w - 10, 12))
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
        if SOUNDS.get('lose'):
            play_sound('lose')
        else:
            play_sound('win')

def handle_draw():
    global draws
    draws += 1
    play_sound('draw')

# -------------------------
# AI (unchanged)
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
    screen.fill(BG_COLOR)
    draw_text_center("Tic Tac Toe", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, 60)
    options = [
        "Player vs Player",
        "Player vs AI (Easy)",
        "Player vs AI (Hard)",
        "Settings",
        "Quit"
    ]
    y = 160
    option_rects = []
    for o in options:
        txt_surf = FONT.render(o, True, TEXT_COLOR)
        rect = txt_surf.get_rect(center=(WIDTH//2, y))
        screen.blit(txt_surf, rect)
        option_rects.append(rect)
        y += 52
    pygame.display.update()
    return option_rects

def menu_loop():
    global game_mode
    while True:
        option_rects = draw_menu()
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                set_display_mode(event.w, event.h, full=fullscreen)
                option_rects = draw_menu()
                continue
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    option_rects = draw_menu()
                    break
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
                    play_sound('menu'); settings_screen()
                elif event.key == pygame.K_5:
                    play_sound('menu'); save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                for i, rect in enumerate(option_rects):
                    if rect.collidepoint(mx, my):
                        play_sound('menu')
                        if i == 0:
                            game_mode = "PVP"
                            return
                        elif i == 1:
                            game_mode = "AI_EASY"
                            return
                        elif i == 2:
                            game_mode = "AI_HARD"
                            return
                        elif i == 3:
                            settings_screen()
                            break
                        elif i == 4:
                            save_settings()
                            pygame.quit()
                            sys.exit()

# -------------------------
# Simple utilities for settings UI
# -------------------------
def clamp01(x): return max(0.0, min(1.0, x))
def rels_to_rgb(rels): return (int(rels[0]*255), int(rels[1]*255), int(rels[2]*255))
def rgb_to_rels(rgb): return [rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0]
def clamp_byte(v): return max(0, min(255, int(v)))

# Shared flag to play click only once while dragging volumes
_last_volume_click_time = 0
_VOLUME_CLICK_THROTTLE_MS = 140

def change_volume(delta: float):
    global EFFECT_VOLUME, MUSIC_VOLUME, _volume_changed_time, _last_volume_click_time
    EFFECT_VOLUME = clamp01(EFFECT_VOLUME + delta)
    MUSIC_VOLUME = clamp01(MUSIC_VOLUME + delta)
    try:
        for k, s in SOUNDS.items():
            if s: s.set_volume(EFFECT_VOLUME)
    except Exception:
        pass
    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass
    _volume_changed_time = pygame.time.get_ticks()
    # play single click sound once now
    now = pygame.time.get_ticks()
    if now - _last_volume_click_time > _VOLUME_CLICK_THROTTLE_MS:
        _last_volume_click_time = now
        play_sound('menu_select')

# -------------------------
# Settings screen (as requested)
# -------------------------
def settings_screen():
    """
    Settings screen features:
      - Effects & Music sliders (click/drag). Plays one click sound while dragging adjustments.
      - X, O, Background RGB sliders (compressed spacing).
      - Text Color presets (White text / Gray text / Black text) with black button backgrounds.
      - Preset buttons for X/O/BG colors (background preset texts white).
      - Save / Reset / Reset Scores / Back buttons centered.
      - Toggle Music On checkbox.
      - Clicking previews selects which color presets apply to.
    """
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR, BG_COLOR, TEXT_COLOR, x_wins, o_wins, draws, _last_volume_click_time

    clock = pygame.time.Clock()
    running = True
    dragging = None  # "eff"|"mus" or ("X", idx)|("O", idx)|("BG", idx)
    selected_input = None
    input_text = ""
    active_color = None  # which target receives presets: "X","O","BG" or None -> apply to all
    music_on = True if pygame.mixer.music.get_busy() else False

    # Layout tuned for larger width and compressed spacing
    margin_top = 46
    col_left = WIDTH * 0.26
    col_right = WIDTH * 0.74
    slider_w = int(WIDTH * 0.24)
    slider_h = 14

    # (Layout is computed dynamically each frame below.)

    # Color presets with single-letter labels for top row and named background presets
    color_presets = [
        ("R", (255, 0, 0)),
        ("G", (0, 255, 0)),
        ("B", (0, 100, 255)),
        ("Y", (255, 255, 0)),
        ("P", (255, 105, 180)),
        ("W", (255, 255, 255))
    ]
    bg_presets = [
        ("Dark", (20, 20, 20)),
        ("Gray", (80, 80, 80)),
        ("Tan", (120, 100, 86)),
        ("Blue", (16,32,64))
    ]
    text_presets = [
        ("White text", (255,255,255)),
        ("Gray text", (200,200,200)),
        ("Black text", (0,0,0))
    ]

    # current slider rels
    x_rels = rgb_to_rels(X_COLOR)
    o_rels = rgb_to_rels(O_COLOR)
    bg_rels = rgb_to_rels(BG_COLOR)

    def update_color_from_mouse(target, idx, mx):
        if target == "X":
            base = x_base_x
            rel = clamp01((mx - base) / slider_w)
            x_rels[idx] = rel
            return rels_to_rgb(x_rels)
        elif target == "O":
            base = o_base_x
            rel = clamp01((mx - base) / slider_w)
            o_rels[idx] = rel
            return rels_to_rgb(o_rels)
        else:
            base = bg_base_x
            rel = clamp01((mx - base) / slider_w)
            bg_rels[idx] = rel
            return rels_to_rgb(bg_rels)

    def set_color(target, rgb):
        nonlocal x_rels, o_rels, bg_rels
        global X_COLOR, O_COLOR, BG_COLOR
        if target == "X":
            X_COLOR = tuple(rgb); x_rels = rgb_to_rels(X_COLOR)
        elif target == "O":
            O_COLOR = tuple(rgb); o_rels = rgb_to_rels(O_COLOR)
        else:
            BG_COLOR = tuple(rgb); bg_rels = rgb_to_rels(BG_COLOR)

    def commit_numeric_input(target, idx, txt):
        if not txt: return
        try:
            v = int(txt)
        except Exception:
            return
        v = clamp_byte(v)
        if target == "X":
            c = list(X_COLOR); c[idx] = v; set_color("X", tuple(c))
        elif target == "O":
            c = list(O_COLOR); c[idx] = v; set_color("O", tuple(c))
        else:
            c = list(BG_COLOR); c[idx] = v; set_color("BG", tuple(c))

    # button rects are computed per-frame below

    # bounding rect placeholders for inputs/previews
    x_input_boxes = [pygame.Rect(0,0,0,0) for _ in range(3)]
    o_input_boxes = [pygame.Rect(0,0,0,0) for _ in range(3)]
    bg_input_boxes = [pygame.Rect(0,0,0,0) for _ in range(3)]
    preview_rect_x = preview_rect_o = preview_rect_bg = None

    # main loop
    while running:
        # recompute layout each frame to avoid overlap on resize
        margin_top = max(36, int(HEIGHT * 0.06))
        col_left = int(WIDTH * 0.22)
        col_right = int(WIDTH * 0.78)
        slider_w = max(180, int(WIDTH * 0.22))
        slider_h = max(16, int(HEIGHT * 0.02))
        # vertical spacing tuned to window height
        slider_v_space = max(64, int(HEIGHT * 0.085))

        # recompute rects
        eff_rect = pygame.Rect(int(col_left - slider_w//2), int(margin_top + 56), slider_w, slider_h)
        mus_rect = pygame.Rect(int(col_right - slider_w//2), int(margin_top + 56), slider_w, slider_h)

        color_y = int(margin_top + 130)
        x_base_x = int(col_left - slider_w//2)
        o_base_x = int(col_right - slider_w//2)
        bg_base_x = int((WIDTH // 2) - slider_w//2)

        x_slider_rects = [pygame.Rect(x_base_x, color_y + i*slider_v_space, slider_w, slider_h) for i in range(3)]
        o_slider_rects = [pygame.Rect(o_base_x, color_y + i*slider_v_space, slider_w, slider_h) for i in range(3)]
        bg_slider_rects = [pygame.Rect(bg_base_x, color_y + i*slider_v_space, slider_w, slider_h) for i in range(3)]

        preview_w = min(320, int(WIDTH * 0.18))
        preview_h = min(120, int(HEIGHT * 0.12))

        # place buttons near bottom with margin - evenly spaced
        buttons_y = HEIGHT - max(92, int(HEIGHT * 0.12))
        btn_w = min(220, max(140, int(WIDTH * 0.16)))
        btn_h = max(48, int(HEIGHT * 0.07))
        gap = max(20, int(WIDTH * 0.03))
        total_w = btn_w * 4 + gap * 3
        start_x = WIDTH//2 - total_w//2
        save_rect = pygame.Rect(start_x, buttons_y, btn_w, btn_h)
        reset_rect = pygame.Rect(start_x + (btn_w + gap) * 1, buttons_y, btn_w, btn_h)
        reset_scores_rect = pygame.Rect(start_x + (btn_w + gap) * 2, buttons_y, btn_w, btn_h)
        back_rect = pygame.Rect(start_x + (btn_w + gap) * 3, buttons_y, btn_w, btn_h)

        # draw background area
        screen.fill(BG_COLOR)
        draw_text_center("Settings", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, margin_top)

        # Effects & Music labels and sliders
        vol_y = margin_top + 56
        draw_text_center(f"Effects: {int(EFFECT_VOLUME*100)}%", FONT_MED, TEXT_COLOR, screen, col_left, vol_y - 10)
        draw_text_center(f"Music:   {int(MUSIC_VOLUME*100)}%", FONT_MED, TEXT_COLOR, screen, col_right, vol_y - 10)

        # draw effect slider track + fill with rounded corners and subtle inner shadow
        br = max(4, slider_h // 3)
        pygame.draw.rect(screen, (70,70,70), eff_rect, border_radius=br)
        fill_rect = pygame.Rect(eff_rect.x, eff_rect.y, int(eff_rect.w * EFFECT_VOLUME), eff_rect.h)
        pygame.draw.rect(screen, (120,180,120), fill_rect, border_radius=br)
        # subtle inner shadow: thin dark line at top inside track
        shadow_surf = pygame.Surface((eff_rect.w - 4, 2), pygame.SRCALPHA)
        shadow_surf.fill((0,0,0,48))
        screen.blit(shadow_surf, (eff_rect.x + 2, eff_rect.y + 2))

        # draw effect slider handle + glow when active
        eff_handle_pos = (eff_rect.x + int(eff_rect.w * EFFECT_VOLUME), eff_rect.y + eff_rect.h//2)
        eff_handle_radius = max(10, slider_h)
        eff_handle_color = (255,255,255)
        if dragging == "eff":
            eff_handle_color = (255,220,40)
            eff_handle_radius = eff_handle_radius + 4
            glow_s_eff = pygame.Surface((eff_handle_radius*6, eff_handle_radius*6), pygame.SRCALPHA)
            glow_rect_eff = glow_s_eff.get_rect(center=eff_handle_pos)
            for g in range(eff_handle_radius*3, 0, -2):
                alpha = max(6, int(80 * (g / (eff_handle_radius*3))))
                pygame.draw.circle(glow_s_eff, (255,220,40,alpha), (glow_s_eff.get_width()//2, glow_s_eff.get_height()//2), g)
            screen.blit(glow_s_eff, glow_rect_eff.topleft)
        pygame.draw.circle(screen, eff_handle_color, eff_handle_pos, eff_handle_radius)

        pygame.draw.rect(screen, (70,70,70), mus_rect, border_radius=br)
        fill_m = pygame.Rect(mus_rect.x, mus_rect.y, int(mus_rect.w * MUSIC_VOLUME), mus_rect.h)
        pygame.draw.rect(screen, (120,180,120), fill_m, border_radius=br)
        shadow_surf2 = pygame.Surface((mus_rect.w - 4, 2), pygame.SRCALPHA)
        shadow_surf2.fill((0,0,0,48))
        screen.blit(shadow_surf2, (mus_rect.x + 2, mus_rect.y + 2))

        # draw music slider handle + glow when active
        mus_handle_pos = (mus_rect.x + int(mus_rect.w * MUSIC_VOLUME), mus_rect.y + mus_rect.h//2)
        mus_handle_radius = max(10, slider_h)
        mus_handle_color = (255,255,255)
        if dragging == "mus":
            mus_handle_color = (255,220,40)
            mus_handle_radius = mus_handle_radius + 4
            glow_s_mus = pygame.Surface((mus_handle_radius*6, mus_handle_radius*6), pygame.SRCALPHA)
            glow_rect_mus = glow_s_mus.get_rect(center=mus_handle_pos)
            for g in range(mus_handle_radius*3, 0, -2):
                alpha = max(6, int(80 * (g / (mus_handle_radius*3))))
                pygame.draw.circle(glow_s_mus, (255,220,40,alpha), (glow_s_mus.get_width()//2, glow_s_mus.get_height()//2), g)
            screen.blit(glow_s_mus, glow_rect_mus.topleft)
        pygame.draw.circle(screen, mus_handle_color, mus_handle_pos, mus_handle_radius)

        # Music toggle checkbox and label under music slider
        music_toggle_rect = pygame.Rect(mus_rect.x, mus_rect.y + 28, 20, 20)
        pygame.draw.rect(screen, (0,0,0), music_toggle_rect)
        pygame.draw.rect(screen, (255,255,255), music_toggle_rect, 2)
        if music_on:
            pygame.draw.rect(screen, (50,200,80), (music_toggle_rect.x+4, music_toggle_rect.y+4, 12, 12))
        draw_text_center("Music On", FONT_SMALL, TEXT_COLOR, screen, music_toggle_rect.x + 70, music_toggle_rect.centery)

        # Titles for color sections
        draw_text_center("X Color", FONT_MED, X_COLOR, screen, col_left, color_y - 30)
        draw_text_center("Background", FONT_MED, BG_COLOR, screen, WIDTH//2, color_y - 30)  # rename BG->Background
        draw_text_center("O Color", FONT_MED, O_COLOR, screen, col_right, color_y - 30)

        # Draw RGB sliders and numeric boxes for X, BG, O (compressed spacing)
        slider_rects = {"X": [], "BG": [], "O": []}
        input_boxes = {"X": [], "BG": [], "O": []}

        for i, lbl in enumerate(["R","G","B"]):
            y_pos = color_y + i*slider_v_space

            # X side
            r = x_slider_rects[i]
            pygame.draw.rect(screen, (100,100,100), r, border_radius=6)
            # thin white outline for slider track
            pygame.draw.rect(screen, (255,255,255), r, 1, border_radius=6)
            fill = int(r.w * x_rels[i])
            pygame.draw.rect(screen, X_COLOR, (r.x, r.y, fill, r.h))
            # slider handle - larger and changes color when active
            handle_pos = (r.x + fill, r.y + r.h//2)
            handle_radius = 12
            handle_color = (255, 255, 255)
            active = isinstance(dragging, tuple) and dragging[0] == "X" and dragging[1] == i
            if active:
                handle_color = (255, 220, 40)  # bright accent when dragging
                handle_radius = 14
                # draw soft glow behind active handle
                glow_s = pygame.Surface((handle_radius*6, handle_radius*6), pygame.SRCALPHA)
                glow_rect = glow_s.get_rect(center=handle_pos)
                for g in range(handle_radius*3, 0, -2):
                    alpha = max(6, int(80 * (g / (handle_radius*3))))
                    pygame.draw.circle(glow_s, (255, 220, 40, alpha), (glow_s.get_width()//2, glow_s.get_height()//2), g)
                screen.blit(glow_s, glow_rect.topleft)
            pygame.draw.circle(screen, handle_color, handle_pos, handle_radius)
            draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, r.x - 22, r.y + r.h//2)

            # numeric box for X (left column)
            vx = int(col_left + slider_w/2 + 28)
            val_rect_x = pygame.Rect(vx, r.y - 6, 64, 30)
            pygame.draw.rect(screen, (40,40,40), val_rect_x)
            pygame.draw.rect(screen, (200,200,200), val_rect_x, 1)
            draw_text_center(str(int(X_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_rect_x.centerx, val_rect_x.centery)

            slider_rects["X"].append(r.copy())
            input_boxes["X"].append(val_rect_x)
            x_input_boxes[i] = val_rect_x

            # BG middle
            rb = bg_slider_rects[i]
            pygame.draw.rect(screen, (100,100,100), rb, border_radius=6)
            # thin white outline for slider track
            pygame.draw.rect(screen, (255,255,255), rb, 1, border_radius=6)
            fillb = int(rb.w * bg_rels[i])
            pygame.draw.rect(screen, BG_COLOR, (rb.x, rb.y, fillb, rb.h))
            handle_pos_b = (rb.x + fillb, rb.y + rb.h//2)
            handle_radius_b = 12
            handle_color_b = (255, 255, 255)
            active_b = isinstance(dragging, tuple) and dragging[0] == "BG" and dragging[1] == i
            if active_b:
                handle_color_b = (255, 220, 40)
                handle_radius_b = 14
                glow_s_b = pygame.Surface((handle_radius_b*6, handle_radius_b*6), pygame.SRCALPHA)
                glow_rect_b = glow_s_b.get_rect(center=handle_pos_b)
                for g in range(handle_radius_b*3, 0, -2):
                    alpha = max(6, int(80 * (g / (handle_radius_b*3))))
                    pygame.draw.circle(glow_s_b, (255, 220, 40, alpha), (glow_s_b.get_width()//2, glow_s_b.get_height()//2), g)
                screen.blit(glow_s_b, glow_rect_b.topleft)
            pygame.draw.circle(screen, handle_color_b, handle_pos_b, handle_radius_b)
            draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, rb.x - 22, rb.y + rb.h//2)

            vb = int(WIDTH//2 + slider_w/2 + 28)
            val_rect_b = pygame.Rect(vb, rb.y - 6, 64, 30)
            pygame.draw.rect(screen, (40,40,40), val_rect_b)
            pygame.draw.rect(screen, (200,200,200), val_rect_b, 1)
            draw_text_center(str(int(BG_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_rect_b.centerx, val_rect_b.centery)

            slider_rects["BG"].append(rb.copy())
            input_boxes["BG"].append(val_rect_b)
            bg_input_boxes[i] = val_rect_b

            # O side
            r2 = o_slider_rects[i]
            pygame.draw.rect(screen, (100,100,100), r2, border_radius=6)
            # thin white outline for slider track
            pygame.draw.rect(screen, (255,255,255), r2, 1, border_radius=6)
            fill2 = int(r2.w * o_rels[i])
            pygame.draw.rect(screen, O_COLOR, (r2.x, r2.y, fill2, r2.h))
            handle_pos_o = (r2.x + fill2, r2.y + r2.h//2)
            handle_radius_o = 12
            handle_color_o = (255, 255, 255)
            active_o = isinstance(dragging, tuple) and dragging[0] == "O" and dragging[1] == i
            if active_o:
                handle_color_o = (255, 220, 40)
                handle_radius_o = 14
                glow_s_o = pygame.Surface((handle_radius_o*6, handle_radius_o*6), pygame.SRCALPHA)
                glow_rect_o = glow_s_o.get_rect(center=handle_pos_o)
                for g in range(handle_radius_o*3, 0, -2):
                    alpha = max(6, int(80 * (g / (handle_radius_o*3))))
                    pygame.draw.circle(glow_s_o, (255, 220, 40, alpha), (glow_s_o.get_width()//2, glow_s_o.get_height()//2), g)
                screen.blit(glow_s_o, glow_rect_o.topleft)
            pygame.draw.circle(screen, handle_color_o, handle_pos_o, handle_radius_o)
            draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, r2.x - 22, r2.y + r2.h//2)

            vo = int(col_right + slider_w/2 + 28)
            val_rect_o = pygame.Rect(vo, r2.y - 6, 64, 30)
            # make sure not off-screen
            if val_rect_o.right > WIDTH - 8:
                val_rect_o.right = WIDTH - 8
            pygame.draw.rect(screen, (40,40,40), val_rect_o)
            pygame.draw.rect(screen, (200,200,200), val_rect_o, 1)
            draw_text_center(str(int(O_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_rect_o.centerx, val_rect_o.centery)

            slider_rects["O"].append(r2.copy())
            input_boxes["O"].append(val_rect_o)
            o_input_boxes[i] = val_rect_o

        # (Previews removed) place presets below the color sliders area
        presets_y = color_y + slider_v_space * 3 + max(int(HEIGHT * 0.03), 36)
        preset_rects = []

        # Presets row 1 (top colored small buttons, apply to active color)
        preset_rects = []
        small_preset_w = max(56, int(WIDTH * 0.06))
        small_preset_h = max(32, int(HEIGHT * 0.05))
        preset_gap = max(12, int(WIDTH * 0.02))
        total_presets_w = len(color_presets) * small_preset_w + (len(color_presets)-1) * preset_gap
        x_start = (WIDTH - total_presets_w) // 2
        for idx, (k, col) in enumerate(color_presets):
            pr = pygame.Rect(x_start + idx*(small_preset_w + preset_gap), presets_y, small_preset_w, small_preset_h)
            pygame.draw.rect(screen, col, pr)
            pygame.draw.rect(screen, (255,255,255), pr, 2)
            draw_text_center(k, FONT_SMALL, (0,0,0), screen, pr.centerx, pr.centery)
            preset_rects.append((pr, col))

        # Background preset row (below color presets, centered)
        bgp_y = presets_y + 56
        bg_preset_rects = []
        x_start2 = (WIDTH - (len(bg_presets) * 140 - 20)) // 2
        for idx, (name, col) in enumerate(bg_presets):
            br = pygame.Rect(x_start2 + idx*140, bgp_y, 128, 48)
            pygame.draw.rect(screen, col, br)
            pygame.draw.rect(screen, (255,255,255), br, 2)
            draw_text_center(name, FONT_SMALL, (255,255,255), screen, br.centerx, br.centery)  # white text as requested
            bg_preset_rects.append((br, col))

        # Text color options: moved to bottom row near the white button as requested.
        # But user asked "Move the 'Text Color' text at the top of the settings page to the left of the 'White' button at the bottom"
        # We'll place label text left of the "White text" button at the bottom center area.
        text_pres_x = WIDTH//2 - 380
        text_pres_y = bgp_y + 80
        # draw text label (left of first button)
        draw_text_center("Text Color:", FONT_SMALL, TEXT_COLOR, screen, text_pres_x - 70, text_pres_y + 18)

        text_preset_rects = []
        # White, Gray, Black buttons: Black text button has white background per request.
        tp_x = text_pres_x
        for (label, col) in text_presets:
            tbr = pygame.Rect(tp_x, text_pres_y, 140, 44)
            if label == "Black text":
                bg_col = (255,255,255)
                txt_col = (0,0,0)
                outline_col = (0,0,0)
            elif label == "White text":
                bg_col = (0,0,0)
                txt_col = (255,255,255)
                outline_col = (255,255,255)
            else:
                bg_col = (0,0,0)
                txt_col = (200,200,200)
                outline_col = (255,255,255)
            pygame.draw.rect(screen, bg_col, tbr)
            draw_text_center(label, FONT_SMALL, txt_col, screen, tbr.centerx, tbr.centery)
            pygame.draw.rect(screen, outline_col, tbr, 2)
            text_preset_rects.append((tbr, col, label))
            tp_x += 160

        # Buttons at bottom: Save, Reset, Reset Scores, Back (evenly spaced)
        pygame.draw.rect(screen, (60,180,60), save_rect)
        pygame.draw.rect(screen, (80,80,200), reset_rect)
        pygame.draw.rect(screen, (120,20,120), reset_scores_rect)
        pygame.draw.rect(screen, (180,60,60), back_rect)
        draw_text_center("Save", FONT_MED, (255,255,255), screen, save_rect.centerx, save_rect.centery)
        draw_text_center("Reset", FONT_MED, (255,255,255), screen, reset_rect.centerx, reset_rect.centery)
        draw_text_center("Reset Scores", FONT_MED, (255,255,255), screen, reset_scores_rect.centerx, reset_scores_rect.centery)
        draw_text_center("Back", FONT_MED, (255,255,255), screen, back_rect.centerx, back_rect.centery)

        # Draw thin white outlines around each RGB slider group to separate them
        pad = max(8, int(slider_h * 0.8))
        for key in ("X", "BG", "O"):
            rects = slider_rects.get(key, [])
            if rects:
                left = rects[0].left - pad
                top = rects[0].top - pad
                width = rects[0].w + pad * 2
                height = (rects[-1].bottom - rects[0].top) + pad * 2
                pygame.draw.rect(screen, (255,255,255), (left, top, width, height), 1, border_radius=10)

        # show currently active_color (small hint)
        hint_x = WIDTH//2
        hint_y = save_rect.top - 28
        active_label = active_color if active_color else "All"
        draw_text_center(f"Preset target: {active_label}", FONT_SMALL, TEXT_COLOR, screen, hint_x, hint_y)

        pygame.display.flip()

        # Event handling for settings
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                set_display_mode(event.w, event.h, full=fullscreen)
                # redraw immediately
                break
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # Toggle music on checkbox
                if music_toggle_rect.collidepoint(mx, my):
                    music_on = not music_on
                    if music_on:
                        try:
                            start_bgm(loop=True)
                        except Exception:
                            pass
                    else:
                        try:
                            stop_bgm()
                        except Exception:
                            pass
                    play_sound('menu')
                    continue

                # effects / music slider click & drag
                if eff_rect.collidepoint(mx, my):
                    dragging = "eff"
                    EFFECT_VOLUME = clamp01((mx - eff_rect.x) / eff_rect.w)
                    # set volumes on sound objects
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                    _volume_changed_time = pygame.time.get_ticks()
                    # click sound once
                    now = pygame.time.get_ticks()
                    if now - _last_volume_click_time > _VOLUME_CLICK_THROTTLE_MS:
                        _last_volume_click_time = now
                        play_sound('menu_select')
                    continue
                if mus_rect.collidepoint(mx, my):
                    dragging = "mus"
                    MUSIC_VOLUME = clamp01((mx - mus_rect.x) / mus_rect.w)
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    _volume_changed_time = pygame.time.get_ticks()
                    now = pygame.time.get_ticks()
                    if now - _last_volume_click_time > _VOLUME_CLICK_THROTTLE_MS:
                        _last_volume_click_time = now
                        play_sound('menu_select')
                    continue

                # color sliders start drag & apply immediately
                hit = False
                for i, r in enumerate(slider_rects["X"]):
                    if r.collidepoint(mx, my):
                        dragging = ("X", i); active_color = "X"
                        X_COLOR = update_color_from_mouse("X", i, mx)
                        hit = True
                for i, r in enumerate(slider_rects["O"]):
                    if r.collidepoint(mx, my):
                        dragging = ("O", i); active_color = "O"
                        O_COLOR = update_color_from_mouse("O", i, mx)
                        hit = True
                for i, r in enumerate(slider_rects["BG"]):
                    if r.collidepoint(mx, my):
                        dragging = ("BG", i); active_color = "BG"
                        BG_COLOR = update_color_from_mouse("BG", i, mx)
                        hit = True
                if hit:
                    continue

                # numeric boxes clicked -> prepare editing
                for i, rect in enumerate(input_boxes["X"]):
                    if rect.collidepoint(mx, my):
                        selected_input = ("X", i); input_text = str(int(X_COLOR[i])); active_color = "X"
                for i, rect in enumerate(input_boxes["O"]):
                    if rect.collidepoint(mx, my):
                        selected_input = ("O", i); input_text = str(int(O_COLOR[i])); active_color = "O"
                for i, rect in enumerate(input_boxes["BG"]):
                    if rect.collidepoint(mx, my):
                        selected_input = ("BG", i); input_text = str(int(BG_COLOR[i])); active_color = "BG"

                # preview elements removed; selecting active target happens via presets or numeric boxes

                # color presets (top small)
                for rect, col in preset_rects:
                    if rect.collidepoint(mx, my):
                        if active_color == "X":
                            set_color("X", col)
                        elif active_color == "O":
                            set_color("O", col)
                        elif active_color == "BG":
                            set_color("BG", col)
                        else:
                            set_color("X", col); set_color("O", col); set_color("BG", col)
                        play_sound('menu')
                        break

                # background presets
                for rect, col in bg_preset_rects:
                    if rect.collidepoint(mx, my):
                        set_color("BG", col)
                        play_sound('menu')
                        break

                # text color presets (bottom)
                for rect, col, label in text_preset_rects:
                    if rect.collidepoint(mx, my):
                        TEXT_COLOR = col
                        play_sound('menu')
                        break

                # Buttons: Save, Reset, Reset Scores, Back
                if save_rect.collidepoint(mx, my):
                    save_settings(); play_sound('menu')
                elif reset_rect.collidepoint(mx, my):
                    # Reset colors and volumes to defaults (volumes -> 100% per requirement)
                    X_COLOR = DEFAULT_X_COLOR
                    O_COLOR = DEFAULT_O_COLOR
                    BG_COLOR = DEFAULT_BG_COLOR
                    TEXT_COLOR = DEFAULT_TEXT_COLOR
                    EFFECT_VOLUME = 1.0
                    MUSIC_VOLUME = 1.0
                    # apply volumes and bgm
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    play_sound('menu')
                elif reset_scores_rect.collidepoint(mx, my):
                    x_wins = o_wins = draws = 0
                    play_sound('menu')
                elif back_rect.collidepoint(mx, my):
                    save_settings()
                    play_sound('menu')
                    return

            elif event.type == pygame.MOUSEBUTTONUP:
                dragging = None

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if dragging == "eff":
                    EFFECT_VOLUME = clamp01((mx - eff_rect.x) / eff_rect.w)
                    # throttle click to once while dragging
                    now = pygame.time.get_ticks()
                    if now - _last_volume_click_time > _VOLUME_CLICK_THROTTLE_MS:
                        _last_volume_click_time = now
                        play_sound('menu_select')
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                    _volume_changed_time = pygame.time.get_ticks()
                elif dragging == "mus":
                    MUSIC_VOLUME = clamp01((mx - mus_rect.x) / mus_rect.w)
                    now = pygame.time.get_ticks()
                    if now - _last_volume_click_time > _VOLUME_CLICK_THROTTLE_MS:
                        _last_volume_click_time = now
                        play_sound('menu_select')
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    _volume_changed_time = pygame.time.get_ticks()
                elif isinstance(dragging, tuple):
                    who, idx = dragging
                    if who in ("X","O","BG"):
                        new_rgb = update_color_from_mouse(who, idx, mx)
                        set_color(who, new_rgb)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    continue
                if selected_input:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        target, idx = selected_input
                        commit_numeric_input(target, idx, input_text)
                        selected_input = None; input_text = ""
                    elif event.key == pygame.K_BACKSPACE:
                        input_text = input_text[:-1]
                    else:
                        ch = event.unicode
                        if ch.isdigit() and len(input_text) < 3:
                            input_text += ch
                else:
                    if event.key == pygame.K_ESCAPE:
                        save_settings(); return

        # draw numeric editing overlay if editing
        if selected_input:
            target, idx = selected_input
            box = input_boxes[target][idx]
            # draw darker box
            pygame.draw.rect(screen, (20,20,20), box)
            pygame.draw.rect(screen, (200,200,200), box, 2)
            draw_text_center(input_text or "0", FONT_SMALL, TEXT_COLOR, screen, box.centerx, box.centery)
            pygame.display.flip()

        clock.tick(60)

# -------------------------
# Play loop & events
# -------------------------
def play_one_game():
    reset_board()
    global player, _volume_changed_time
    while running:
        # always ensure bgm is playing per user's selection 1
        start_bgm(loop=True)
        draw_lines(); draw_figures(); display_scoreboard()
        display_volume_hud_if_needed()
        pygame.display.update()
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                set_display_mode(event.w, event.h, full=fullscreen)
                draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                continue
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # map to board coords
                if BOARD_LEFT <= mx < BOARD_LEFT + 3 * SQUARE_SIZE and BOARD_TOP <= my < BOARD_TOP + 3 * SQUARE_SIZE:
                    cell_x = (mx - BOARD_LEFT) // SQUARE_SIZE
                    cell_y = (my - BOARD_TOP) // SQUARE_SIZE
                    if game_mode == "PVP":
                        if available_square(cell_y, cell_x):
                            mark_square(cell_y, cell_x, player)
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
                        if available_square(cell_y, cell_x):
                            mark_square(cell_y, cell_x, player)
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
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                    continue
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
        pygame.time.delay(8)
    return False

# -------------------------
# End screen with clickable Restart/Menu
# -------------------------
def display_end_options(message):
    screen.fill(END_BG)
    result = FONT_LARGE.render(message, True, END_TEXT)
    screen.blit(result, (WIDTH//2 - result.get_width()//2, HEIGHT//2 - 120))
    # clickable buttons
    restart_rect = pygame.Rect(WIDTH//2 - 220, HEIGHT//2 - 20, 200, 64)
    menu_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 20, 200, 64)
    pygame.draw.rect(screen, (60,180,60), restart_rect)
    pygame.draw.rect(screen, (180,60,60), menu_rect)
    draw_text_center("Restart", FONT_MED, (255,255,255), screen, restart_rect.centerx, restart_rect.centery)
    draw_text_center("Menu", FONT_MED, (255,255,255), screen, menu_rect.centerx, menu_rect.centery)
    pygame.display.update()
    return restart_rect, menu_rect

def end_screen_loop(message):
    global game_mode, running
    restart_rect, menu_rect = display_end_options(message)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                if restart_rect.collidepoint(mx, my):
                    reset_board(); return True
                if menu_rect.collidepoint(mx, my):
                    game_mode = None; return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)

# -------------------------
# Main
# -------------------------
def main():
    load_settings()
    init_sounds()
    # apply volumes to sounds & music
    try:
        for s in SOUNDS.values():
            if s: s.set_volume(EFFECT_VOLUME)
    except Exception:
        pass
    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass
    # attempt to start bgm loop if loaded
    try:
        start_bgm(loop=True)
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
