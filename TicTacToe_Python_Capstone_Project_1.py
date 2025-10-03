# main.py -- Tic Tac Toe with sound + persistent settings menu
import pygame
import sys
import random
import os
import json
from typing import Optional, Dict, Tuple

# -------------------------
# Initialization & constants
# -------------------------
pygame.mixer.pre_init(44100, -16, 2, 512)
pygame.init()
pygame.mixer.set_num_channels(8)

# Files
SETTINGS_FILE = "settings.json"
SOUND_DIR = os.path.join("assets", "sounds")

# Default volumes
DEFAULT_EFFECT_VOLUME = 0.9
DEFAULT_MUSIC_VOLUME = 0.25

# Runtime volume variables (will be loaded from settings)
EFFECT_VOLUME = DEFAULT_EFFECT_VOLUME
MUSIC_VOLUME = DEFAULT_MUSIC_VOLUME

# --- Sound assets dict ---
SOUNDS: Dict[str, Optional[pygame.mixer.Sound]] = {}

def safe_load_sound(path):
    try:
        return pygame.mixer.Sound(path)
    except Exception as e:
        # don't spam if files missing; keep running
        print(f"Warning: couldn’t load sound {path}: {e}")
        return None

def init_sounds():
    base = SOUND_DIR
    SOUNDS['move'] = safe_load_sound(os.path.join(base, "move.wav"))
    SOUNDS['move_ai'] = safe_load_sound(os.path.join(base, "move_ai.wav")) or SOUNDS['move']
    SOUNDS['win'] = safe_load_sound(os.path.join(base, "win.wav"))
    SOUNDS['draw'] = safe_load_sound(os.path.join(base, "draw.wav"))
    SOUNDS['menu'] = safe_load_sound(os.path.join(base, "menu_select.wav"))

    # Set initial effect volumes
    for k in SOUNDS:
        if SOUNDS[k]:
            try:
                SOUNDS[k].set_volume(EFFECT_VOLUME)
            except Exception:
                pass

    # Background music (optional)
    bgm_path = os.path.join(base, "bgm.ogg")
    if os.path.exists(bgm_path):
        try:
            pygame.mixer.music.load(bgm_path)
            pygame.mixer.music.set_volume(MUSIC_VOLUME)
        except Exception as e:
            print(f"Warning: couldn't load bgm: {e}")

# Load settings (if present) before init_sounds so volumes can be applied
def load_settings():
    global EFFECT_VOLUME, MUSIC_VOLUME
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
                EFFECT_VOLUME = float(data.get("effect_volume", DEFAULT_EFFECT_VOLUME))
                MUSIC_VOLUME = float(data.get("music_volume", DEFAULT_MUSIC_VOLUME))
        except Exception as e:
            print(f"Warning: couldn't load settings ({e}), using defaults")

def save_settings():
    try:
        with open(SETTINGS_FILE, "w") as f:
            json.dump({
                "effect_volume": EFFECT_VOLUME,
                "music_volume": MUSIC_VOLUME
            }, f, indent=2)
    except Exception as e:
        print(f"Warning: couldn't save settings ({e})")

# load saved settings (if any) then init sounds with those volumes
load_settings()
init_sounds()

# Screen & style
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
O_COLOR = (0, 200, 230)
X_COLOR = (0, 255, 120)
TEXT_COLOR = (255, 255, 255)
MENU_BG = (30, 30, 30)
END_BG = (10, 10, 10)
END_TEXT = (255, 255, 255)

# highlight/pulse
HIGHLIGHT_COLOR = (255, 50, 50)
HIGHLIGHT_WIDTH = 12
HIGHLIGHT_FLASHES = 6
HIGHLIGHT_DELAY_MS = 120
PULSE_STEPS = 6
PULSE_PULSES = 3
PULSE_TOTAL_MS = 500
PULSE_LINE_WIDTH = 8

# Setup screen & fonts
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic Tac Toe")
pygame.font.init()
font = pygame.font.SysFont(None, 28)
large_font = pygame.font.SysFont(None, 60)
vol_font = pygame.font.SysFont(None, 20)
small_font = pygame.font.SysFont(None, 18)

# Game state
board: list[list[Optional[str]]] = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
game_mode = None  # "PVP", "AI_EASY", "AI_HARD"
player = "X"
running = False

x_wins = 0
o_wins = 0
draws = 0

# volume HUD helper
_volume_changed_time = 0
_VOLUME_HUD_DURATION_MS = 1500

# -------------------------
# Sound helpers
# -------------------------
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
        print(f"BGM error: {e}")

def stop_bgm(fade_ms=300):
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except Exception:
        pass

