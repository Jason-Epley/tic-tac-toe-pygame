import pygame
import sys
import random

# Initialization
pygame.init()
pygame.font.init()

# --- Constants ---
WIDTH, HEIGHT = 600, 600
LINE_WIDTH = 10
BOARD_ROWS = 3
BOARD_COLS = 3
SQUARE_SIZE = WIDTH // BOARD_COLS
CIRCLE_RADIUS = SQUARE_SIZE // 3
CIRCLE_WIDTH = 15
CROSS_WIDTH = 25
SPACE = SQUARE_SIZE // 4

# Colors (R,G,B)
BG_COLOR = (10, 10, 10)
LINE_COLOR = (150, 150, 150)
O_COLOR = (0, 255, 255)
X_COLOR = (0, 255, 0)
TEXT_COLOR = (255, 255, 255)
MENU_BG = (30, 30, 30)
END_BG = (10, 10, 10)
END_TEXT = (255, 255, 255)

# Highlight settings for winning line
HIGHLIGHT_COLOR = (255, 50, 50)
HIGHLIGHT_WIDTH = 12
HIGHLIGHT_FLASHES = 6
HIGHLIGHT_DELAY_MS = 140

# Highlight Cell / pulse settings
HIGHLIGHT_COLOR = (255, 50, 50)
PULSE_STEPS = 6           # number of radius steps for expand/contract
PULSE_PULSES = 3          # how many full pulses (expand+contract cycles)
PULSE_TOTAL_MS = 600      # total ms per pulse (expand+contract)
PULSE_LINE_WIDTH = 8      # thickness of pulsing outline

# --- Screen Setup ---
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Tic Tac Toe")
font = pygame.font.SysFont(None, 36)
large_font = pygame.font.SysFont(None, 60)

# --- Global State ---
board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]
game_mode = None  # "PVP", "AI_EASY", "AI_HARD"
player = "X"
running = False

# --- Scoreboard ---
x_wins = 0
o_wins = 0
draws = 0

# Helper / Game functions
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
    # board background and lines
    screen.fill(BG_COLOR)
    # Horizontal
    pygame.draw.line(screen, LINE_COLOR, (0, SQUARE_SIZE), (WIDTH, SQUARE_SIZE), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (0, 2 * SQUARE_SIZE), (WIDTH, 2 * SQUARE_SIZE), LINE_WIDTH)
    # Vertical
    pygame.draw.line(screen, LINE_COLOR, (SQUARE_SIZE, 0), (SQUARE_SIZE, HEIGHT), LINE_WIDTH)
    pygame.draw.line(screen, LINE_COLOR, (2 * SQUARE_SIZE, 0), (2 * SQUARE_SIZE, HEIGHT), LINE_WIDTH)