def set_effect_volume(vol: float):
    global EFFECT_VOLUME, _volume_changed_time
    EFFECT_VOLUME = max(0.0, min(1.0, vol))
    for k in SOUNDS:
        if SOUNDS[k]:
            try:
                SOUNDS[k].set_volume(EFFECT_VOLUME)
            except Exception:
                pass
    _volume_changed_time = pygame.time.get_ticks()
    save_settings()

def set_music_volume(vol: float):
    global MUSIC_VOLUME, _volume_changed_time
    MUSIC_VOLUME = max(0.0, min(1.0, vol))
    try:
        pygame.mixer.music.set_volume(MUSIC_VOLUME)
    except Exception:
        pass
    _volume_changed_time = pygame.time.get_ticks()
    save_settings()

def change_volume(delta: float):
    set_effect_volume(EFFECT_VOLUME + delta)
    set_music_volume(MUSIC_VOLUME + delta)

# -------------------------
# Game drawing & logic
# -------------------------
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
                pygame.draw.circle(screen, O_COLOR,
                                   (int(c * SQUARE_SIZE + SQUARE_SIZE // 2),
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
    if not cells:
        return
    start = cell_center(cells[0])
    end = cell_center(cells[-1])
    for i in range(flash_times):
        draw_lines(); draw_figures(); display_scoreboard()
        if i % 2 == 0:
            pygame.draw.line(screen, HIGHLIGHT_COLOR, start, end, HIGHLIGHT_WIDTH)
        pygame.display.update(); pygame.time.delay(flash_delay)

def draw_pulsing_circles(cells, pulses=PULSE_PULSES, total_ms=PULSE_TOTAL_MS, steps=PULSE_STEPS, line_width=PULSE_LINE_WIDTH):
    if not cells:
        return
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
    score_text = font.render(f"X Wins: {x_wins}   O Wins: {o_wins}   Draws: {draws}", True, TEXT_COLOR)
    screen.blit(score_text, (10, 10))

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
    ev_text = vol_font.render(f"Effects: {int(EFFECT_VOLUME*100)}%", True, (255,255,255))
    mv_text = vol_font.render(f"Music:   {int(MUSIC_VOLUME*100)}%", True, (255,255,255))
    screen.blit(ev_text, (WIDTH - hud_w + 8, 18))
    screen.blit(mv_text, (WIDTH - hud_w + 8, 36))

def handle_win(player_mark):
    global x_wins, o_wins
    if player_mark == "X": x_wins += 1
    else: o_wins += 1
    play_sound('win')

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
# Menu and screens
# -------------------------
def draw_menu():
    screen.fill(MENU_BG)
    title = large_font.render("Tic Tac Toe", True, TEXT_COLOR)
    screen.blit(title, (WIDTH//2 - title.get_width()//2, 60))
    options = [
        ("1. Player vs Player","PVP"),
        ("2. Player vs AI (Easy)","AI_EASY"),
        ("3. Player vs AI (Hard)","AI_HARD"),
        ("4. Quit","QUIT"),
        ("5. Settings","SETTINGS")
    ]
    y=160
    for text,_ in options:
        label = font.render(text, True, TEXT_COLOR)
        screen.blit(label, (WIDTH//2 - label.get_width()//2, y))
        y += 44
    pygame.display.update()

def menu_loop():
    global game_mode
    while True:
        draw_menu()
        for event in pygame.event.get():
            if event.type==pygame.QUIT:
                pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                # global keys
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
                elif event.key==pygame.K_1:
                    play_sound('menu'); game_mode="PVP"; return
                elif event.key==pygame.K_2:
                    play_sound('menu'); game_mode="AI_EASY"; return
                elif event.key==pygame.K_3:
                    play_sound('menu'); game_mode="AI_HARD"; return
                elif event.key==pygame.K_4:
                    play_sound('menu'); pygame.quit(); sys.exit()
                elif event.key==pygame.K_5:
                    play_sound('menu'); settings_screen(); # after this returns, redraw menu

# -------------------------
# Settings screen (persistent)
# -------------------------
# UI geometry for sliders/buttons
SLIDER_W = 300
SLIDER_H = 16
SLIDER_X = WIDTH//2 - SLIDER_W//2
EFFECT_SLIDER_Y = 220
MUSIC_SLIDER_Y = 320

BUTTON_W = 80
BUTTON_H = 34

def draw_slider(x, y, width, height, value, label):
    # background
    pygame.draw.rect(screen, (60,60,60), (x, y, width, height))
    # filled portion
    fill_w = int(width * value)
    pygame.draw.rect(screen, (120,180,120), (x, y, fill_w, height))
    # border
    pygame.draw.rect(screen, (200,200,200), (x, y, width, height), 2)
    # label
    lbl = font.render(f"{label}: {int(value*100)}%", True, TEXT_COLOR)
    screen.blit(lbl, (x, y - 26))

def draw_button(rect: pygame.Rect, text: str, hover: bool=False):
    color = (100,100,100) if not hover else (140,140,140)
    pygame.draw.rect(screen, color, rect, border_radius=6)
    pygame.draw.rect(screen, (220,220,220), rect, 2, border_radius=6)
    lbl = font.render(text, True, TEXT_COLOR)
    screen.blit(lbl, (rect.x + rect.w//2 - lbl.get_width()//2, rect.y + rect.h//2 - lbl.get_height()//2))

def settings_screen():
    global EFFECT_VOLUME, MUSIC_VOLUME, _volume_changed_time
    dragging = None  # "effect" or "music" when dragging sliders
    clock = pygame.time.Clock()
    while True:
        screen.fill(MENU_BG)
        title = large_font.render("Settings", True, TEXT_COLOR)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 80))

        # sliders
        draw_slider(SLIDER_X, EFFECT_SLIDER_Y, SLIDER_W, SLIDER_H, EFFECT_VOLUME, "Effects Volume")
        draw_slider(SLIDER_X, MUSIC_SLIDER_Y, SLIDER_W, SLIDER_H, MUSIC_VOLUME, "Music Volume")

        # +/- buttons for effects
        eff_minus = pygame.Rect(SLIDER_X - 100, EFFECT_SLIDER_Y - 6, BUTTON_W//2, BUTTON_H)
        eff_plus  = pygame.Rect(SLIDER_X + SLIDER_W + 20, EFFECT_SLIDER_Y - 6, BUTTON_W//2, BUTTON_H)
        # +/- buttons for music
        mus_minus = pygame.Rect(SLIDER_X - 100, MUSIC_SLIDER_Y - 6, BUTTON_W//2, BUTTON_H)
        mus_plus  = pygame.Rect(SLIDER_X + SLIDER_W + 20, MUSIC_SLIDER_Y - 6, BUTTON_W//2, BUTTON_H)

        # Reset and Back buttons
        reset_btn = pygame.Rect(WIDTH//2 - 160, MUSIC_SLIDER_Y + 100, 140, BUTTON_H)
        back_btn  = pygame.Rect(WIDTH//2 + 20, MUSIC_SLIDER_Y + 100, 140, BUTTON_H)

        # Draw buttons
        mx, my = pygame.mouse.get_pos()
        draw_button(eff_minus, "-", eff_minus.collidepoint(mx,my))
        draw_button(eff_plus, "+", eff_plus.collidepoint(mx,my))
        draw_button(mus_minus, "-", mus_minus.collidepoint(mx,my))
        draw_button(mus_plus, "+", mus_plus.collidepoint(mx,my))
        draw_button(reset_btn, "Reset", reset_btn.collidepoint(mx,my))
        draw_button(back_btn, "Back", back_btn.collidepoint(mx,my))

        # Small helper text
        hint = small_font.render("Click slider or +/- buttons, or drag the handle. Changes saved on exit.", True, (200,200,200))
        screen.blit(hint, (WIDTH//2 - hint.get_width()//2, MUSIC_SLIDER_Y + 150))

        # Draw current numeric values over sliders
        ev_label = font.render(f"{int(EFFECT_VOLUME*100)}%", True, TEXT_COLOR)
        mv_label = font.render(f"{int(MUSIC_VOLUME*100)}%", True, TEXT_COLOR)
        screen.blit(ev_label, (SLIDER_X + SLIDER_W + 70, EFFECT_SLIDER_Y - 6))
        screen.blit(mv_label, (SLIDER_X + SLIDER_W + 70, MUSIC_SLIDER_Y - 6))

        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings()
                pygame.quit(); sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = event.pos
                # check +/- clicks
                if eff_minus.collidepoint(mx,my):
                    set_effect_volume(EFFECT_VOLUME - 0.05)
                elif eff_plus.collidepoint(mx,my):
                    set_effect_volume(EFFECT_VOLUME + 0.05)
                elif mus_minus.collidepoint(mx,my):
                    set_music_volume(MUSIC_VOLUME - 0.05)
                elif mus_plus.collidepoint(mx,my):
                    set_music_volume(MUSIC_VOLUME + 0.05)
                elif reset_btn.collidepoint(mx,my):
                    set_effect_volume(DEFAULT_EFFECT_VOLUME)
                    set_music_volume(DEFAULT_MUSIC_VOLUME)
                elif back_btn.collidepoint(mx,my):
                    save_settings()
                    return
                # check slider click (start dragging)
                elif pygame.Rect(SLIDER_X, EFFECT_SLIDER_Y, SLIDER_W, SLIDER_H).collidepoint(mx,my):
                    dragging = "effect"
                    # set immediate value based on click pos
                    rel = (mx - SLIDER_X) / SLIDER_W
                    set_effect_volume(rel)
                elif pygame.Rect(SLIDER_X, MUSIC_SLIDER_Y, SLIDER_W, SLIDER_H).collidepoint(mx,my):
                    dragging = "music"
                    rel = (mx - SLIDER_X) / SLIDER_W
                    set_music_volume(rel)

            if event.type == pygame.MOUSEBUTTONUP:
                dragging = None

            if event.type == pygame.MOUSEMOTION and dragging is not None:
                mx, my = event.pos
                rel = (mx - SLIDER_X) / SLIDER_W
                rel = max(0.0, min(1.0, rel))
                if dragging == "effect":
                    set_effect_volume(rel)
                else:
                    set_music_volume(rel)

            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
                elif event.key == pygame.K_ESCAPE:
                    save_settings()
                    return

        clock.tick(60)

# End settings screen

def display_end_options(message):
    screen.fill(END_BG)
    result = large_font.render(message, True, END_TEXT)
    screen.blit(result, (WIDTH//2 - result.get_width()//2, HEIGHT//2 - 100))
    restart = font.render("Press R to Restart", True, END_TEXT)
    menu_txt = font.render("Press M for Menu", True, END_TEXT)
    screen.blit(restart, (WIDTH//2 - restart.get_width()//2, HEIGHT//2))
    screen.blit(menu_txt, (WIDTH//2 - menu_txt.get_width()//2, HEIGHT//2 + 60))
    pygame.display.update()

def end_screen_loop(message):
    global game_mode
    display_end_options(message)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
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
# Main play loop
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
            if event.type == pygame.QUIT: pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX, mouseY = event.pos[0]//SQUARE_SIZE, event.pos[1]//SQUARE_SIZE
                if game_mode == "PVP":
                    if available_square(mouseY, mouseX):
                        mark_square(mouseY, mouseX, player)
                        play_sound('move')
                        if check_win(player):
                            win_cells = get_winning_line(player)
                            draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                            handle_win(player)
                            draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            return end_screen_loop(f"Player {player} Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            return end_screen_loop("It's a Draw!")
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
                            return end_screen_loop("Player X Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            return end_screen_loop("It's a Draw!")
                        if game_mode == "AI_EASY": ai_move_easy()
                        else: ai_move_hard()
                        if check_win("O"):
                            win_cells = get_winning_line("O")
                            draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                            handle_win("O")
                            draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            return end_screen_loop("Player O Wins!")
                        elif is_board_full():
                            handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); pygame.display.update()
                            return end_screen_loop("It's a Draw!")
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
        pygame.time.delay(8)
    return False

# -------------------------
# Menu loop (updated includes Settings)
# -------------------------
def menu_loop():
    global game_mode
    while True:
        draw_menu()
        for event in pygame.event.get():
            if event.type==pygame.QUIT: pygame.quit(); sys.exit()
            if event.type==pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
                elif event.key==pygame.K_1:
                    play_sound('menu'); game_mode="PVP"; return
                elif event.key==pygame.K_2:
                    play_sound('menu'); game_mode="AI_EASY"; return
                elif event.key==pygame.K_3:
                    play_sound('menu'); game_mode="AI_HARD"; return
                elif event.key==pygame.K_4:
                    play_sound('menu'); pygame.quit(); sys.exit()
                elif event.key==pygame.K_5:
                    play_sound('menu'); settings_screen()

# -------------------------
# Small helpers used earlier (defined here for completeness)
# -------------------------
def display_scoreboard():  # already used above
    score_text = font.render(f"X Wins: {x_wins}   O Wins: {o_wins}   Draws: {draws}", True, TEXT_COLOR)
    screen.blit(score_text, (10, 10))

# Re-declare small functions used in play loop to avoid NameError if moved around
def mark_square(row, col, mark):
    board[row][col] = mark

def available_square(row, col):
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS and board[row][col] is None

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
                pygame.draw.circle(screen, O_COLOR,
                                   (int(c * SQUARE_SIZE + SQUARE_SIZE // 2),
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

def check_win(player_mark):
    return get_winning_line(player_mark) is not None

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

# -------------------------
# Entry point
# -------------------------
def main():
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