def draw_figures():
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] == "O":
                pygame.draw.circle(
                    screen,
                    O_COLOR,
                    (int(col * SQUARE_SIZE + SQUARE_SIZE // 2),
                     int(row * SQUARE_SIZE + SQUARE_SIZE // 2)),
                    CIRCLE_RADIUS,
                    CIRCLE_WIDTH,
                )
            elif board[row][col] == "X":
                start_desc = (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SPACE)
                end_desc = (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE)
                pygame.draw.line(screen, X_COLOR, start_desc, end_desc, CROSS_WIDTH)
                start_asc = (col * SQUARE_SIZE + SPACE, row * SQUARE_SIZE + SQUARE_SIZE - SPACE)
                end_asc = (col * SQUARE_SIZE + SQUARE_SIZE - SPACE, row * SQUARE_SIZE + SPACE)
                pygame.draw.line(screen, X_COLOR, start_asc, end_asc, CROSS_WIDTH)

def mark_square(row, col, mark):
    board[row][col] = mark

def available_square(row, col):
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS and board[row][col] is None

def is_board_full():
    for row in range(BOARD_ROWS):
        for col in range(BOARD_COLS):
            if board[row][col] is None:
                return False
    return True

# Winning-line helpers
def get_winning_line(player_mark):
    """
    Return list of 3 (row,col) tuples if player_mark has a winning line,
    otherwise return None.
    """
    # Check rows
    for r in range(BOARD_ROWS):
        if board[r][0] == player_mark and board[r][1] == player_mark and board[r][2] == player_mark:
            return [(r, 0), (r, 1), (r, 2)]

    # Check cols
    for c in range(BOARD_COLS):
        if board[0][c] == player_mark and board[1][c] == player_mark and board[2][c] == player_mark:
            return [(0, c), (1, c), (2, c)]

    # Main diagonal
    if board[0][0] == player_mark and board[1][1] == player_mark and board[2][2] == player_mark:
        return [(0, 0), (1, 1), (2, 2)]

    # Anti-diagonal
    if board[0][2] == player_mark and board[1][1] == player_mark and board[2][0] == player_mark:
        return [(0, 2), (1, 1), (2, 0)]

    return None

def cell_center(rc):
    """Return pixel center (x,y) for a board cell (row,col)."""
    r, c = rc
    return (c * SQUARE_SIZE + SQUARE_SIZE // 2, r * SQUARE_SIZE + SQUARE_SIZE // 2)


def draw_winning_line(cells, flash_times=HIGHLIGHT_FLASHES, flash_delay=HIGHLIGHT_DELAY_MS):
    """
    Draw a highlighted line across the winning cells.
    Flashes flash_times times (on/off).
    """
    if not cells:
        return

    # compute start/end pixel coords from first and last cell
    start = cell_center(cells[0])
    end = cell_center(cells[-1])

    # flash: redraw board + pieces then draw/erase highlight
    for i in range(flash_times):
        # redraw base board and pieces
        draw_lines()
        draw_figures()
        display_scoreboard()

        if i % 2 == 0:
            # draw highlight
            pygame.draw.line(screen, HIGHLIGHT_COLOR, start, end, HIGHLIGHT_WIDTH)
        # update and wait
        pygame.display.update()
        pygame.time.delay(flash_delay)
        
def draw_pulsing_circles(cells, pulses=PULSE_PULSES, total_ms=PULSE_TOTAL_MS, steps=PULSE_STEPS, line_width=PULSE_LINE_WIDTH):
    """
    Pulses outline circles on each winning cell center.
    - pulses: number of expand+contract cycles
    - total_ms: total milliseconds per pulse (expand+contract)
    - steps: number of intermediate radii between min and max
    """
    if not cells:
        return

    centers = [cell_center(c) for c in cells]

    # radius range: from slightly larger than drawn symbol to near cell boundary
    min_r = CIRCLE_RADIUS + 6
    max_r = int(SQUARE_SIZE * 0.45)  # leave small margin to cell edges

    # ms per step (expand or contract)
    ms_per_half = max(10, total_ms // 2)  # half for expand, half for contract
    ms_per_step = max(10, ms_per_half // max(1, steps - 1))

    for _ in range(pulses):
        # expand
        for s in range(steps):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines()
            draw_figures()
            display_scoreboard()
            for c in centers:
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update()
            pygame.time.delay(ms_per_step)

        # contract
        for s in reversed(range(steps)):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines()
            draw_figures()
            display_scoreboard()
            for c in centers:
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            pygame.display.update()
            pygame.time.delay(ms_per_step)
    

# Win check (uses get_winning_line)
def check_win(player_mark):
    """
    Return True if player_mark has a winning line, False otherwise.
    """
    return get_winning_line(player_mark) is not None

def display_scoreboard():
    score_text = font.render(f"X Wins: {x_wins}   O Wins: {o_wins}   Draws: {draws}", True, TEXT_COLOR)
    screen.blit(score_text, (10, 10))

def display_message_center(message, duration_ms=1500, front=large_font, color=TEXT_COLOR):
    text = front.render(message, True, color)
    rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(text, rect)
    pygame.display.update()
    if duration_ms > 0:
        pygame.time.delay(duration_ms)

def handle_win(player_mark):
    global x_wins, o_wins
    if player_mark == "X":
        x_wins += 1
    else:
        o_wins += 1

def handle_draw():
    global draws
    draws += 1

# AI: Easy (random) and Hard (Minimax)
def ai_move_easy():
    empty_squares = [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None]
    if empty_squares:
        r, c = random.choice(empty_squares)
        mark_square(r, c, "O")

def evaluate():
    if check_win("O"):
        return 1
    if check_win("X"):
        return -1
    return 0

def minimax(depth, is_maximizing):
    score = evaluate()
    if score == 1 or score == -1:
        return score
    if is_board_full():
        return 0

    if is_maximizing:
        best = -999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "O"
                    best = max(best, minimax(depth + 1, False))
                    board[r][c] = None
        return best
    else:
        best = 999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "X"
                    best = min(best, minimax(depth + 1, True))
                    board[r][c] = None
        return best

def ai_move_hard():
    best_score = -999
    best_move = None
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


# Menu and End screens
def draw_menu():
    screen.fill(MENU_BG)
    title = large_font.render("Tic Tac Toe", True, TEXT_COLOR)
    screen.blit(title, (WIDTH // 2 - title.get_width() // 2, 80))

    options = [
        ("1. Player vs Player", "PVP"),
        ("2. Player vs AI (Easy)", "AI_EASY"),
        ("3. Player vs AI (Hard)", "AI_HARD"),
        ("4. Quit", "QUIT"),
    ]

    y = 220
    for text, _ in options:
        label = font.render(text, True, TEXT_COLOR)
        screen.blit(label, (WIDTH // 2 - label.get_width() // 2, y))
        y += 60

    pygame.display.update()


def menu_loop():
    global game_mode
    while True:
        draw_menu()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_1:
                    game_mode = "PVP"
                    return
                elif event.key == pygame.K_2:
                    game_mode = "AI_EASY"
                    return
                elif event.key == pygame.K_3:
                    game_mode = "AI_HARD"
                    return
                elif event.key == pygame.K_4:
                    pygame.quit()
                    sys.exit()


def display_end_options(message):
    screen.fill(END_BG)
    result = large_font.render(message, True, END_TEXT)
    screen.blit(result, (WIDTH // 2 - result.get_width() // 2, HEIGHT // 2 - 100))

    restart = font.render("Press R to Restart", True, END_TEXT)
    menu = font.render("Press M for Menu", True, END_TEXT)

    screen.blit(restart, (WIDTH // 2 - restart.get_width() // 2, HEIGHT // 2))
    screen.blit(menu, (WIDTH // 2 - menu.get_width() // 2, HEIGHT // 2 + 60))
    pygame.display.update()


def end_screen_loop(message):
    global game_mode
    display_end_options(message)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_r:  # Restart same mode
                    reset_board()
                    return True
                elif event.key == pygame.K_m:  # Back to menu
                    game_mode = None
                    return False

# MAIN PLAY LOOP
def play_one_game():
    """
    Play one match in the currently selected game_mode.
    Returns True if we should restart the same mode, False to return to menu.
    """
    reset_board()
    global player

    while running:
        # Redraw everything each frame
        draw_lines()
        draw_figures()
        display_scoreboard()
        pygame.display.update()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.MOUSEBUTTONDOWN:
                mouseX = event.pos[0] // SQUARE_SIZE
                mouseY = event.pos[1] // SQUARE_SIZE

                if game_mode == "PVP":
                    if available_square(mouseY, mouseX):
                        mark_square(mouseY, mouseX, player)
                        # Check win/draw
                        if check_win(player):
                            win_cells = get_winning_line(player)
                            draw_winning_line(win_cells)
                            draw_pulsing_circles(win_cells)
                            handle_win(player)
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop(f"Player {player} Wins!")
                        elif is_board_full():
                            handle_draw()
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop("It's a Draw!")
                        else:
                            player = "O" if player == "X" else "X"

                elif game_mode in ("AI_EASY", "AI_HARD"):
                    # Human always X, AI is O
                    if available_square(mouseY, mouseX):
                        mark_square(mouseY, mouseX, "X")
                        if check_win("X"):
                            win_cells = get_winning_line("X")
                            draw_winning_line(win_cells)
                            draw_pulsing_circles(win_cells)
                            handle_win("X")
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop("Player X Wins!")
                        elif is_board_full():
                            handle_draw()
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop("It's a Draw!")

                        # AI turn
                        if game_mode == "AI_EASY":
                            ai_move_easy()
                        else:
                            ai_move_hard()

                        # After AI move, check
                        if check_win("O"):
                            win_cells = get_winning_line("O")
                            draw_winning_line(win_cells)
                            draw_pulsing_circles(win_cells)
                            handle_win("O")
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop("Player O Wins!")
                        elif is_board_full():
                            handle_draw()
                            draw_lines()
                            draw_figures()
                            display_scoreboard()
                            pygame.display.update()
                            return end_screen_loop("It's a Draw!")

    # Shouldn't reach here normally
    return False

# Entry point
def main():
    global game_mode, running
    while True:
        if game_mode is None:
            menu_loop()  # set game_mode
        # Play single match in selected mode; returns whether to restart same mode
        restart_same = play_one_game()
        if restart_same:
            continue
        else:
            # go back to menu (game_mode already set to None by end_screen_loop)
            continue


if __name__ == "__main__":
    main()