# tic_tac_toe.py
"""
Tic-Tac-Toe Game with Pygame

Features:
- Two board sizes: Classic 3x3 and Connect 4-style 4x4
- Three AI difficulty levels: Easy (random), Medium (balanced), Hard (optimized minimax)
- Player vs Player and Player vs AI modes
- Undo move system with move history
- Smooth animations
- Game timer and move counter
- Five color themes + full RGB customization
- Ten player shapes (X, O, Triangle, Square, Plus, Diamond, Star, Heart, Pentagon, Hexagon)
- Sound effects with volume controls
- Settings saved automatically
- Scoreboard tracking

Requirements: Python 3.8+, pygame
Sound files optional (assets/sounds). settings.json auto-created.

Author: Jason Epley
Date: 2025
Version: 1.0
"""

import os
import sys
import json
import random
import time
import traceback
import inspect
import pygame
from typing import Optional, Dict, Tuple
from collections import deque
from game_utils import has_unsaved_shape_changes

# -------------------------
# Basic setup
# -------------------------
VERSION = "1.0"
BASE_DIR = os.path.dirname(os.path.abspath(__file__))

def resource_path(*parts):
    """Get file path that works in both source and PyInstaller exe.
    Usage: resource_path('assets', 'sounds')
    """
    if getattr(sys, 'frozen', False):
        # PyInstaller places files in _MEIPASS (onefile) or next to the exe (onedir)
        base = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base = BASE_DIR
    return os.path.join(base, *parts)


# --- Default configuration and globals ---
# Logical drawing size (adjusted by set_display_mode at runtime)
WIDTH = 1000
HEIGHT = 700

# Default board size and derived layout values
DEFAULT_BOARD_SIZE = 3
GAME_SIZE = DEFAULT_BOARD_SIZE
BOARD_ROWS = GAME_SIZE
BOARD_COLS = GAME_SIZE
WIN_LEN = GAME_SIZE

# Default colors and UI constants
DEFAULT_X_COLOR = (200, 40, 40)
DEFAULT_O_COLOR = (40, 40, 200)
DEFAULT_BG_COLOR = (18, 18, 18)
DEFAULT_TEXT_COLOR = (255, 255, 255)
# Default color used for grid/line drawing (contrasts with background)
DEFAULT_LINE_COLOR = (200, 200, 200)
DEFAULT_EFFECT_VOLUME = 1.0
DEFAULT_MUSIC_VOLUME = 1.0
DEFAULT_X_SHAPE = "X"
DEFAULT_O_SHAPE = "O"
SHAPE_OPTIONS = ["X", "O", "Square", "Triangle", "Diamond"]

# Visual/animation defaults
HIGHLIGHT_FLASHES = 6
HIGHLIGHT_DELAY_MS = 120
HIGHLIGHT_COLOR = (255, 220, 40)
HIGHLIGHT_WIDTH = 6

# Pulsing circle defaults used on win highlight
PULSE_PULSES = 2
PULSE_TOTAL_MS = 600
PULSE_STEPS = 8
PULSE_LINE_WIDTH = 4

# End screen defaults (background and text)
END_BG = (12, 12, 12)
# Runtime defaults (may be overridden by load_settings())
X_COLOR = DEFAULT_X_COLOR
O_COLOR = DEFAULT_O_COLOR
BG_COLOR = DEFAULT_BG_COLOR
TEXT_COLOR = DEFAULT_TEXT_COLOR
# line color used for drawing the board grid
LINE_COLOR = DEFAULT_LINE_COLOR
EFFECT_VOLUME = DEFAULT_EFFECT_VOLUME
MUSIC_VOLUME = DEFAULT_MUSIC_VOLUME
X_SHAPE = DEFAULT_X_SHAPE
O_SHAPE = DEFAULT_O_SHAPE

# Theme presets
THEMES = {
    "Classic Dark": {
        "x_color": (200, 40, 40),
        "o_color": (40, 40, 200),
        "bg_color": (18, 18, 18),
        "text_color": (255, 255, 255),
        "line_color": (200, 200, 200)
    },
    "Ocean": {
        "x_color": (255, 140, 50),
        "o_color": (50, 180, 255),
        "bg_color": (10, 30, 50),
        "text_color": (200, 230, 255),
        "line_color": (80, 150, 200)
    },
    "Forest": {
        "x_color": (220, 180, 50),
        "o_color": (50, 160, 80),
        "bg_color": (20, 30, 20),
        "text_color": (230, 255, 230),
        "line_color": (100, 150, 100)
    },
    "Sunset": {
        "x_color": (255, 100, 100),
        "o_color": (255, 200, 100),
        "bg_color": (40, 20, 40),
        "text_color": (255, 240, 220),
        "line_color": (200, 150, 150)
    },
    "Neon": {
        "x_color": (255, 0, 255),
        "o_color": (0, 255, 255),
        "bg_color": (10, 10, 10),
        "text_color": (255, 255, 0),
        "line_color": (100, 255, 100)
    }
}

# Asset/settings paths
SOUND_DIR = resource_path('assets', 'sounds')
SETTINGS_FILE = os.path.join(BASE_DIR, 'settings.json')

# Settings UI state
settings_current_tab = "Appearance"  # "Appearance", "Audio", "Game"
settings_collapsed = {
    "colors": False,  # Start expanded so RGB sliders are immediately accessible
    "themes": True,
    "shapes": True,
    "text_color": True
}

def compute_board_layout() -> dict:
    """Calculate board layout based on window size and board dimensions.
    Returns SQUARE_SIZE, BOARD_LEFT, BOARD_TOP, CIRCLE_RADIUS, CIRCLE_WIDTH, CROSS_WIDTH.
    """
    # Choose square size to fit comfortably within the window while leaving space for UI
    max_board_w = int(WIDTH * 0.72)
    max_board_h = int(HEIGHT * 0.66)
    # avoid division by zero
    cols = max(1, BOARD_COLS)
    rows = max(1, BOARD_ROWS)
    square_w = max(24, max_board_w // cols)
    square_h = max(24, max_board_h // rows)
    square = min(square_w, square_h)
    board_w = square * cols
    board_h = square * rows
    left = max(8, (WIDTH - board_w) // 2)
    top = max(64, (HEIGHT - board_h) // 2)
    circle_radius = max(10, square // 3)
    circle_width = max(3, square // 12)
    cross_width = max(4, square // 10)
    return {
        'SQUARE_SIZE': square,
        'BOARD_LEFT': left,
        'BOARD_TOP': top,
        'CIRCLE_RADIUS': circle_radius,
        'CIRCLE_WIDTH': circle_width,
        'CROSS_WIDTH': cross_width,
    }


# Initialize pygame font module early so FONT_* are available for debug rendering.
try:
    pygame.font.init()
    FONT = pygame.font.SysFont(None, 28)
    FONT_SMALL = pygame.font.SysFont(None, 18)
    FONT_MED = pygame.font.SysFont(None, 22)
    FONT_LARGE = pygame.font.SysFont(None, 48)
except Exception:
    # In extremely headless environments fonts may fail; provide placeholders
    FONT = FONT_SMALL = FONT_MED = FONT_LARGE = None


def set_game_size(n: int):
    """Set the board/game size (3x3 or 4x4) and recompute layout and board state."""
    global GAME_SIZE, BOARD_ROWS, BOARD_COLS, WIN_LEN
    if n not in (3, 4):
        return
    GAME_SIZE = n
    BOARD_ROWS = n
    BOARD_COLS = n
    WIN_LEN = n
    # reinitialize the logical board to match the new size first so callers
    # (including tests) can safely mutate the board even if display re-init
    # later raises an exception.
    try:
        new_board()
    except Exception:
        pass
    # recompute layout by re-applying the current display mode
    try:
        set_display_mode(WIDTH, HEIGHT, full=fullscreen)
    except Exception:
        # if display re-init fails, keep the new board we just created
        pass
    # return to the menu to allow user to start a game with the new size
    # If running in headless/test mode (SDL_VIDEODRIVER=dummy), don't enter
    # the interactive menu loop because tests call set_game_size() directly.
    try:
        if os.environ.get('SDL_VIDEODRIVER', '').lower() != 'dummy':
            reset_board()
    except Exception:
        pass

# Display helpers: allow resize and fullscreen toggling
fullscreen = False
screen = None

def set_display_mode(w: int, h: int, full: bool = False, force_use_scaled: Optional[bool] = True):
    """Set the global display mode and recompute layout-related globals."""
    # make sure all names that will be assigned in this function are declared global up-front
    global screen, logical_surf, physical_display, use_scaled, WIDTH, HEIGHT, SQUARE_SIZE, BOARD_LEFT, BOARD_TOP, CIRCLE_RADIUS, CIRCLE_WIDTH, CROSS_WIDTH, SPACE, _LAST_WINDOWED_SIZE, display_initialized
    # Init pygame display if needed (for headless tests with SDL_VIDEODRIVER=dummy)
    try:
        if not pygame.display.get_init():
            try:
                pygame.display.init()
            except Exception:
                pass
    except Exception:
        pass
    # If running under dummy video driver (headless CI), skip display ops
    # and use a logical surface so tests can import safely.

    try:
        if os.environ.get('SDL_VIDEODRIVER', '').lower() == 'dummy':
            try:
                logical_surf = pygame.Surface((int(w), int(h)))
                physical_display = None
                screen = logical_surf
                use_scaled = False
                WIDTH, HEIGHT = int(w), int(h)
                display_initialized = False
                layout = compute_board_layout()
                SQUARE_SIZE = layout['SQUARE_SIZE']
                BOARD_LEFT = layout['BOARD_LEFT']
                BOARD_TOP = layout['BOARD_TOP']
                CIRCLE_RADIUS = layout['CIRCLE_RADIUS']
                CIRCLE_WIDTH = layout['CIRCLE_WIDTH']
                CROSS_WIDTH = layout['CROSS_WIDTH']
                SPACE = max(8, SQUARE_SIZE // 10)
            except Exception:
                pass
            return
    except Exception:
        pass
    # Use desktop resolution for fullscreen mode
    if full:
        try:
            info = pygame.display.Info()
            new_w, new_h = info.current_w, info.current_h
        except Exception:
            new_w, new_h = int(w), int(h)
        # store the last windowed size so we can restore when exiting fullscreen
        try:
            _LAST_WINDOWED_SIZE = (WIDTH, HEIGHT)
        except Exception:
            _LAST_WINDOWED_SIZE = (int(w), int(h))
        # If pygame.SCALED is available we'll let pygame manage scaling and use the
        # physical resolution as the logical drawing size. If not, keep WIDTH/HEIGHT
        # as the logical (windowed) size and create a separate physical display
        # at the desktop resolution; we'll scale the logical surface up when presenting.
    else:
        # restore previous windowed size if available
        try:
            prev_w, prev_h = _LAST_WINDOWED_SIZE
            WIDTH, HEIGHT = int(prev_w), int(prev_h)
        except Exception:
            WIDTH, HEIGHT = int(w), int(h)

    # decide flags
    # Avoid attempting real fullscreen flags when running with the dummy video driver
    # (headless test environments) because drivers like 'dummy' don't support them.
    avoid_real_fullscreen = os.environ.get('SDL_VIDEODRIVER', '').lower() == 'dummy'
    flags = pygame.FULLSCREEN if full and not avoid_real_fullscreen else pygame.RESIZABLE

    # If running under the dummy driver, avoid any attempt at real fullscreen
    # and always use a logical surface; this guarantees headless tests won't fail
    # on platforms without real display support.
    if avoid_real_fullscreen and full:
        try:
            logical_surf = pygame.Surface((int(w), int(h)))
            physical_display = None
            screen = logical_surf
            use_scaled = False
            WIDTH, HEIGHT = int(w), int(h)
            display_initialized = False
            layout = compute_board_layout()
            SQUARE_SIZE = layout['SQUARE_SIZE']
            BOARD_LEFT = layout['BOARD_LEFT']
            BOARD_TOP = layout['BOARD_TOP']
            CIRCLE_RADIUS = layout['CIRCLE_RADIUS']
            CIRCLE_WIDTH = layout['CIRCLE_WIDTH']
            CROSS_WIDTH = layout['CROSS_WIDTH']
            SPACE = max(8, SQUARE_SIZE // 10)
        except Exception:
            pass
        return

    # If the user requested fullscreen, prefer a borderless fullscreen window (NOFRAME)
    # and manual scaling. This is more reliable across varied drivers than SCALED on
    # some Windows DPI setups. If NOFRAME fails, we'll fall back to the SCALED path.
    if full and not force_use_scaled:
        try:
            logical_surf = pygame.Surface((int(w), int(h)))
            physical_display = pygame.display.set_mode((new_w, new_h), pygame.NOFRAME)
            screen = logical_surf
            use_scaled = False
            WIDTH, HEIGHT = int(w), int(h)
            display_initialized = True
            # caption set later
            layout = compute_board_layout()
            SQUARE_SIZE = layout['SQUARE_SIZE']
            BOARD_LEFT = layout['BOARD_LEFT']
            BOARD_TOP = layout['BOARD_TOP']
            CIRCLE_RADIUS = layout['CIRCLE_RADIUS']
            CIRCLE_WIDTH = layout['CIRCLE_WIDTH']
            CROSS_WIDTH = layout['CROSS_WIDTH']
            SPACE = max(8, SQUARE_SIZE // 10)
            try:
                if display_initialized:
                    pygame.display.set_caption("Tic Tac Toe")
            except Exception:
                pass
            return
        except Exception:
            # If NOFRAME fails we continue to the existing SCALED/non-scaled logic below
            physical_display = None
            logical_surf = None
            screen = None
            display_initialized = False

    # prepare display surfaces: For fullscreen we will avoid using pygame.SCALED because
    # on some platforms SCALED returns a logical-sized surface instead of a desktop-sized one.
    # Instead, prefer manual scaling via a borderless fullscreen (NOFRAME) window. When not
    # fullscreen, SCALED may still be useful for automatic scaling.
    if force_use_scaled is not None:
        use_scaled = bool(force_use_scaled)
    else:
        use_scaled = False if full else getattr(pygame, 'SCALED', 0) != 0
    # Attempt to create a real display/renderer; if it fails, fall back to logical surface mode
    display_initialized = False
    if use_scaled:
        # include SCALED flag if present for cleaner scaling behavior
        flags = flags | getattr(pygame, 'SCALED', 0)
        try:
            # when SCALED is used, we allow pygame to use the physical resolution as logical
            screen = pygame.display.set_mode((new_w if full else WIDTH, new_h if full else HEIGHT), flags)
            logical_surf = None
            physical_display = None
            # update WIDTH/HEIGHT to match the logical surface used by pygame
            WIDTH, HEIGHT = screen.get_size()
            display_initialized = True
            # If we requested fullscreen but pygame returned a surface sized smaller than the
            # desktop (i.e. it didn't actually create a fullscreen surface at desktop resolution),
            # treat SCALED as ineffective and fall back to manual scaling using a separate physical display.
            try:
                current_size = screen.get_size()
            except Exception:
                current_size = (WIDTH, HEIGHT)
            if full and current_size != (new_w, new_h):
                try:
                    print("[WARN] pygame.SCALED returned a non-desktop surface in fullscreen; using manual scaling fallback.")
                    use_scaled = False
                    # create a logical surface at the game's logical size
                    logical_surf = pygame.Surface((int(w), int(h)))
                    # first try borderless fullscreen (NOFRAME) at desktop size
                    try:
                        physical_display = pygame.display.set_mode((new_w, new_h), pygame.NOFRAME)
                        screen = logical_surf
                        WIDTH, HEIGHT = int(w), int(h)
                        display_initialized = True
                    except Exception:
                        # fallback to normal fullscreen at desktop resolution
                        physical_display = pygame.display.set_mode((new_w, new_h), pygame.FULLSCREEN)
                        screen = logical_surf
                        WIDTH, HEIGHT = int(w), int(h)
                        display_initialized = True
                except Exception:
                    # if that fails, continue with what we have
                    pass
        except Exception as e:
            print(f"[WARN] pygame.display.set_mode (scaled) failed: {e}; falling back to logical surface.")
            # disable scaled behavior because creating the scaled display failed
            use_scaled = False
            # Try to create a non-scaled physical display at desktop resolution as a fallback.
            logical_surf = pygame.Surface((WIDTH, HEIGHT))
            try:
                secondary_flags = pygame.FULLSCREEN if full else pygame.RESIZABLE
                physical_display = pygame.display.set_mode((new_w if full else WIDTH, new_h if full else HEIGHT), secondary_flags)
                screen = logical_surf
                display_initialized = True
            except Exception:
                # final fallback: only logical surface available
                physical_display = None
                screen = logical_surf
                display_initialized = False
    else:
        # when not using SCALED and entering fullscreen, keep WIDTH/HEIGHT as the logical size
        # and create a physical_display at the desktop resolution to blit the scaled logical surface.
        try:
            phys_w, phys_h = (new_w, new_h) if full else (WIDTH, HEIGHT)
            physical_display = pygame.display.set_mode((phys_w, phys_h), flags)
            # logical surface stays at logical WIDTH/HEIGHT so layout remains consistent
            logical_surf = pygame.Surface((WIDTH, HEIGHT))
            screen = logical_surf
            display_initialized = True
        except Exception as e:
            print(f"[WARN] pygame.display.set_mode failed: {e}; using logical surface fallback.")
            logical_surf = pygame.Surface((WIDTH, HEIGHT))
            physical_display = None
            screen = logical_surf
            display_initialized = False
    try:
        if display_initialized:
            pygame.display.set_caption("Tic Tac Toe")
    except Exception:
        pass
    layout = compute_board_layout()
    SQUARE_SIZE = layout['SQUARE_SIZE']
    BOARD_LEFT = layout['BOARD_LEFT']
    BOARD_TOP = layout['BOARD_TOP']
    CIRCLE_RADIUS = layout['CIRCLE_RADIUS']
    CIRCLE_WIDTH = layout['CIRCLE_WIDTH']
    CROSS_WIDTH = layout['CROSS_WIDTH']
    SPACE = max(8, SQUARE_SIZE // 10)
    # prepare logical surface for manual scaling if SCALED isn't available
    try:
        use_scaled = getattr(pygame, 'SCALED', 0) != 0
        if not use_scaled:
            logical_surf = pygame.Surface((WIDTH, HEIGHT))
        else:
            logical_surf = None
    except Exception:
        logical_surf = None
    # Clear the new display to avoid artifacts from previous window contents
    # after a fullscreen/windowed switch.
    try:
        if physical_display is not None:
            try:
                physical_display.fill(BG_COLOR)
            except Exception:
                pass
            try:
                pygame.display.flip()
            except Exception:
                pass
        elif logical_surf is not None:
            try:
                logical_surf.fill(BG_COLOR)
            except Exception:
                pass
            # if no physical display exists yet, ensure any system surface is also cleared
            try:
                disp = pygame.display.get_surface()
                if disp is not None:
                    try:
                        disp.fill(BG_COLOR)
                        pygame.display.flip()
                    except Exception:
                        pass
            except Exception:
                pass
    except Exception:
        pass

def toggle_fullscreen():
    global fullscreen, _SKIP_INPUT_FRAMES
    fullscreen = not fullscreen
    # Main menu toggle: use force_reinit_display for clean renderer recreation
    if globals().get('running') is False and globals().get('game_mode') is None:
        print(f"[TOGGLE-FS] Main menu: toggling to fullscreen={fullscreen}, calling force_reinit_display()")
        try:
            show_status("Applying display…", 900)
        except Exception:
            pass
        try:
            force_reinit_display()
            print("[TOGGLE-FS] force_reinit_display completed successfully")
        except Exception as e:
            print(f"[TOGGLE-FS] force_reinit_display failed: {e}")
        return
        
        # OLD SCALED path (disabled, keeping for reference)
        if False and use_scaled:
            # Simple SCALED sequence: set mode -> delay -> multiple clears -> redraw menu -> present
            print(f"[TOGGLE-FS] SCALED path: toggling to fullscreen={fullscreen}")
            try:
                set_display_mode(WIDTH, HEIGHT, full=fullscreen)
            except Exception as e:
                print(f"[TOGGLE-FS] set_display_mode failed: {e}")
            # Small delay to let display mode settle
            try:
                pygame.time.delay(50)
            except Exception:
                pass
            # Multiple clears to ensure compositor drops old content
            try:
                for i in range(3):
                    ds = pygame.display.get_surface()
                    if ds is not None:
                        ds.fill(BG_COLOR)
                        pygame.display.flip()
                        try:
                            pygame.time.delay(16)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                draw_menu_with_shape_choices(
                    globals().get('X_SHAPE', None),
                    globals().get('O_SHAPE', None),
                    {},
                    do_present=False,
                )
            except Exception as e:
                print(f"[TOGGLE-FS] draw_menu failed: {e}")
            try:
                present()
            except Exception as e:
                print(f"[TOGGLE-FS] present failed: {e}")
            # One final clear after present to ensure clean state
            try:
                ds2 = pygame.display.get_surface()
                if ds2 is not None:
                    ds2.fill(BG_COLOR)
                    pygame.display.flip()
            except Exception:
                pass
            try:
                _SKIP_INPUT_FRAMES = max(_SKIP_INPUT_FRAMES, 6)
            except Exception:
                pass
            print("[TOGGLE-FS] SCALED path completed")
            return
        else:
            # Manual-scaling fallback (non-SCALED): aggressive clear + redraw + present
            try:
                try:
                    set_display_mode(WIDTH, HEIGHT, full=fullscreen, force_use_scaled=False)
                except Exception:
                    force_reinit_display()
            except Exception:
                try:
                    force_reinit_display()
                except Exception:
                    pass
            # Clear the physical display a few times to drop stale content
            try:
                ds = pygame.display.get_surface()
                if ds is not None:
                    for _ in range(3):
                        ds.fill(BG_COLOR)
                        pygame.display.flip()
                        try:
                            pygame.time.delay(20)
                        except Exception:
                            pass
            except Exception:
                pass
            try:
                draw_menu_with_shape_choices(
                    globals().get('X_SHAPE', None),
                    globals().get('O_SHAPE', None),
                    {},
                    do_present=False,
                )
            except Exception:
                pass
            try:
                present()
            except Exception:
                pass
            try:
                _SKIP_INPUT_FRAMES = max(_SKIP_INPUT_FRAMES, 8)
            except Exception:
                pass
            return

    # In-game: prefer lightweight switch to avoid interrupting gameplay
    try:
        set_display_mode(WIDTH, HEIGHT, full=fullscreen)
    except Exception:
        try:
            force_reinit_display()
        except Exception:
            pass

# initialize safe default surfaces; real display init is attempted in main()
# Avoid creating pygame.Surface() at import time to keep imports headless-friendly.
logical_surf = None
physical_display = None
use_scaled = getattr(pygame, 'SCALED', 0) != 0
screen = None
# whether a real display/renderer was successfully created
display_initialized = False
# debug overlay toggle (set to True to show logical/physical sizes on-screen)
DEBUG_DISPLAY_OVERLAY = False
# Diagnostic overlay shown automatically on fallback paths to help debugging
# Disable by default to prefer the pygame.SCALED path when available.
DIAGNOSTIC_ON_FALLBACK = False
# runtime key toggles
DEBUG_OVERLAY_ON_KEY = True  # allow Ctrl+D to toggle overlay at runtime
# Verbose logging for display diagnostics; set True only when investigating
VERBOSE_LOGS = False
# Reinitialization instrumentation (option 2): when enabled, we keep a short
# in-memory history of recent calls to force_reinit_display() and log callsites
# and stack snippets when rapid/repeated calls are observed. This is purely
# diagnostic and does not change behavior (no cooldown or early-return).
_REINIT_INSTRUMENT = True
_REINIT_HISTORY = deque(maxlen=64)
_REINIT_RAPID_MS = 800
# Lightweight cooldown: ignore repeated reinit requests within this window (ms).
# This is enabled now to prevent renderer thrashing. Instrumentation still logs
# skipped calls when `_REINIT_INSTRUMENT` is True.
_LAST_REINIT_MS = 0
_REINIT_COOLDOWN_MS = 800
# Per-caller last reinit timestamps to debounce repeated calls from the same location
_LAST_REINIT_MS_BY_CALLER = {}
# Per-caller last reinit timestamps to debounce repeated calls from the same location
_LAST_REINIT_MS_BY_CALLER = {}
# module-level clock for main loops
clock = pygame.time.Clock()

# After a successful reinit, ignore input for this many frames to allow surfaces to settle
_SKIP_INPUT_FRAMES = 0
# Frames to suppress diagnostic overlays after a reinit
_POST_REINIT_FRAMES = 0
# Whether we've performed the one-time full-window clear after the last reinit
_CLEARED_AFTER_REINIT = False
# Tuning for compositor nudges: number of blank flips before/after present and delay per flip (ms)
_BLANK_FLIPS_PRE = 3
_BLANK_FLIPS_POST = 3
_BLANK_DELAY_MS = 40
_ENABLE_RESIZE_TRICK = False  # keep disabled by default; only enable when diagnosing


# Logical surface and scaling helper (fallback when pygame.SCALED is not available)
logical_surf = None
physical_display = None
use_scaled = getattr(pygame, 'SCALED', 0) != 0

# Lightweight status HUD (e.g., "Applying display…") drawn in present()
_STATUS_MSG = ""
_STATUS_EXPIRE_MS = 0

def show_status(msg: str, duration_ms: int = 800):
    """Show a transient status message overlay for duration_ms.
    It will be rendered in present() so callers can invoke this from anywhere.
    """
    global _STATUS_MSG, _STATUS_EXPIRE_MS
    try:
        _STATUS_MSG = str(msg)
        _STATUS_EXPIRE_MS = pygame.time.get_ticks() + max(0, int(duration_ms))
    except Exception:
        # If pygame isn't initialized yet, just set the text and a short expiry
        _STATUS_MSG = str(msg)
        _STATUS_EXPIRE_MS = 0


def present():
    """Present the current frame. If SCALED is available pygame handles scaling; otherwise
    blit the logical surface to the physical display and flip.
    """
    try:
        # decrement input-skip frames (centralized so all loops benefit)
        # also reference post-reinit counters and cleared flag as module globals
        global _SKIP_INPUT_FRAMES, _POST_REINIT_FRAMES, _CLEARED_AFTER_REINIT
        try:
            if _SKIP_INPUT_FRAMES > 0:
                _SKIP_INPUT_FRAMES -= 1
                # occasional debug print to help diagnose missed clicks
                if VERBOSE_LOGS:
                    try:
                        now = pygame.time.get_ticks()
                        if getattr(present, '_last_input_skip_dbg_ms', 0) + 500 < now:
                            print(f"[INPUT-BLOCK] skipping input frames, remaining={_SKIP_INPUT_FRAMES}")
                            present._last_input_skip_dbg_ms = now
                    except Exception:
                        pass
        except Exception:
            pass
        # decrement overlay suppression counter when present() runs each frame
        try:
            global _POST_REINIT_FRAMES
            if _POST_REINIT_FRAMES > 0:
                _POST_REINIT_FRAMES -= 1
        except Exception:
            pass
        # allow updating the module-level physical_display as a fallback
        global physical_display
        # throttled present debug: print branch and surface identities occasionally
        if VERBOSE_LOGS:
            try:
                now = pygame.time.get_ticks()
                if getattr(present, '_last_debug_ms', 0) + 500 < now:
                    try:
                        ds = pygame.display.get_surface()
                        print(f"[PRESENT-INFO] branch_info use_scaled={use_scaled} display_ok={display_initialized} fullscreen={fullscreen}")
                        print(f"  ids: screen={id(screen)} logical={id(logical_surf)} physical={id(physical_display)} disp_get={id(ds)}")
                        try:
                            print(f"  sizes: WIDTHxHEIGHT={WIDTH}x{HEIGHT} screen_get={(getattr(screen,'get_size',lambda: (None,None))())} logical_get={(logical_surf.get_size() if logical_surf else None)} phys_get={(physical_display.get_size() if physical_display else None)} disp_get={(ds.get_size() if ds else None)}")
                        except Exception:
                            pass
                    except Exception:
                        pass
                    present._last_debug_ms = now
            except Exception:
                pass
        # optional on-screen debug overlay
        if DEBUG_DISPLAY_OVERLAY:
            try:
                # logical size: size of logical_surf or screen when SCALED in use
                logical_size = (WIDTH, HEIGHT) if logical_surf is not None else getattr(screen, 'get_size', lambda: (WIDTH, HEIGHT))()
                physical_size = physical_display.get_size() if physical_display is not None else getattr(screen, 'get_size', lambda: (WIDTH, HEIGHT))()
                status_lines = [f"logical={logical_size[0]}x{logical_size[1]}", f"physical={physical_size[0]}x{physical_size[1]}", f"SCALED={bool(use_scaled)}", f"display_ok={bool(display_initialized)}"]
                info_s = " | ".join(status_lines)
                info_font = FONT_SMALL
                info_surf = info_font.render(info_s, True, (255,255,255))
                bg = pygame.Surface((info_surf.get_width()+12, info_surf.get_height()+8), pygame.SRCALPHA)
                bg.fill((0,0,0,160))
                # blit to top-left
                if logical_surf is not None:
                    logical_surf.blit(bg, (8, 8))
                    logical_surf.blit(info_surf, (14, 12))
                else:
                    try:
                        screen.blit(bg, (8,8))
                        screen.blit(info_surf, (14,12))
                    except Exception:
                        pass
            except Exception:
                pass
        # transient status HUD (e.g., "Applying display…")
        try:
            if _STATUS_MSG and (pygame.time.get_ticks() <= _STATUS_EXPIRE_MS or _STATUS_EXPIRE_MS == 0):
                txt = _STATUS_MSG
                font = FONT_MED or FONT
                if font:
                    msg_surf = font.render(txt, True, (255,255,255))
                    pad_w, pad_h = 24, 14
                    bg = pygame.Surface((msg_surf.get_width()+pad_w, msg_surf.get_height()+pad_h), pygame.SRCALPHA)
                    bg.fill((0,0,0,170))
                    target = logical_surf if logical_surf is not None else screen
                    if target is not None:
                        x = WIDTH//2 - bg.get_width()//2
                        y = HEIGHT - bg.get_height() - 20
                        try:
                            target.blit(bg, (x, y))
                            target.blit(msg_surf, (x + pad_w//2, y + pad_h//2))
                        except Exception:
                            pass
        except Exception:
            pass
        # only rely on pygame's SCALED handling if we successfully initialized a real display
        # and not in diagnostic fallback mode. When SCALED+display works we can flip directly.
        if use_scaled and display_initialized and not DIAGNOSTIC_ON_FALLBACK:
            # throttled info for debugging
            if VERBOSE_LOGS:
                try:
                    now = pygame.time.get_ticks()
                    if getattr(present, '_last_log_ms', 0) + 1000 < now:
                        print(f"[PRESENT] using SCALED flip logical={WIDTH}x{HEIGHT}")
                        present._last_log_ms = now
                except Exception:
                    pass
            pygame.display.flip(); return
        # If we've just reinitialized and haven't yet performed a full-window clear,
        # perform multiple blank flips+update to ensure the OS/compositor discards
        # any old window contents before we begin blitting scaled frames. This
        # helps on platforms where a single flip isn't reliable.
        try:
            if _POST_REINIT_FRAMES > 0 and not _CLEARED_AFTER_REINIT:
                try:
                    for _ in range(max(1, _BLANK_FLIPS_PRE)):
                        ds = pygame.display.get_surface()
                        if ds is not None:
                            try:
                                ds.fill(BG_COLOR)
                                pygame.display.flip()
                                try:
                                    pygame.display.update()
                                except Exception:
                                    pass
                            except Exception:
                                pass
                        try:
                            pygame.time.delay(_BLANK_DELAY_MS)
                        except Exception:
                            pass
                except Exception:
                    pass
                _CLEARED_AFTER_REINIT = True
        except Exception:
            pass
        # Prefer to query the current display surface from pygame each frame and
        # blit into it. On some drivers the previously-held `physical_display`
        # object may not be the active surface the compositor uses; using
        # pygame.display.get_surface() reduces that mismatch.
        try:
            disp_surface = pygame.display.get_surface()
        except Exception:
            disp_surface = None

        if logical_surf is not None and disp_surface is not None:
            try:
                phys_w, phys_h = disp_surface.get_size()
                log_w, log_h = logical_surf.get_size()
                # diagnostic print for mapping issues (throttled by present._last_log_ms)
                try:
                    now = pygame.time.get_ticks()
                    if getattr(present, '_last_log_ms', 0) + 1000 < now:
                        print(f"[PRESENT-DBG] manual blit sizes logical={log_w}x{log_h} phys={phys_w}x{phys_h}")
                        present._last_log_ms = now
                except Exception:
                    pass
                # If fullscreen, offer a stretch-to-fit mode that exactly fills the display
                # (no aspect preservation). This guarantees no black margins. Otherwise
                # use aspect-preserving scaling (cover/contain based on fullscreen state).
                # compute aspect-preserving scale
                scale_w = phys_w / log_w
                scale_h = phys_h / log_h
                # When fullscreen, prefer a 'cover' behavior so the image fills the display
                # (this may crop top/bottom). In windowed mode we use 'contain' to avoid cropping.
                if fullscreen:
                    scale = max(scale_w, scale_h)
                else:
                    scale = min(scale_w, scale_h)
                target_w = max(1, int(log_w * scale))
                target_h = max(1, int(log_h * scale))
                scaled = pygame.transform.smoothscale(logical_surf, (target_w, target_h))
                # center the scaled surface on the physical display
                x = (phys_w - target_w) // 2
                y = (phys_h - target_h) // 2
                # fill background (letterbox color = BG_COLOR) on the real
                # display surface from pygame (disp_surface).
                try:
                    disp_surface.fill(BG_COLOR)
                except Exception:
                    pass
                disp_surface.blit(scaled, (x, y))
                # also try to draw a tiny diagnostic overlay directly to the actual
                # display surface so it is visible even if logical-to-physical
                # bookkeeping is inconsistent on this platform.
                try:
                    disp_direct = disp_surface
                    # Only draw diagnostic overlay directly when the display surface
                    # we're returned is the same object we've been using as
                    # disp_surface. Avoid drawing to other surfaces which may be
                    # intermediate or logical surfaces that cause visual duplication.
                    if disp_direct is not None:
                        try:
                            dbg = FONT_SMALL.render(f"logical={log_w}x{log_h} phys={phys_w}x{phys_h}", True, (255,255,255))
                            dbg_bg = pygame.Surface((dbg.get_width()+8, dbg.get_height()+6))
                            dbg_bg.fill((0,0,0))
                            disp_direct.blit(dbg_bg, (8, 8))
                            disp_direct.blit(dbg, (12, 10))
                            # draw a diagnostic crosshair at the physical mouse position
                            try:
                                # Skip drawing the diagnostic crosshair for the first
                                # few frames after a reinit so the initial flips are
                                # not polluted by overlays.
                                if (DIAGNOSTIC_ON_FALLBACK or DEBUG_DISPLAY_OVERLAY) and _POST_REINIT_FRAMES <= 0:
                                    pmx, pmy = pygame.mouse.get_pos()
                                    # bright red crosshair
                                    pygame.draw.line(disp_direct, (255,48,48), (pmx-12, pmy), (pmx+12, pmy), 3)
                                    pygame.draw.line(disp_direct, (255,48,48), (pmx, pmy-12), (pmx, pmy+12), 3)
                                    pygame.draw.circle(disp_direct, (255,200,200), (pmx, pmy), 4)
                            except Exception:
                                pass
                        except Exception:
                            pass
                except Exception:
                    pass
                # throttled info for debugging fallback path
                try:
                    now = pygame.time.get_ticks()
                    if getattr(present, '_last_log_ms', 0) + 1000 < now:
                        print(f"[PRESENT] manual blit logical={log_w}x{log_h} -> phys={phys_w}x{phys_h} (x={x},y={y})")
                        present._last_log_ms = now
                except Exception:
                    pass
                pygame.display.flip()
                # After flipping the drawn content, if we're in the special
                # post-reinit window, perform a few extra blank flips+update to
                # nudge the compositor into accepting the new buffer. This is
                # intentionally limited to the post-reinit period to avoid
                # delaying normal frame presentation.
                try:
                    if _POST_REINIT_FRAMES > 0:
                        for _ in range(max(1, _BLANK_FLIPS_POST)):
                            try:
                                ds2 = pygame.display.get_surface()
                                if ds2 is not None:
                                    ds2.fill(BG_COLOR)
                                    pygame.display.flip()
                                    try:
                                        pygame.display.update()
                                    except Exception:
                                        pass
                            except Exception:
                                pass
                            try:
                                pygame.time.delay(_BLANK_DELAY_MS)
                            except Exception:
                                pass
                        # optional resize nudge: toggle set_mode to same size to force
                        # the window manager/compositor to recompose the window.
                        try:
                            if _ENABLE_RESIZE_TRICK:
                                try:
                                    cur = pygame.display.get_surface()
                                    if cur is not None:
                                        w, h = cur.get_size()
                                        # re-apply same mode flags briefly
                                        try:
                                            pygame.display.set_mode((w, h))
                                            pygame.time.delay(30)
                                            pygame.display.set_mode((w, h))
                                        except Exception:
                                            pass
                                except Exception:
                                    pass
                        except Exception:
                            pass
                except Exception:
                    pass
                return
            except Exception:
                # fallback to scaling to logical size if anything fails
                try:
                    scaled = pygame.transform.smoothscale(logical_surf, (WIDTH, HEIGHT))
                    # attempt to blit to whatever surface pygame currently exposes
                    try:
                        ds_fb = pygame.display.get_surface()
                        if ds_fb is not None:
                            ds_fb.blit(scaled, (0, 0))
                        else:
                            if physical_display is not None:
                                physical_display.blit(scaled, (0, 0))
                    except Exception:
                        if physical_display is not None:
                            physical_display.blit(scaled, (0, 0))
                    pygame.display.flip()
                    return
                except Exception:
                    pass
        # final fallback: attempt a flip on whatever surface exists
        try:
            pygame.display.flip()
        except Exception:
            pass
    except Exception:
        try:
            pygame.display.flip()
        except Exception:
            pass


def map_mouse_pos(pos):
    """Map a physical/display mouse position to logical surface coordinates.
    When manual scaling is in use (logical_surf rendered to a separate physical_display),
    events and pygame.mouse.get_pos() will report physical coordinates. UI hit
    rects are defined in logical coordinates, so we convert here. If mapping isn't
    needed, return the original position.
    """
    try:
        mx, my = pos
        # Ensure physical_display is attached if possible (helps after reinit)
        try:
            global physical_display
            if physical_display is None:
                disp = pygame.display.get_surface()
                if disp is not None:
                    physical_display = disp
        except Exception:
            pass
        # only map when we have a separate logical surface and a physical display
        if logical_surf is not None and physical_display is not None and not use_scaled:
            phys_w, phys_h = physical_display.get_size()
            log_w, log_h = logical_surf.get_size()
            # small diagnostic print to help debug mapping mismatches
            try:
                now = pygame.time.get_ticks()
                if getattr(map_mouse_pos, '_last_dbg_ms', 0) + 1000 < now:
                    print(f"[MAP-DBG] mapping pm=({mx},{my}) phys={phys_w}x{phys_h} log={log_w}x{log_h}")
                    map_mouse_pos._last_dbg_ms = now
            except Exception:
                pass
            # same math as present(): compute scale and letterbox offset
            scale_w = phys_w / log_w
            scale_h = phys_h / log_h
            if fullscreen:
                scale = max(scale_w, scale_h)
            else:
                scale = min(scale_w, scale_h)
            target_w = max(1, int(log_w * scale))
            target_h = max(1, int(log_h * scale))
            offset_x = (phys_w - target_w) // 2
            offset_y = (phys_h - target_h) // 2
            # convert physical -> logical
            lx = int((mx - offset_x) / scale)
            ly = int((my - offset_y) / scale)
            # clamp to logical surface bounds
            lx = max(0, min(log_w - 1, lx))
            ly = max(0, min(log_h - 1, ly))
            return (lx, ly)
    except Exception:
        pass
    return pos


def force_reinit_display():
    """More aggressive display re-init for platforms that lose the renderer/context.
    This will attempt to safely re-create pygame display surfaces by quitting and
    re-initializing the display subsystem and re-calling set_display_mode with the
    current logical size and fullscreen flag.
    """
    global display_initialized, _LAST_REINIT_MS
    # If running in a headless test environment (SDL_VIDEODRIVER=dummy), skip
    # aggressive reinitialization to avoid flaky behavior during automated tests.
    try:
        env_dummy = os.environ.get('SDL_VIDEODRIVER', '').lower() == 'dummy'
        driver_dummy = False
        try:
            # pygame.display.get_driver() may raise if display not initialized
            if pygame.display.get_init():
                driver_dummy = (pygame.display.get_driver().lower() == 'dummy')
            else:
                driver_dummy = False
        except Exception:
            driver_dummy = False
        if env_dummy or (not pygame.display.get_init()) or driver_dummy:
            if _REINIT_INSTRUMENT:
                print("[REINIT-INSTRUMENT] force_reinit_display no-op under headless/dummy driver or uninitialized display")
            return False
    except Exception:
        pass
    try:
        # Instrumentation: capture caller and stack snippet for diagnostics
        try:
            # global cooldown: skip if a reinit occurred very recently from any caller
            try:
                now_ms_gc = int(time.time() * 1000)
                global _LAST_REINIT_MS
                if _LAST_REINIT_MS and (now_ms_gc - _LAST_REINIT_MS) < _REINIT_COOLDOWN_MS:
                    if _REINIT_INSTRUMENT:
                        print(f"[REINIT-INSTRUMENT] global cooldown active; skipping reinit (delta={now_ms_gc - _LAST_REINIT_MS}ms)")
                    return False
            except Exception:
                pass
            if _REINIT_INSTRUMENT:
                frm = None
                try:
                    frm = inspect.stack()[1]
                except Exception:
                    pass
                caller_line = "<unknown>"
                if frm is not None:
                    try:
                        caller_line = f"{os.path.basename(frm.filename)}:{frm.lineno} in {frm.function}"
                    except Exception:
                        pass
                # print concise one-line caller info for immediate visibility
                if VERBOSE_LOGS:
                    try:
                        print(f"[REINIT-INSTRUMENT] force_reinit_display called by {caller_line}")
                    except Exception:
                        pass
                # per-caller debounce: skip repeated requests from same file:line:function
                try:
                    now_ms = int(time.time() * 1000)
                    caller_key = caller_line
                    last_for_caller = _LAST_REINIT_MS_BY_CALLER.get(caller_key, 0)
                    if last_for_caller and (now_ms - last_for_caller) < _REINIT_COOLDOWN_MS:
                        if _REINIT_INSTRUMENT:
                            print(f"[REINIT-INSTRUMENT] skipping reinit from same caller due to cooldown ({now_ms - last_for_caller}ms) caller={caller_key}")
                        return False
                    # update per-caller and global timestamps
                    _LAST_REINIT_MS_BY_CALLER[caller_key] = now_ms
                    _LAST_REINIT_MS = now_ms
                except Exception:
                    pass
                # now record a richer entry for later rapid-call analysis
                try:
                    stack = traceback.format_stack(limit=8)
                    entry = {'ts': now_ms, 'caller': caller_line, 'stack': stack}
                    _REINIT_HISTORY.append(entry)
                    if len(_REINIT_HISTORY) >= 2:
                        last = _REINIT_HISTORY[-2]
                        if now_ms - last['ts'] <= _REINIT_RAPID_MS:
                            if VERBOSE_LOGS:
                                print(f"[REINIT-INSTRUMENT] rapid reinit detected: {len(_REINIT_HISTORY)} entries (last callers):")
                                for e in list(_REINIT_HISTORY)[-4:]:
                                    t_rel = (e['ts'] - _REINIT_HISTORY[0]['ts'])
                                    print(f"  - {t_rel}ms: {e['caller']}")
                                print("  Recent stack (most recent call):")
                                for line in _REINIT_HISTORY[-1]['stack'][-6:]:
                                    for l in line.rstrip().splitlines():
                                        print("    "+l)
                except Exception:
                    pass
        except Exception:
            pass
        if VERBOSE_LOGS:
            print("[INFO] force_reinit_display: reinitializing display subsystem...")
        # try graceful re-init first
        try:
            pygame.display.quit()
        except Exception:
            pass
        try:
            pygame.display.init()
        except Exception:
            pass
        # small delay to allow driver to settle on some platforms
        try:
            pygame.time.delay(60)
        except Exception:
            pass
        # attempt to set the desired mode again
        try:
            set_display_mode(WIDTH, HEIGHT, full=fullscreen)
            display_initialized = True
            try:
                ds = pygame.display.get_surface()
                if VERBOSE_LOGS:
                    print(f"[STARTUP-INFO] screen_id={id(screen)} logical_id={id(logical_surf)} phys_id={id(physical_display)} disp_get_id={id(ds)}")
                    try:
                        print(f"  sizes: WIDTHxHEIGHT={WIDTH}x{HEIGHT} screen_get={(getattr(screen,'get_size',lambda: (None,None))())} logical_get={(logical_surf.get_size() if logical_surf else None)} phys_get={(physical_display.get_size() if physical_display else None)} disp_get={(ds.get_size() if ds else None)}")
                    except Exception:
                        pass
            except Exception:
                pass
            if VERBOSE_LOGS:
                print("[INFO] force_reinit_display: set_display_mode succeeded.")
            try:
                global _CLEARED_AFTER_REINIT
                _CLEARED_AFTER_REINIT = False
            except Exception:
                pass
            try:
                # After a successful reinit, ignore mouse input for a couple frames
                global _SKIP_INPUT_FRAMES
                # give the display a slightly longer settle window to avoid
                # accidental clicks and visible artifacts on some drivers
                _SKIP_INPUT_FRAMES = max(_SKIP_INPUT_FRAMES, 6)
                # suppress diagnostic overlays for a few frames after reinit
                try:
                    global _POST_REINIT_FRAMES
                    _POST_REINIT_FRAMES = max(_POST_REINIT_FRAMES, 3)
                except Exception:
                    pass
                # clear any queued events so we don't process stale input/draw
                # requests that may interleave with our reinit sequence.
                try:
                    pygame.event.clear()
                except Exception:
                    pass
                # pump briefly to let the driver settle
                try:
                    pygame.event.pump()
                except Exception:
                    pass
                # perform an immediate full-window clear+flip to ensure the
                # compositor/OS discards any previous window contents before
                # we redraw the logical surface.
                try:
                    ds = pygame.display.get_surface()
                    if ds is not None:
                        try:
                            ds.fill(BG_COLOR)
                            pygame.display.flip()
                        except Exception:
                            pass
                except Exception:
                    pass
                # If we appear to be at the main menu (not running any game),
                # perform a full menu redraw onto the logical surface so the
                # subsequent present() shows a complete, consistent UI. Do
                # this after clearing and flipping to avoid overlapping draws.
                try:
                    # only redraw the main menu when not in a running game
                    if globals().get('running') is False and globals().get('game_mode') is None:
                        try:
                            # prefer to reuse current shape selections if available
                            sel_x = globals().get('X_SHAPE', None)
                            sel_o = globals().get('O_SHAPE', None)
                            # draw_menu_with_shape_choices will render the menu to
                            # the current `screen` (logical surface) and call present
                            # at the end of its flow. We call it directly to ensure
                            # the logical surface content is up-to-date.
                            draw_menu_with_shape_choices(sel_x, sel_o, {}, do_present=False)
                        except Exception:
                            # best-effort only; don't block reinit
                            pass
                except Exception:
                    pass
                try:
                    present()
                except Exception:
                    pass
                # perform an additional full clear+flip and short delay after present
                # give the OS/compositor a blank frame before the game loop resumes.
                # Fixes transient/stale content on some platforms.
                try:
                    ds2 = pygame.display.get_surface()
                    if ds2 is not None:
                        try:
                            ds2.fill(BG_COLOR)
                            pygame.display.flip()
                        except Exception:
                            pass
                except Exception:
                    pass
                try:
                    pygame.time.delay(40)
                except Exception:
                    pass
                # clear any events generated during redraw so the caller loop
                # doesn't process them immediately and cause duplicate drawing
                try:
                    pygame.event.clear()
                except Exception:
                    pass
                try:
                    pygame.time.delay(40)
                except Exception:
                    pass
                try:
                    present()
                except Exception:
                    pass
            except Exception:
                pass
            return True
        except Exception as e:
            print(f"[WARN] force_reinit_display: set_display_mode failed: {e}")
            display_initialized = False
            return False
    except Exception as e:
        print(f"[ERROR] force_reinit_display unexpected error: {e}")
        display_initialized = False
        return False

# Game state
def new_board():
    """Recreate the global board structure to match BOARD_ROWS and BOARD_COLS."""
    global board
    board = [[None] * BOARD_COLS for _ in range(BOARD_ROWS)]

# initialize board
new_board()
game_mode = None  # "PVP", "AI_EASY", "AI_MEDIUM", "AI_HARD"
player = "X"

# Move history for undo feature
move_history = []  # List of (row, col, player) tuples
game_start_time = 0  # Track when current game started
move_count = 0  # Count moves in current game
running = False

# Undo feedback
_undo_feedback_time = 0
_UNDO_FEEDBACK_DURATION_MS = 1000

# Volume HUD helper
_volume_changed_time = 0
_VOLUME_HUD_DURATION_MS = 1500

# -------------------------
# Sound loading helpers
# -------------------------
SOUNDS: Dict[str, Optional[pygame.mixer.Sound]] = {}
LOADED_SOUNDS: Dict[str, bool] = {}
bgm_available = False

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
    print("\n[INFO] Verifying sound assets...")
    for filename in expected_files:
        ok = any(os.path.exists(cand) for cand in candidates_for(filename))
        status = "OK" if ok else "MISSING"
        print(f"  [{status}] {filename}")

def init_sounds():
    global bgm_available
    expected_files = ["move", "move_ai", "win", "draw", "menu_select", "lose", "bgm"]
    verify_sounds_exist(SOUND_DIR, expected_files)
    # If the mixer isn't initialized we must not attempt to create Sound objects or
    # use pygame.mixer.music — doing so raises 'mixer not initialized'. Skip loading
    # when mixer isn't available and mark sounds as missing.
    if not pygame.mixer.get_init():
        print("[WARN] init_sounds: pygame.mixer not initialized, skipping sound load.")
        for name in ['move','move_ai','win','draw','menu','lose']:
            SOUNDS[name] = None; LOADED_SOUNDS[name] = False
        bgm_available = False
        return
    # load each expected sound and record success/failure
    SOUNDS['move'] = safe_load_sound_by_name("move"); LOADED_SOUNDS['move'] = bool(SOUNDS['move'])
    SOUNDS['move_ai'] = safe_load_sound_by_name("move_ai") or SOUNDS['move']; LOADED_SOUNDS['move_ai'] = bool(SOUNDS['move_ai'])
    SOUNDS['win'] = safe_load_sound_by_name("win"); LOADED_SOUNDS['win'] = bool(SOUNDS['win'])
    SOUNDS['draw'] = safe_load_sound_by_name("draw"); LOADED_SOUNDS['draw'] = bool(SOUNDS['draw'])
    SOUNDS['menu'] = safe_load_sound_by_name("menu_select"); LOADED_SOUNDS['menu'] = bool(SOUNDS['menu'])
    SOUNDS['lose'] = safe_load_sound_by_name("lose"); LOADED_SOUNDS['lose'] = bool(SOUNDS['lose'])

    # Initial effect volumes
    for k, s in SOUNDS.items():
        if s:
            try:
                s.set_volume(EFFECT_VOLUME)
            except Exception:
                pass
    # bgm
    # load bgm separately and record availability
    bgm_available = False
    for cand in candidates_for("bgm"):
        if os.path.exists(cand):
            try:
                pygame.mixer.music.load(cand)
                pygame.mixer.music.set_volume(MUSIC_VOLUME)
                bgm_available = True
            except Exception as e:
                print(f"Warning: couldn't load background music: {e}")
            break

    # print a concise load summary
    print("[INFO] Sound load summary:")
    for k in ['move','move_ai','win','draw','menu','lose']:
        print(f"  {k}: {'LOADED' if LOADED_SOUNDS.get(k) else 'MISSING'}")
    print(f"  bgm: {'AVAILABLE' if bgm_available else 'MISSING'}")

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
        global bgm_available
        if not bgm_available:
            print("background music was not found.")
            return False
        if pygame.mixer.music.get_busy():
            return True
        loops = -1 if loop else 0
        pygame.mixer.music.play(loops=loops, fade_ms=300)
        return True
    except Exception as e:
        print("BGM play error:", e)
        return False

def stop_bgm(fade_ms=300):
    try:
        pygame.mixer.music.fadeout(fade_ms)
    except Exception:
        pass

# -------------------------
# Settings persistence
# -------------------------
def how_to_play_screen():
    """Display game instructions and rules."""
    while True:
        screen.fill(BG_COLOR)
        
        # Title
        draw_text_center("How to Play", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, 50)
        
        # Instructions
        instructions = [
            "OBJECTIVE:",
            "Classic (3x3): Connect 3 shapes in a row horizontally, vertically, or diagonally",
            "Connect 4 (4x4): Connect 4 shapes in a row to win",
            "",
            "CONTROLS:",
            "• Click a square to place your mark",
            "• Ctrl+Z or click Undo button to undo last move(s)",
            "• F11 to toggle fullscreen",
            "• ESC to return to menu",
            "",
            "GAME MODES:",
            "• Player vs Player - Take turns with a friend",
            "• AI Easy - Random moves (good for practice)",
            "• AI Medium - Balanced strategy (moderate challenge)",
            "• AI Hard - Optimal play using minimax algorithm",
            "",
            "CUSTOMIZATION:",
            "• Choose from 5 different player shapes",
            "• Select theme presets or customize RGB colors for shapes and background",
            "• Adjust sound effects and music volume",
            "• Scores are saved automatically",
        ]
        
        y = 110
        for line in instructions:
            if line.startswith("•"):
                color = (200, 200, 255)
                font = FONT_SMALL
            elif line == "" or ":" in line:
                color = (255, 220, 100)
                font = FONT_MED
            else:
                color = TEXT_COLOR
                font = FONT_SMALL
            
            text_surf = font.render(line, True, color)
            screen.blit(text_surf, (WIDTH//2 - text_surf.get_width()//2, y))
            y += 26 if line else 10
        
        # Back button
        back_btn_w, back_btn_h = 150, 45
        back_rect = pygame.Rect(WIDTH//2 - back_btn_w//2, HEIGHT - 70, back_btn_w, back_btn_h)
        mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
        
        pygame.draw.rect(screen, (80, 80, 200), back_rect, border_radius=8)
        if back_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255, 220, 40), back_rect, 3, border_radius=8)
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
            except Exception:
                pass
        else:
            pygame.draw.rect(screen, (255, 255, 255), back_rect, 2, border_radius=8)
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
            except Exception:
                pass
        draw_text_center("Back to Menu", FONT_MED, (255, 255, 255), screen, back_rect.centerx, back_rect.centery)
        
        present()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = map_mouse_pos(event.pos)
                if back_rect.collidepoint(mx, my):
                    play_sound('menu')
                    return
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE or event.key == pygame.K_RETURN:
                    play_sound('menu')
                    return
                elif event.key == pygame.K_F11:
                    toggle_fullscreen()
        
        clock.tick(60)

# -------------------------
# Settings persistence
# -------------------------
def load_settings():
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR, BG_COLOR, TEXT_COLOR, x_wins, o_wins, draws, GAME_SIZE, BOARD_ROWS, BOARD_COLS, WIN_LEN
    if os.path.exists(SETTINGS_FILE):
        try:
            with open(SETTINGS_FILE, "r") as f:
                data = json.load(f)
            EFFECT_VOLUME = float(data.get("effect_volume", DEFAULT_EFFECT_VOLUME))
            MUSIC_VOLUME = float(data.get("music_volume", DEFAULT_MUSIC_VOLUME))
            X_COLOR = tuple(data.get("x_color", DEFAULT_X_COLOR))
            O_COLOR = tuple(data.get("o_color", DEFAULT_O_COLOR))
            # shapes
            X_SHAPE = data.get("x_shape", DEFAULT_X_SHAPE)
            O_SHAPE = data.get("o_shape", DEFAULT_O_SHAPE)
            BG_COLOR = tuple(data.get("bg_color", DEFAULT_BG_COLOR))
            TEXT_COLOR = tuple(data.get("text_color", DEFAULT_TEXT_COLOR))
            x_wins = int(data.get("x_wins", 0))
            o_wins = int(data.get("o_wins", 0))
            draws = int(data.get("draws", 0))
            # board size
            b = int(data.get("board_size", DEFAULT_BOARD_SIZE))
            if b in (3,4):
                GAME_SIZE = b
                BOARD_ROWS = b; BOARD_COLS = b; WIN_LEN = b
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
                "x_shape": X_SHAPE,
                "o_shape": O_SHAPE,
                "bg_color": BG_COLOR,
                "text_color": TEXT_COLOR,
                "board_size": GAME_SIZE,
                "x_wins": x_wins,
                "o_wins": o_wins,
                "draws": draws
            }, f, indent=2)
    except Exception as e:
        print("Warning: couldn't save settings:", e)

# -------------------------
# Helpers (drawing/logic)
# -------------------------
def confirmation_dialog(message, button_yes="Yes", button_no="Cancel"):
    """Display a modal confirmation dialog. Returns True if Yes, False if No/Cancel."""
    dialog_w = 500
    dialog_h = 200
    dialog_x = WIDTH // 2 - dialog_w // 2
    dialog_y = HEIGHT // 2 - dialog_h // 2
    
    btn_w = 120
    btn_h = 45
    btn_gap = 20
    btn_y = dialog_y + dialog_h - btn_h - 25
    yes_rect = pygame.Rect(dialog_x + dialog_w // 2 - btn_w - btn_gap // 2, btn_y, btn_w, btn_h)
    no_rect = pygame.Rect(dialog_x + dialog_w // 2 + btn_gap // 2, btn_y, btn_w, btn_h)
    
    pressed_button = None
    
    while True:
        # Darken background
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        
        # Draw dialog box
        dialog_rect = pygame.Rect(dialog_x, dialog_y, dialog_w, dialog_h)
        pygame.draw.rect(screen, (40, 40, 40), dialog_rect, border_radius=10)
        pygame.draw.rect(screen, (255, 255, 255), dialog_rect, 3, border_radius=10)
        
        # Draw message
        draw_text_center(message, FONT_MED, (255, 255, 255), screen, WIDTH // 2, dialog_y + 60)
        draw_text_center("This cannot be undone.", FONT_SMALL, (200, 200, 100), screen, WIDTH // 2, dialog_y + 95)
        
        # Draw buttons
        mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
        
        # Yes button (red/danger)
        yes_color = (180, 60, 60) if pressed_button != 'yes' else (140, 40, 40)
        if yes_rect.collidepoint(mouse_pos) and pressed_button != 'yes':
            yes_color = tuple(min(255, c + 32) for c in yes_color)
        pygame.draw.rect(screen, yes_color, yes_rect, border_radius=8)
        if yes_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255, 220, 40), yes_rect, 3, border_radius=8)
        else:
            pygame.draw.rect(screen, (255, 255, 255), yes_rect, 2, border_radius=8)
        draw_text_center(button_yes, FONT_MED, (255, 255, 255), screen, yes_rect.centerx, yes_rect.centery)
        
        # No/Cancel button (gray)
        no_color = (80, 80, 80) if pressed_button != 'no' else (60, 60, 60)
        if no_rect.collidepoint(mouse_pos) and pressed_button != 'no':
            no_color = tuple(min(255, c + 32) for c in no_color)
        pygame.draw.rect(screen, no_color, no_rect, border_radius=8)
        if no_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255, 220, 40), no_rect, 3, border_radius=8)
        else:
            pygame.draw.rect(screen, (255, 255, 255), no_rect, 2, border_radius=8)
        draw_text_center(button_no, FONT_MED, (255, 255, 255), screen, no_rect.centerx, no_rect.centery)
        
        present()
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings()
                pygame.quit()
                sys.exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                mx, my = map_mouse_pos(event.pos)
                if yes_rect.collidepoint(mx, my):
                    pressed_button = 'yes'
                elif no_rect.collidepoint(mx, my):
                    pressed_button = 'no'
            elif event.type == pygame.MOUSEBUTTONUP:
                mx, my = map_mouse_pos(event.pos)
                if pressed_button == 'yes' and yes_rect.collidepoint(mx, my):
                    play_sound('menu')
                    return True
                elif pressed_button == 'no' and no_rect.collidepoint(mx, my):
                    play_sound('menu')
                    return False
                pressed_button = None
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    play_sound('menu')
                    return False
        
        clock.tick(60)

def draw_text_center(text, font, color, surface, x, y):
    """Draw text centered at the specified (x, y) position."""
    surf_text = font.render(text, True, color)
    rect = surf_text.get_rect(center=(x, y))
    surface.blit(surf_text, rect)

def draw_lines():
    """Draw the grid lines for the current board size and layout."""
    # background fill
    screen.fill(BG_COLOR)
    # vertical lines
    for c in range(1, BOARD_COLS):
        x = BOARD_LEFT + c * SQUARE_SIZE
        pygame.draw.line(screen, LINE_COLOR, (x, BOARD_TOP), (x, BOARD_TOP + BOARD_ROWS * SQUARE_SIZE), 4)
    # horizontal lines
    for r in range(1, BOARD_ROWS):
        y = BOARD_TOP + r * SQUARE_SIZE
        pygame.draw.line(screen, LINE_COLOR, (BOARD_LEFT, y), (BOARD_LEFT + BOARD_COLS * SQUARE_SIZE, y), 4)

def reset_board():
    global _SKIP_INPUT_FRAMES, _POST_REINIT_FRAMES, _CLEARED_AFTER_REINIT
    global DEBUG_DISPLAY_OVERLAY, game_mode, running
    if VERBOSE_LOGS:
        print("[RESET-BOARD] entering reset_board()")
        try:
            print(f"  screen_id={id(screen)} logical_id={id(logical_surf)} phys_id={id(physical_display)}")
        except Exception:
            pass
    flash_rects = {}
    sel_x = X_SHAPE
    sel_o = O_SHAPE
    tooltip_text = None
    tooltip_expiry = 0
    try:
        option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
    except Exception as e:
        print(f"[RESET-BOARD] draw_menu_with_shape_choices raised: {e}")
        traceback.print_exc()
        option_rects = []
    while True:
        for event in pygame.event.get():
            # Handle window resize while on the main menu to avoid stale/backbuffer artifacts
            if event.type == pygame.VIDEORESIZE:
                try:
                    show_status("Resizing…", 700)
                    set_display_mode(event.w, event.h, full=fullscreen)
                    # Briefly block clicks while driver settles
                    _SKIP_INPUT_FRAMES = max(_SKIP_INPUT_FRAMES, 3)
                    _POST_REINIT_FRAMES = max(_POST_REINIT_FRAMES, 4)
                    _CLEARED_AFTER_REINIT = False
                except Exception:
                    pass
                # Redraw menu immediately after resize and continue loop
                option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                continue
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                # F11 toggles fullscreen
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    # redraw menu after toggling
                    option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                    continue
                # Ctrl+D toggles the debug overlay
                mods = pygame.key.get_mods()
                if (mods & pygame.KMOD_CTRL) and event.key == pygame.K_d:
                    DEBUG_DISPLAY_OVERLAY = not DEBUG_DISPLAY_OVERLAY
                    # redraw menu to show overlay immediately
                    option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                    continue
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                # optionally skip mouse input for a few frames after reinit
                try:
                    if _SKIP_INPUT_FRAMES > 0:
                        # Capture this click and replay it when skip ends, so users
                        # don't need to click twice after a toggle/resize.
                        setattr(reset_board, '_pending_click_pos', event.pos)
                        if VERBOSE_LOGS:
                            now = pygame.time.get_ticks()
                            if getattr(reset_board, '_last_skip_dbg_ms', 0) + 500 < now:
                                print(f"[INPUT-BLOCK] reset_board skipping mouse (frames={_SKIP_INPUT_FRAMES})")
                                reset_board._last_skip_dbg_ms = now
                        continue
                except Exception:
                    pass
                mx, my = map_mouse_pos(event.pos)
                # check menu options
                for i, r in enumerate(option_rects):
                    if r.collidepoint((mx, my)):
                        # ensure globals are updated when a mode is chosen
                        if i == 0:
                            game_mode = "PVP"
                            running = True
                            return
                        if i == 1:
                            game_mode = "AI_EASY"
                            running = True
                            return
                        if i == 2:
                            game_mode = "AI_MEDIUM"
                            running = True
                            return
                        if i == 3:
                            game_mode = "AI_HARD"
                            running = True
                            return
                        if i == 4:
                            # open How to Play screen
                            how_to_play_screen()
                            sel_x = X_SHAPE
                            sel_o = O_SHAPE
                            option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                        if i == 5:
                            # open settings; pass current selections so UI reflects them
                            settings_screen()
                            sel_x = X_SHAPE
                            sel_o = O_SHAPE
                            option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                        if i == 6:
                            pygame.quit()
                            sys.exit()
        # Manually decrement input-skip counter each frame so it doesn't get stuck
        if _SKIP_INPUT_FRAMES > 0:
            _SKIP_INPUT_FRAMES -= 1
            # If a click occurred during skip, replay it once when counter hits 0
            try:
                if _SKIP_INPUT_FRAMES == 0 and hasattr(reset_board, '_pending_click_pos'):
                    pos = getattr(reset_board, '_pending_click_pos')
                    delattr(reset_board, '_pending_click_pos')
                    mx, my = map_mouse_pos(pos)
                    # Try to apply to current option rects
                    for i, r in enumerate(option_rects):
                        if r.collidepoint((mx, my)):
                            # emulate the selection behavior inline
                            if i == 0:
                                game_mode = "PVP"; running = True; return
                            if i == 1:
                                game_mode = "AI_EASY"; running = True; return
                            if i == 2:
                                game_mode = "AI_MEDIUM"; running = True; return
                            if i == 3:
                                game_mode = "AI_HARD"; running = True; return
                            if i == 4:
                                how_to_play_screen()
                                sel_x = X_SHAPE; sel_o = O_SHAPE
                                option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                            if i == 5:
                                settings_screen()
                                sel_x = X_SHAPE; sel_o = O_SHAPE
                                option_rects = draw_menu_with_shape_choices(sel_x, sel_o, flash_rects)
                            if i == 6:
                                pygame.quit(); sys.exit()
                            break
            except Exception:
                pass
        
        clock.tick(60)

def draw_figures():
    """Draw all placed figures on the board using the selected shapes for X and O."""
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            x_center = BOARD_LEFT + c * SQUARE_SIZE + SQUARE_SIZE // 2
            y_center = BOARD_TOP + r * SQUARE_SIZE + SQUARE_SIZE // 2
            mark = board[r][c]
            if mark is None:
                continue
            # choose color and shape for this mark
            if mark == "O":
                color = O_COLOR
                shape = O_SHAPE
            else:
                color = X_COLOR
                shape = X_SHAPE

            # small helper sizes
            half = SQUARE_SIZE // 2
            pad = max(8, SQUARE_SIZE // 10)

            if shape == "O":
                pygame.draw.circle(screen, color, (x_center, y_center), CIRCLE_RADIUS, CIRCLE_WIDTH)
            elif shape == "X":
                padx = max(12, SQUARE_SIZE // 8)
                pygame.draw.line(screen, color,
                                 (x_center - half + padx, y_center - half + padx),
                                 (x_center + half - padx, y_center + half - padx),
                                 CROSS_WIDTH)
                pygame.draw.line(screen, color,
                                 (x_center - half + padx, y_center + half - padx),
                                 (x_center + half - padx, y_center - half + padx),
                                 CROSS_WIDTH)
            elif shape == "Square":
                rect = pygame.Rect(x_center - half + pad, y_center - half + pad, (half - pad)*2, (half - pad)*2)
                pygame.draw.rect(screen, color, rect, CIRCLE_WIDTH)
            elif shape == "Triangle":
                points = [
                    (x_center, y_center - half + pad),
                    (x_center - half + pad, y_center + half - pad),
                    (x_center + half - pad, y_center + half - pad)
                ]
                pygame.draw.polygon(screen, color, points, CIRCLE_WIDTH)
            elif shape == "Diamond":
                points = [
                    (x_center, y_center - half + pad),
                    (x_center - half + pad, y_center),
                    (x_center, y_center + half - pad),
                    (x_center + half - pad, y_center)
                ]
                pygame.draw.polygon(screen, color, points, CIRCLE_WIDTH)

def animate_piece_placement(row, col, mark):
    """Animate a piece being placed with a scale-up effect."""
    animation_frames = 8
    for frame in range(animation_frames):
        scale = (frame + 1) / animation_frames
        screen.fill(BG_COLOR)
        draw_lines()
        
        # Draw all existing pieces
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] and not (r == row and c == col):
                    # Draw normal pieces
                    shape = X_SHAPE if board[r][c] == "X" else O_SHAPE
                    color = X_COLOR if board[r][c] == "X" else O_COLOR
                    x_center = BOARD_LEFT + c * SQUARE_SIZE + SQUARE_SIZE // 2
                    y_center = BOARD_TOP + r * SQUARE_SIZE + SQUARE_SIZE // 2
                    draw_shape_at(x_center, y_center, shape, color, 1.0)
        
        # Draw animating piece with scale
        shape = X_SHAPE if mark == "X" else O_SHAPE
        color = X_COLOR if mark == "X" else O_COLOR
        x_center = BOARD_LEFT + col * SQUARE_SIZE + SQUARE_SIZE // 2
        y_center = BOARD_TOP + row * SQUARE_SIZE + SQUARE_SIZE // 2
        draw_shape_at(x_center, y_center, shape, color, scale)
        
        display_scoreboard()
        present()
        pygame.time.delay(20)

def draw_shape_at(x_center, y_center, shape, color, scale=1.0):
    """Helper to draw a shape at specific coordinates with optional scaling."""
    half = int((SQUARE_SIZE // 2 - SPACE) * scale)
    pad = int(SPACE * scale)
    line_width = max(1, int(CIRCLE_WIDTH * scale))
    
    if shape == "X":
        pygame.draw.line(screen, color, (x_center - half, y_center - half),
                        (x_center + half, y_center + half), line_width)
        pygame.draw.line(screen, color, (x_center + half, y_center - half),
                        (x_center - half, y_center + half), line_width)
    elif shape == "O":
        pygame.draw.circle(screen, color, (x_center, y_center), half, line_width)
    elif shape == "Square":
        rect = pygame.Rect(x_center - half, y_center - half, half * 2, half * 2)
        pygame.draw.rect(screen, color, rect, line_width)
    elif shape == "Triangle":
        points = [
            (x_center, y_center - half),
            (x_center - half, y_center + half),
            (x_center + half, y_center + half)
        ]
        pygame.draw.polygon(screen, color, points, line_width)
    elif shape == "Diamond":
        points = [
            (x_center, y_center - half + pad),
            (x_center - half + pad, y_center),
            (x_center, y_center + half - pad),
            (x_center + half - pad, y_center)
        ]
        pygame.draw.polygon(screen, color, points, line_width)

def mark_square(row, col, mark, animate=True):
    global move_history, move_count
    board[row][col] = mark
    move_history.append((row, col, mark))
    move_count += 1
    
    # Animate the placement
    if animate:
        animate_piece_placement(row, col, mark)

def undo_last_move():
    """Undo the last move(s). Returns True if successful, False if no moves to undo."""
    global player, move_history, move_count, _undo_feedback_time
    
    if not move_history:
        return False
    
    # In AI modes, undo both AI and player moves (2 moves)
    if game_mode in ["AI_EASY", "AI_MEDIUM", "AI_HARD"]:
        moves_to_undo = min(2, len(move_history))
    else:
        moves_to_undo = 1
    
    for _ in range(moves_to_undo):
        if move_history:
            row, col, mark = move_history.pop()
            board[row][col] = None
            move_count -= 1
            # Restore player turn
            player = mark
    
    # Set feedback timer
    _undo_feedback_time = pygame.time.get_ticks()
    
    return True

def display_undo_feedback():
    """Display undo feedback message if within the feedback duration."""
    global _undo_feedback_time
    now = pygame.time.get_ticks()
    if now - _undo_feedback_time < _UNDO_FEEDBACK_DURATION_MS:
        # Calculate fade-out alpha
        elapsed = now - _undo_feedback_time
        alpha = int(255 * (1 - elapsed / _UNDO_FEEDBACK_DURATION_MS))
        
        # Draw feedback message at top center
        msg = "Move undone"
        msg_surf = FONT_MED.render(msg, True, (100, 255, 100))
        msg_surf.set_alpha(alpha)
        msg_rect = msg_surf.get_rect(center=(WIDTH // 2, 30))
        screen.blit(msg_surf, msg_rect)

def draw_tooltip(text, x, y):
    """Draw a tooltip at the specified position."""
    if not text:
        return
    
    # Render text
    tooltip_surf = FONT_SMALL.render(text, True, (255, 255, 255))
    padding = 8
    tooltip_w = tooltip_surf.get_width() + padding * 2
    tooltip_h = tooltip_surf.get_height() + padding * 2
    
    # Position tooltip (avoid going off-screen)
    tooltip_x = min(x, WIDTH - tooltip_w - 10)
    tooltip_y = y + 20  # Below cursor
    if tooltip_y + tooltip_h > HEIGHT:
        tooltip_y = y - tooltip_h - 10  # Above cursor
    
    # Draw background
    tooltip_rect = pygame.Rect(tooltip_x, tooltip_y, tooltip_w, tooltip_h)
    pygame.draw.rect(screen, (40, 40, 40), tooltip_rect, border_radius=4)
    pygame.draw.rect(screen, (255, 220, 40), tooltip_rect, 2, border_radius=4)
    
    # Draw text
    screen.blit(tooltip_surf, (tooltip_x + padding, tooltip_y + padding))

def available_square(row, col):
    return 0 <= row < BOARD_ROWS and 0 <= col < BOARD_COLS and board[row][col] is None

def is_board_full():
    return all(board[r][c] is not None for r in range(BOARD_ROWS) for c in range(BOARD_COLS))

def get_winning_line(player_mark):
    """
    Check if the specified player has a winning line.
    Returns a list of (row, col) tuples representing the winning cells, or None.
    Checks horizontal, vertical, and diagonal lines.
    """
    # Horizontal checks
    for r in range(BOARD_ROWS):
        for start_c in range(0, BOARD_COLS - WIN_LEN + 1):
            cells = [(r, start_c + i) for i in range(WIN_LEN)]
            if all(board[r][start_c + i] == player_mark for i in range(WIN_LEN)):
                return cells
    # Vertical checks
    for c in range(BOARD_COLS):
        for start_r in range(0, BOARD_ROWS - WIN_LEN + 1):
            if all(board[start_r + i][c] == player_mark for i in range(WIN_LEN)):
                return [(start_r + i, c) for i in range(WIN_LEN)]
    # Diagonals (top-left -> bottom-right)
    for start_r in range(0, BOARD_ROWS - WIN_LEN + 1):
        for start_c in range(0, BOARD_COLS - WIN_LEN + 1):
            if all(board[start_r + i][start_c + i] == player_mark for i in range(WIN_LEN)):
                return [(start_r + i, start_c + i) for i in range(WIN_LEN)]
    # Diagonals (top-right -> bottom-left)
    for start_r in range(0, BOARD_ROWS - WIN_LEN + 1):
        for start_c in range(WIN_LEN - 1, BOARD_COLS):
            if all(board[start_r + i][start_c - i] == player_mark for i in range(WIN_LEN)):
                return [(start_r + i, start_c - i) for i in range(WIN_LEN)]
    return None

def cell_center(rc):
    """Return the pixel coordinates of the center of a board cell."""
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
        present(); pygame.time.delay(flash_delay)

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
            present(); pygame.time.delay(ms_per_step)
        for s in reversed(range(steps)):
            r = min_r + (max_r - min_r) * s // max(1, steps - 1)
            draw_lines(); draw_figures(); display_scoreboard()
            for c in centers:
                pygame.draw.circle(screen, HIGHLIGHT_COLOR, c, r, line_width)
            present(); pygame.time.delay(ms_per_step)

def check_win(player_mark):
    """Check if the specified player has won. Returns True if winning line exists."""
    return get_winning_line(player_mark) is not None

def display_scoreboard():
    # Centered top scoreboard
    txt = f"Player 1 Wins: {x_wins}    Player 2 Wins: {o_wins}    Draws: {draws}"
    draw_text_center(txt, FONT_MED, TEXT_COLOR, screen, WIDTH // 2, 36)
    
    # Display elapsed time in top-right corner
    if game_start_time > 0:
        elapsed_seconds = (pygame.time.get_ticks() - game_start_time) // 1000
        minutes = elapsed_seconds // 60
        seconds = elapsed_seconds % 60
        time_txt = f"Time: {minutes:02d}:{seconds:02d}"
        time_surf = FONT_MED.render(time_txt, True, (180, 180, 180))
        screen.blit(time_surf, (WIDTH - time_surf.get_width() - 10, 10))
    
    # Display AI mode notices and move counter - moved to top below scoreboard
    if game_mode in ["AI_EASY", "AI_MEDIUM", "AI_HARD"]:
        if game_mode == "AI_HARD":
            notice = "AI Hard Mode - Please allow for longer loading time"  # Always show full message
            notice_font = FONT_MED  # Use FONT_MED for better visibility
        elif game_mode == "AI_MEDIUM":
            notice = "AI Medium Mode"
            notice_font = FONT_SMALL
        else:
            notice = "AI Easy Mode"
            notice_font = FONT_SMALL
        
        # Show move counter
        if move_count > 0:
            notice += f"  |  Moves: {move_count}"
        
        # Display notice at top, below the scoreboard (scoreboard is at y=36) with brighter color
        draw_text_center(notice, notice_font, (255, 255, 100), screen, WIDTH // 2, 65)

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
# AI (Easy, Medium, Hard)
# -------------------------
def ai_move_easy():
    """AI Easy mode: Make a random move from available squares."""
    empty = [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None]
    if empty:
        r, c = random.choice(empty)
        mark_square(r, c, "O", animate=True)
        play_sound('move_ai')

def ai_move_medium():
    """
    AI Medium mode: 60% chance to make optimal move, 40% chance to make random move.
    Provides a balanced challenge between Easy and Hard difficulties.
    Checks for immediate wins and blocks before making random moves.
    """
    # 60% of the time, play smart (check for wins/blocks)
    if random.random() < 0.6:
        # Check if AI can win immediately
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "O"
                    if check_win("O"):
                        mark_square(r, c, "O", animate=True)
                        play_sound('move_ai')
                        return
                    board[r][c] = None
        
        # Check if AI must block player from winning
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "X"
                    if check_win("X"):
                        board[r][c] = None
                        mark_square(r, c, "O", animate=True)
                        play_sound('move_ai')
                        return
                    board[r][c] = None
    
    # Otherwise (or if no smart move found), play randomly
    ai_move_easy()

def evaluate():
    """Evaluate the board state. Returns 1 if AI wins, -1 if player wins, 0 otherwise."""
    if check_win("O"): return 1
    if check_win("X"): return -1
    return 0

def heuristic_eval():
    """
    Heuristic evaluation for non-terminal board states.
    Used when depth limit is reached in minimax to estimate position quality.
    Returns a score based on potential winning lines and board control.
    """
    # For 4x4 boards, evaluate based on potential winning lines
    score = 0
    
    # Helper to evaluate a line (row, column, or diagonal)
    def eval_line(cells):
        o_count = cells.count("O")
        x_count = cells.count("X")
        empty = cells.count(None)
        
        # Line with only O's and empty spaces is an opportunity
        if o_count > 0 and x_count == 0:
            if o_count == WIN_LEN - 1 and empty == 1:
                return 0.5  # One move from winning
            elif o_count == WIN_LEN - 2 and empty == 2:
                return 0.2  # Two moves from winning
            else:
                return 0.05 * o_count
        
        # Line with only X's and empty spaces is a threat
        elif x_count > 0 and o_count == 0:
            if x_count == WIN_LEN - 1 and empty == 1:
                return -0.5  # Opponent one move from winning
            elif x_count == WIN_LEN - 2 and empty == 2:
                return -0.2  # Opponent two moves from winning
            else:
                return -0.05 * x_count
        
        return 0
    
    # Evaluate rows
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS - WIN_LEN + 1):
            line = [board[r][c + i] for i in range(WIN_LEN)]
            score += eval_line(line)
    
    # Evaluate columns
    for c in range(BOARD_COLS):
        for r in range(BOARD_ROWS - WIN_LEN + 1):
            line = [board[r + i][c] for i in range(WIN_LEN)]
            score += eval_line(line)
    
    # Evaluate diagonals (top-left to bottom-right)
    for r in range(BOARD_ROWS - WIN_LEN + 1):
        for c in range(BOARD_COLS - WIN_LEN + 1):
            line = [board[r + i][c + i] for i in range(WIN_LEN)]
            score += eval_line(line)
    
    # Evaluate diagonals (top-right to bottom-left)
    for r in range(BOARD_ROWS - WIN_LEN + 1):
        for c in range(WIN_LEN - 1, BOARD_COLS):
            line = [board[r + i][c - i] for i in range(WIN_LEN)]
            score += eval_line(line)
    
    return score

def minimax(depth, is_maximizing, alpha=-999, beta=999, max_depth=None):
    """Minimax with alpha-beta pruning and depth limiting for larger boards."""
    # Dynamic depth limit based on board size and number of empty squares
    if max_depth is None:
        empty_count = sum(1 for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None)
        if BOARD_ROWS >= 4:
            # For 4x4, limit depth based on how full the board is
            if empty_count > 12:
                max_depth = 4  # Early game: shallow search
            elif empty_count > 8:
                max_depth = 5  # Mid game: medium search
            elif empty_count > 4:
                max_depth = 6  # Late-mid game: deeper search
            else:
                max_depth = 10  # End game: full search (few positions left)
        else:
            max_depth = 15  # 3x3: can afford deeper search
    
    score = evaluate()
    if score != 0: 
        # Favor quicker wins/losses by adjusting score based on depth
        return score * (10 - depth) if score > 0 else score * (depth - 10)
    if is_board_full(): 
        return 0
    
    # Depth limit reached: use heuristic evaluation
    if depth >= max_depth:
        return heuristic_eval()
    
    if is_maximizing:
        best = -999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "O"
                    best = max(best, minimax(depth+1, False, alpha, beta, max_depth))
                    board[r][c] = None
                    alpha = max(alpha, best)
                    if beta <= alpha:
                        break  # Beta cutoff
            if beta <= alpha:
                break  # Beta cutoff
        return best
    else:
        best = 999
        for r in range(BOARD_ROWS):
            for c in range(BOARD_COLS):
                if board[r][c] is None:
                    board[r][c] = "X"
                    best = min(best, minimax(depth+1, True, alpha, beta, max_depth))
                    board[r][c] = None
                    beta = min(beta, best)
                    if beta <= alpha:
                        break  # Alpha cutoff
            if beta <= alpha:
                break  # Alpha cutoff
        return best

def ai_move_hard():
    """AI using minimax with alpha-beta pruning and move ordering."""
    # Quick win/block check first (huge speedup for common cases)
    # Check if AI can win immediately
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            if board[r][c] is None:
                board[r][c] = "O"
                if check_win("O"):
                    mark_square(r, c, "O", animate=True)
                    play_sound('move_ai')
                    return
                board[r][c] = None
    
    # Check if AI must block player from winning
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            if board[r][c] is None:
                board[r][c] = "X"
                if check_win("X"):
                    board[r][c] = None
                    mark_square(r, c, "O", animate=True)
                    play_sound('move_ai')
                    return
                board[r][c] = None
    
    # Use minimax with alpha-beta pruning for remaining cases
    best_score = -999
    best_move = None
    alpha = -999
    beta = 999
    
    # Collect all possible moves
    moves = [(r, c) for r in range(BOARD_ROWS) for c in range(BOARD_COLS) if board[r][c] is None]
    
    # Move ordering: prioritize center and corners for better pruning
    center = BOARD_ROWS // 2
    def move_priority(move):
        r, c = move
        # Center gets highest priority, then corners, then edges
        if r == center and c == center:
            return 0
        elif (r == 0 or r == BOARD_ROWS-1) and (c == 0 or c == BOARD_COLS-1):
            return 1
        else:
            return 2
    
    moves.sort(key=move_priority)
    
    for r, c in moves:
        board[r][c] = "O"
        score = minimax(0, False, alpha, beta)
        board[r][c] = None
        if score > best_score:
            best_score = score
            best_move = (r, c)
        alpha = max(alpha, best_score)
        if beta <= alpha:
            break  # Prune remaining moves
    
    if best_move:
        mark_square(best_move[0], best_move[1], "O", animate=True)
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
    present()
    return option_rects


def draw_menu_with_shape_choices(sel_x_shape, sel_o_shape, flash_rects=None, tooltip_text=None, tooltip_expiry=0, do_present=True):
    """Draw the main menu. Returns option_rects (list of button rectangles)."""
    if VERBOSE_LOGS:
        try:
            print(f"[DRAW-MENU] entry screen_id={id(screen)} logical_id={id(logical_surf)} phys_id={id(physical_display)} do_present={do_present}")
        except Exception:
            pass
    screen.fill(BG_COLOR)
    draw_text_center("Tic Tac Toe", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, 60)
    options = [
        "Player vs Player",
        "Player vs AI (Easy)",
        "Player vs AI (Medium)",
        "Player vs AI (Hard)",
        "How to Play",
        "Settings",
        "Quit"
    ]
    y = 160
    option_rects = []
    btn_w, btn_h = 320, 48
    gap_y = 24  # Doubled spacing between buttons
    mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
    hand_cursor = False
    for idx, o in enumerate(options):
        rect = pygame.Rect(WIDTH//2 - btn_w//2, y - btn_h//2, btn_w, btn_h)
        option_rects.append(rect)
        is_hovered = rect.collidepoint(mouse_pos)
        # Fill color (use green for PvP, blue for AI Easy, orange for Medium, purple for Hard, cyan for How to Play, gray for settings, red for quit)
        if idx == 0:
            fill_color = (60,180,60)  # Green for PvP
        elif idx == 1:
            fill_color = (80,80,200)  # Blue for Easy
        elif idx == 2:
            fill_color = (200,120,40)  # Orange for Medium
        elif idx == 3:
            fill_color = (120,20,120)  # Purple for Hard
        elif idx == 4:
            fill_color = (40,140,140)  # Cyan for How to Play
        elif idx == 5:
            fill_color = (80,80,80)  # Gray for Settings
        else:
            fill_color = (180,60,60)  # Red for Quit
        # Highlight effect: slightly lighter fill on hover
        if is_hovered:
            fill_color = tuple(min(255, c+32) for c in fill_color)
            hand_cursor = True
        pygame.draw.rect(screen, fill_color, rect, border_radius=8)
        # Outline: yellow accent if hovered, white otherwise
        outline_rect = rect.inflate(8, 8) if is_hovered else rect
        outline_color = (255,220,40) if is_hovered else (255,255,255)
        outline_width = 3 if is_hovered else 2
        pygame.draw.rect(screen, outline_color, outline_rect, outline_width, border_radius=8)
        # Centered text
        draw_text_center(o, FONT_MED, (255,255,255), screen, rect.centerx, rect.centery)
        
        # Add difficulty descriptions for AI modes
        if idx == 1:  # AI Easy
            desc = "(Random moves)"
            desc_surf = FONT_SMALL.render(desc, True, (150, 150, 200))
            screen.blit(desc_surf, (rect.centerx - desc_surf.get_width()//2, rect.bottom + 4))
        elif idx == 2:  # AI Medium
            desc = "(Balanced strategy)"
            desc_surf = FONT_SMALL.render(desc, True, (220, 160, 100))
            screen.blit(desc_surf, (rect.centerx - desc_surf.get_width()//2, rect.bottom + 4))
        elif idx == 3:  # AI Hard
            desc = "(Optimal minimax)"
            desc_surf = FONT_SMALL.render(desc, True, (180, 100, 180))
            screen.blit(desc_surf, (rect.centerx - desc_surf.get_width()//2, rect.bottom + 4))
        
        y += btn_h + gap_y
    # Set mouse cursor to hand if hovering any button (use try/except for compatibility)
    try:
        if hand_cursor:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
        else:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
    except Exception:
        pass
    
    # Display version number at bottom left
    version_text = f"v{VERSION}"
    version_surf = FONT_SMALL.render(version_text, True, (120, 120, 120))
    screen.blit(version_surf, (10, HEIGHT - 25))
    
    # Display keyboard shortcuts hint at bottom center
    controls_text = "Controls: F11 (Fullscreen) | ESC (Menu/Back) | Ctrl+Z (Undo)"
    controls_surf = FONT_SMALL.render(controls_text, True, (120, 120, 120))
    controls_rect = controls_surf.get_rect(center=(WIDTH//2, HEIGHT - 15))
    screen.blit(controls_surf, controls_rect)

    if do_present:
        # Only use the manual-blit path when NOT using SCALED; under SCALED,
        # let present() own the flip to avoid double-present races that can
        # show overlapping frames during window maximize/fullscreen.
        manual_done = False
        try:
            if (not use_scaled) and logical_surf is not None and physical_display is not None:
                try:
                    phys = physical_display
                    phys_w, phys_h = phys.get_size()
                    log_w, log_h = logical_surf.get_size()
                    if VERBOSE_LOGS:
                        print(f"[DRAW-MENU] manual blit sizes logical={log_w}x{log_h} -> phys={phys_w}x{phys_h}")
                    scaled = pygame.transform.smoothscale(logical_surf, (phys_w, phys_h))
                    try:
                        phys.fill(BG_COLOR)
                    except Exception:
                        pass
                    phys.blit(scaled, (0, 0))
                    pygame.display.flip()
                    manual_done = True
                except Exception as e:
                    if VERBOSE_LOGS:
                        print(f"[DRAW-MENU] manual blit failed: {e}")
        except Exception:
            pass
        if not manual_done:
            if VERBOSE_LOGS:
                try:
                    print("[DRAW-MENU] calling present()")
                except Exception:
                    pass
            present()
            if VERBOSE_LOGS:
                try:
                    print("[DRAW-MENU] present() returned")
                except Exception:
                    pass
    return option_rects

# -------------------------
# Simple utilities for settings UI
# -------------------------
def clamp01(x): return max(0.0, min(1.0, x))
def rels_to_rgb(rels): return (int(rels[0]*255), int(rels[1]*255), int(rels[2]*255))
def rgb_to_rels(rgb): return [rgb[0]/255.0, rgb[1]/255.0, rgb[2]/255.0]
def clamp_byte(v): return max(0, min(255, int(v)))

def luminance(color: Tuple[int,int,int]) -> float:
    """Return a perceptual luminance (0-255) for an RGB tuple."""
    r, g, b = color
    # round the computed luminance to avoid floating-point truncation issues
    # (ensures int(luminance((255,255,255))) == 255)
    return round(0.2126 * r + 0.7152 * g + 0.0722 * b, 6)

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
# Settings screen
# -------------------------
def settings_screen():
    """
    Settings screen with tabs (Appearance/Audio/Game) and collapsible sections.
    Two-column layouts, condensed RGB sliders.
    """
    global EFFECT_VOLUME, MUSIC_VOLUME, X_COLOR, O_COLOR, BG_COLOR, TEXT_COLOR, x_wins, o_wins, draws, _last_volume_click_time, X_SHAPE, O_SHAPE
    global settings_current_tab, settings_collapsed

    global DEBUG_DISPLAY_OVERLAY
    try:
        force_reinit_display()
        global screen
        screen = pygame.display.get_surface()
    except Exception:
        pass
    clock = pygame.time.Clock()
    running = True
    dragging = None
    selected_input = None
    input_text = ""
    original_input_value = ""  # Store original value in case user clicks away
    active_color = None
    music_on = True if pygame.mixer.music.get_busy() else False
    pressed_button = None

    # Compact layout tuning
    margin_top = 40
    slider_h = 10  # Thinner sliders
    
    # Color presets
    color_presets = [
        ("Red", (255, 0, 0)),
        ("Green", (0, 255, 0)),
        ("Blue", (0, 100, 255)),
        ("Yellow", (255, 255, 0)),
        ("Pink", (255, 105, 180)),
        ("White", (255, 255, 255))
    ]
    text_presets = [
        ("White text", (255,255,255)),
        ("Gray text", (200,200,200)),
        ("Black text", (0,0,0))
    ]

    # Current slider values
    x_rels = rgb_to_rels(X_COLOR)
    o_rels = rgb_to_rels(O_COLOR)
    bg_rels = rgb_to_rels(BG_COLOR)

    # Preview shapes (commit on Save)
    preview_x_shape = X_SHAPE
    preview_o_shape = O_SHAPE

    def update_color_from_mouse(target, idx, mx, base_x, slider_w):
        if target == "X":
            rel = clamp01((mx - base_x) / slider_w)
            x_rels[idx] = rel
            return rels_to_rgb(x_rels)
        elif target == "O":
            rel = clamp01((mx - base_x) / slider_w)
            o_rels[idx] = rel
            return rels_to_rgb(o_rels)
        else:  # BG
            rel = clamp01((mx - base_x) / slider_w)
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
            v = clamp_byte(int(txt))
        except Exception:
            return
        if target == "X":
            c = list(X_COLOR); c[idx] = v; set_color("X", tuple(c))
        elif target == "O":
            c = list(O_COLOR); c[idx] = v; set_color("O", tuple(c))
        else:
            c = list(BG_COLOR); c[idx] = v; set_color("BG", tuple(c))

    # Main loop
    while running:
        screen.fill(BG_COLOR)
        mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
        hand_cursor = False

        # Draw title
        draw_text_center("Settings", FONT_LARGE, TEXT_COLOR, screen, WIDTH//2, margin_top)

        # Tab navigation
        tab_y = margin_top + 50
        tab_names = ["Appearance", "Audio", "Game"]
        tab_w = 140
        tab_h = 36
        tab_gap = 12
        total_tab_w = len(tab_names) * tab_w + (len(tab_names) - 1) * tab_gap
        tab_start_x = WIDTH // 2 - total_tab_w // 2
        tab_rects = []
        
        for idx, tab_name in enumerate(tab_names):
            tx = tab_start_x + idx * (tab_w + tab_gap)
            tr = pygame.Rect(tx, tab_y, tab_w, tab_h)
            tab_rects.append((tr, tab_name))
            
            # Active tab highlighted
            if tab_name == settings_current_tab:
                pygame.draw.rect(screen, (80, 140, 80), tr, border_radius=8)
                pygame.draw.rect(screen, (255, 255, 255), tr, 3, border_radius=8)
            else:
                pygame.draw.rect(screen, (50, 50, 50), tr, border_radius=8)
                pygame.draw.rect(screen, (140, 140, 140), tr, 2, border_radius=8)
            
            # Hover effect
            if tr.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), tr, 3, border_radius=8)
                hand_cursor = True
            
            draw_text_center(tab_name, FONT_MED, (255, 255, 255), screen, tr.centerx, tr.centery)

        # Content area starts below tabs
        content_y = tab_y + tab_h + 30
        
        # Storage for interactive elements
        all_rects = {
            "sliders": {},
            "inputs": {},
            "buttons": []
        }

        # === APPEARANCE TAB ===
        if settings_current_tab == "Appearance":
            current_y = content_y
            
            # Collapsible section: Color Customization
            section_header_y = current_y
            header_rect = pygame.Rect(WIDTH // 2 - 300, section_header_y, 600, 32)
            # Better visibility: darker background when collapsed, lighter when expanded
            header_bg = (50, 50, 70) if settings_collapsed["colors"] else (40, 60, 40)
            pygame.draw.rect(screen, header_bg, header_rect, border_radius=6)
            
            # Better hover feedback
            if header_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), header_rect, 3, border_radius=6)
                hand_cursor = True
            else:
                # Different border color when collapsed vs expanded
                border_color = (150, 150, 180) if settings_collapsed["colors"] else (120, 180, 120)
                pygame.draw.rect(screen, border_color, header_rect, 2, border_radius=6)
            
            # Collapse/expand arrow with better visibility
            arrow = "▼" if not settings_collapsed["colors"] else "▶"
            arrow_color = (255, 200, 100) if settings_collapsed["colors"] else (150, 255, 150)
            draw_text_center(f"{arrow} Color Customization (RGB Sliders)", FONT_MED, arrow_color, screen, header_rect.centerx, header_rect.centery)
            all_rects["buttons"].append((header_rect, "toggle_colors"))
            current_y += 42

            if not settings_collapsed["colors"]:
                # Two-column layout: Player 1 Color (left) | Player 2 Color (right), BG below
                col_left = int(WIDTH * 0.30)
                col_right = int(WIDTH * 0.70)
                slider_w = int(WIDTH * 0.22)
                slider_v_gap = 32  # Reduced vertical spacing
                
                # Player 1 Color section
                draw_text_center("Player 1 Color", FONT_SMALL, X_COLOR, screen, col_left, current_y)
                # Player 2 Color section
                draw_text_center("Player 2 Color", FONT_SMALL, O_COLOR, screen, col_right, current_y)
                current_y += 28

                x_sliders = []
                o_sliders = []
                x_inputs = []
                o_inputs = []
                
                for i, lbl in enumerate(["R", "G", "B"]):
                    row_y = current_y + i * slider_v_gap
                    
                    # X slider (left)
                    x_base = col_left - slider_w // 2
                    x_rect = pygame.Rect(x_base, row_y, slider_w, slider_h)
                    pygame.draw.rect(screen, (70, 70, 70), x_rect, border_radius=4)
                    pygame.draw.rect(screen, (255, 255, 255), x_rect, 1, border_radius=4)
                    fill_x = int(x_rect.w * x_rels[i])
                    pygame.draw.rect(screen, X_COLOR, (x_rect.x, x_rect.y, fill_x, x_rect.h))
                    
                    # Slider handle
                    handle_x_pos = (x_rect.x + fill_x, x_rect.y + x_rect.h // 2)
                    handle_radius = 10
                    handle_color = (255, 255, 255)
                    if isinstance(dragging, tuple) and dragging[0] == "X" and dragging[1] == i:
                        handle_color = HIGHLIGHT_COLOR
                        handle_radius = 12
                    pygame.draw.circle(screen, handle_color, handle_x_pos, handle_radius)
                    if x_rect.collidepoint(mouse_pos):
                        hand_cursor = True
                    
                    # Label
                    draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, x_rect.x - 18, x_rect.y + x_rect.h // 2)
                    
                    # Value box
                    val_x_rect = pygame.Rect(x_rect.right + 10, row_y - 6, 54, 24)
                    pygame.draw.rect(screen, (30, 30, 30), val_x_rect)
                    if val_x_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), val_x_rect, 2)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (150, 150, 150), val_x_rect, 1)
                    draw_text_center(str(int(X_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_x_rect.centerx, val_x_rect.centery)
                    
                    x_sliders.append((x_rect, x_base))
                    x_inputs.append(val_x_rect)
                    
                    # O slider (right)
                    o_base = col_right - slider_w // 2
                    o_rect = pygame.Rect(o_base, row_y, slider_w, slider_h)
                    pygame.draw.rect(screen, (70, 70, 70), o_rect, border_radius=4)
                    pygame.draw.rect(screen, (255, 255, 255), o_rect, 1, border_radius=4)
                    fill_o = int(o_rect.w * o_rels[i])
                    pygame.draw.rect(screen, O_COLOR, (o_rect.x, o_rect.y, fill_o, o_rect.h))
                    
                    handle_o_pos = (o_rect.x + fill_o, o_rect.y + o_rect.h // 2)
                    handle_o_color = (255, 255, 255)
                    if isinstance(dragging, tuple) and dragging[0] == "O" and dragging[1] == i:
                        handle_o_color = HIGHLIGHT_COLOR
                        handle_radius = 12
                    pygame.draw.circle(screen, handle_o_color, handle_o_pos, 10)
                    if o_rect.collidepoint(mouse_pos):
                        hand_cursor = True
                    
                    draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, o_rect.x - 18, o_rect.y + o_rect.h // 2)
                    
                    val_o_rect = pygame.Rect(o_rect.right + 10, row_y - 6, 54, 24)
                    pygame.draw.rect(screen, (30, 30, 30), val_o_rect)
                    if val_o_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), val_o_rect, 2)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (150, 150, 150), val_o_rect, 1)
                    draw_text_center(str(int(O_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_o_rect.centerx, val_o_rect.centery)
                    
                    o_sliders.append((o_rect, o_base))
                    o_inputs.append(val_o_rect)
                
                all_rects["sliders"]["X"] = x_sliders
                all_rects["sliders"]["O"] = o_sliders
                all_rects["inputs"]["X"] = x_inputs
                all_rects["inputs"]["O"] = o_inputs
                
                current_y += slider_v_gap * 3 + 20
                
                # Background Color (centered, below X and O)
                draw_text_center("Background Color", FONT_SMALL, (255, 255, 255), screen, WIDTH // 2, current_y)
                current_y += 28
                
                bg_sliders = []
                bg_inputs = []
                bg_base = WIDTH // 2 - slider_w // 2
                
                for i, lbl in enumerate(["R", "G", "B"]):
                    row_y = current_y + i * slider_v_gap
                    bg_rect = pygame.Rect(bg_base, row_y, slider_w, slider_h)
                    pygame.draw.rect(screen, (70, 70, 70), bg_rect, border_radius=4)
                    pygame.draw.rect(screen, (255, 255, 255), bg_rect, 1, border_radius=4)
                    fill_bg = int(bg_rect.w * bg_rels[i])
                    pygame.draw.rect(screen, BG_COLOR, (bg_rect.x, bg_rect.y, fill_bg, bg_rect.h))
                    
                    handle_bg_pos = (bg_rect.x + fill_bg, bg_rect.y + bg_rect.h // 2)
                    handle_bg_color = (255, 255, 255)
                    if isinstance(dragging, tuple) and dragging[0] == "BG" and dragging[1] == i:
                        handle_bg_color = HIGHLIGHT_COLOR
                        handle_radius = 12
                    pygame.draw.circle(screen, handle_bg_color, handle_bg_pos, 10)
                    if bg_rect.collidepoint(mouse_pos):
                        hand_cursor = True
                    
                    draw_text_center(lbl, FONT_SMALL, TEXT_COLOR, screen, bg_rect.x - 18, bg_rect.y + bg_rect.h // 2)
                    
                    val_bg_rect = pygame.Rect(bg_rect.right + 10, row_y - 6, 54, 24)
                    pygame.draw.rect(screen, (30, 30, 30), val_bg_rect)
                    if val_bg_rect.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), val_bg_rect, 2)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (150, 150, 150), val_bg_rect, 1)
                    draw_text_center(str(int(BG_COLOR[i])), FONT_SMALL, TEXT_COLOR, screen, val_bg_rect.centerx, val_bg_rect.centery)
                    
                    bg_sliders.append((bg_rect, bg_base))
                    bg_inputs.append(val_bg_rect)
                
                all_rects["sliders"]["BG"] = bg_sliders
                all_rects["inputs"]["BG"] = bg_inputs
                
                current_y += slider_v_gap * 3 + 30
                
                # Color presets row
                draw_text_center(f"Quick Presets (Target: {active_color or 'All'})", FONT_SMALL, TEXT_COLOR, screen, WIDTH // 2, current_y)
                current_y += 24
                
                preset_w = 56
                preset_h = 30
                preset_gap = 10
                total_preset_w = len(color_presets) * preset_w + (len(color_presets) - 1) * preset_gap
                preset_start_x = WIDTH // 2 - total_preset_w // 2
                preset_rects = []
                
                for idx, (name, col) in enumerate(color_presets):
                    px = preset_start_x + idx * (preset_w + preset_gap)
                    pr = pygame.Rect(px, current_y, preset_w, preset_h)
                    pygame.draw.rect(screen, col, pr)
                    if pr.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), pr, 3)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (255, 255, 255), pr, 2)
                    draw_text_center(name, FONT_SMALL, (0, 0, 0), screen, pr.centerx, pr.centery)
                    preset_rects.append((pr, col))
                
                all_rects["preset_colors"] = preset_rects
                current_y += 50

            # Collapsible section: Themes
            section_header_y = current_y
            header_rect = pygame.Rect(WIDTH // 2 - 300, section_header_y, 600, 32)
            header_bg = (50, 50, 70) if settings_collapsed["themes"] else (60, 40, 60)
            pygame.draw.rect(screen, header_bg, header_rect, border_radius=6)
            
            if header_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), header_rect, 3, border_radius=6)
                hand_cursor = True
            else:
                border_color = (150, 150, 180) if settings_collapsed["themes"] else (180, 120, 180)
                pygame.draw.rect(screen, border_color, header_rect, 2, border_radius=6)
            
            arrow = "▼" if not settings_collapsed["themes"] else "▶"
            arrow_color = (255, 200, 100) if settings_collapsed["themes"] else (200, 150, 255)
            draw_text_center(f"{arrow} Theme Presets", FONT_MED, arrow_color, screen, header_rect.centerx, header_rect.centery)
            all_rects["buttons"].append((header_rect, "toggle_themes"))
            current_y += 42

            if not settings_collapsed["themes"]:
                theme_w = 100
                theme_h = 46  # Increased to show color swatches
                theme_gap = 8
                theme_names = list(THEMES.keys())
                total_theme_w = len(theme_names) * theme_w + (len(theme_names) - 1) * theme_gap
                theme_start_x = WIDTH // 2 - total_theme_w // 2
                theme_rects = []
                
                for idx, theme_name in enumerate(theme_names):
                    tx = theme_start_x + idx * (theme_w + theme_gap)
                    tr = pygame.Rect(tx, current_y, theme_w, theme_h)
                    
                    # Get theme colors
                    theme = THEMES[theme_name]
                    x_col = theme["x_color"]
                    o_col = theme["o_color"]
                    bg_col = theme["bg_color"]
                    
                    # Draw background with theme's BG color
                    pygame.draw.rect(screen, bg_col, tr, border_radius=6)
                    
                    # Draw color preview swatches at bottom (3 small circles)
                    swatch_y = tr.bottom - 10
                    swatch_spacing = theme_w // 4
                    swatch_start_x = tr.centerx - swatch_spacing
                    for i, col in enumerate([x_col, bg_col, o_col]):
                        swatch_x = swatch_start_x + i * swatch_spacing
                        pygame.draw.circle(screen, col, (swatch_x, swatch_y), 6)
                        pygame.draw.circle(screen, (255, 255, 255), (swatch_x, swatch_y), 6, 1)
                    
                    # Hover effect
                    if tr.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), tr, 3, border_radius=6)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (140, 140, 140), tr, 2, border_radius=6)
                    
                    # Theme name at top
                    draw_text_center(theme_name, FONT_SMALL, theme["text_color"], screen, tr.centerx, tr.top + 12)
                    theme_rects.append((tr, theme_name))
                
                all_rects["themes"] = theme_rects
                current_y += 60

            # Collapsible section: Player Shapes
            section_header_y = current_y
            header_rect = pygame.Rect(WIDTH // 2 - 300, section_header_y, 600, 32)
            header_bg = (50, 50, 70) if settings_collapsed["shapes"] else (40, 50, 40)
            pygame.draw.rect(screen, header_bg, header_rect, border_radius=6)
            
            if header_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), header_rect, 3, border_radius=6)
                hand_cursor = True
            else:
                border_color = (150, 150, 180) if settings_collapsed["shapes"] else (120, 180, 120)
                pygame.draw.rect(screen, border_color, header_rect, 2, border_radius=6)
            
            arrow = "▼" if not settings_collapsed["shapes"] else "▶"
            arrow_color = (255, 200, 100) if settings_collapsed["shapes"] else (150, 255, 150)
            draw_text_center(f"{arrow} Player Shapes", FONT_MED, arrow_color, screen, header_rect.centerx, header_rect.centery)
            all_rects["buttons"].append((header_rect, "toggle_shapes"))
            current_y += 42

            if not settings_collapsed["shapes"]:
                # Two-column: Player 1 left, Player 2 right
                col_left = int(WIDTH * 0.30)
                col_right = int(WIDTH * 0.70)
                
                draw_text_center("Player 1", FONT_SMALL, TEXT_COLOR, screen, col_left, current_y)
                draw_text_center("Player 2", FONT_SMALL, TEXT_COLOR, screen, col_right, current_y)
                current_y += 28
                
                shape_w = 62
                shape_h = 36
                shape_gap = 8
                total_shape_w = len(SHAPE_OPTIONS) * shape_w + (len(SHAPE_OPTIONS) - 1) * shape_gap
                
                shape_token_rects = []
                
                # Player 1 shapes
                sx1 = col_left - total_shape_w // 2
                for idx, shape in enumerate(SHAPE_OPTIONS):
                    tr = pygame.Rect(sx1 + idx * (shape_w + shape_gap), current_y, shape_w, shape_h)
                    if shape == preview_x_shape:
                        pygame.draw.rect(screen, (90, 160, 90), tr, border_radius=6)
                        pygame.draw.rect(screen, (255, 255, 255), tr, 2, border_radius=6)
                    else:
                        pygame.draw.rect(screen, (40, 40, 40), tr, border_radius=6)
                        pygame.draw.rect(screen, (120, 120, 120), tr, 2, border_radius=6)
                    if tr.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), tr, 3, border_radius=6)
                        hand_cursor = True
                    draw_text_center(shape, FONT_SMALL, (255, 255, 255), screen, tr.centerx, tr.centery)
                    shape_token_rects.append((tr, 'X', shape))
                
                # Player 2 shapes
                sx2 = col_right - total_shape_w // 2
                for idx, shape in enumerate(SHAPE_OPTIONS):
                    tr = pygame.Rect(sx2 + idx * (shape_w + shape_gap), current_y, shape_w, shape_h)
                    if shape == preview_o_shape:
                        pygame.draw.rect(screen, (90, 160, 90), tr, border_radius=6)
                        pygame.draw.rect(screen, (255, 255, 255), tr, 2, border_radius=6)
                    else:
                        pygame.draw.rect(screen, (40, 40, 40), tr, border_radius=6)
                        pygame.draw.rect(screen, (120, 120, 120), tr, 2, border_radius=6)
                    if tr.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), tr, 3, border_radius=6)
                        hand_cursor = True
                    draw_text_center(shape, FONT_SMALL, (255, 255, 255), screen, tr.centerx, tr.centery)
                    shape_token_rects.append((tr, 'O', shape))
                
                all_rects["shapes"] = shape_token_rects
                current_y += 60

            # Collapsible section: Text Color
            section_header_y = current_y
            header_rect = pygame.Rect(WIDTH // 2 - 300, section_header_y, 600, 32)
            header_bg = (50, 50, 70) if settings_collapsed["text_color"] else (50, 40, 50)
            pygame.draw.rect(screen, header_bg, header_rect, border_radius=6)
            
            if header_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), header_rect, 3, border_radius=6)
                hand_cursor = True
            else:
                border_color = (150, 150, 180) if settings_collapsed["text_color"] else (180, 120, 150)
                pygame.draw.rect(screen, border_color, header_rect, 2, border_radius=6)
            
            arrow = "▼" if not settings_collapsed["text_color"] else "▶"
            arrow_color = (255, 200, 100) if settings_collapsed["text_color"] else (200, 150, 200)
            draw_text_center(f"{arrow} Text Color", FONT_MED, arrow_color, screen, header_rect.centerx, header_rect.centery)
            all_rects["buttons"].append((header_rect, "toggle_text_color"))
            current_y += 42

            if not settings_collapsed["text_color"]:
                text_preset_rects = []
                tp_w = 120
                tp_h = 38
                tp_gap = 12
                total_tp_w = len(text_presets) * tp_w + (len(text_presets) - 1) * tp_gap
                tp_start_x = WIDTH // 2 - total_tp_w // 2
                
                for idx, (label, col) in enumerate(text_presets):
                    tx = tp_start_x + idx * (tp_w + tp_gap)
                    tbr = pygame.Rect(tx, current_y, tp_w, tp_h)
                    
                    if label == "Black text":
                        bg_col, txt_col = (255, 255, 255), (0, 0, 0)
                    elif label == "White text":
                        bg_col, txt_col = (0, 0, 0), (255, 255, 255)
                    else:
                        bg_col, txt_col = (0, 0, 0), (200, 200, 200)
                    
                    pygame.draw.rect(screen, bg_col, tbr)
                    if tbr.collidepoint(mouse_pos):
                        pygame.draw.rect(screen, (255, 220, 40), tbr, 3)
                        hand_cursor = True
                    else:
                        pygame.draw.rect(screen, (255, 255, 255), tbr, 2)
                    draw_text_center(label, FONT_SMALL, txt_col, screen, tbr.centerx, tbr.centery)
                    text_preset_rects.append((tbr, col))
                
                all_rects["text_colors"] = text_preset_rects
                current_y += 60

        # === AUDIO TAB ===
        elif settings_current_tab == "Audio":
            current_y = content_y + 30
            
            # Effects Volume
            draw_text_center(f"Sound Effects: {int(EFFECT_VOLUME * 100)}%", FONT_MED, TEXT_COLOR, screen, WIDTH // 2, current_y)
            current_y += 32
            
            slider_w = int(WIDTH * 0.4)
            eff_rect = pygame.Rect(WIDTH // 2 - slider_w // 2, current_y, slider_w, 16)
            pygame.draw.rect(screen, (70, 70, 70), eff_rect, border_radius=6)
            fill_eff = int(eff_rect.w * EFFECT_VOLUME)
            pygame.draw.rect(screen, (120, 180, 120), (eff_rect.x, eff_rect.y, fill_eff, eff_rect.h), border_radius=6)
            
            eff_handle_pos = (eff_rect.x + fill_eff, eff_rect.y + eff_rect.h // 2)
            eff_handle_radius = 12
            eff_handle_color = (255, 255, 255)
            if dragging == "eff":
                eff_handle_color = HIGHLIGHT_COLOR
                eff_handle_radius = 14
            pygame.draw.circle(screen, eff_handle_color, eff_handle_pos, eff_handle_radius)
            if eff_rect.collidepoint(mouse_pos):
                hand_cursor = True
            
            all_rects["eff_slider"] = eff_rect
            current_y += 50
            
            # Music Volume
            draw_text_center(f"Music: {int(MUSIC_VOLUME * 100)}%", FONT_MED, TEXT_COLOR, screen, WIDTH // 2, current_y)
            current_y += 32
            
            mus_rect = pygame.Rect(WIDTH // 2 - slider_w // 2, current_y, slider_w, 16)
            pygame.draw.rect(screen, (70, 70, 70), mus_rect, border_radius=6)
            fill_mus = int(mus_rect.w * MUSIC_VOLUME)
            pygame.draw.rect(screen, (120, 180, 120), (mus_rect.x, mus_rect.y, fill_mus, mus_rect.h), border_radius=6)
            
            mus_handle_pos = (mus_rect.x + fill_mus, mus_rect.y + mus_rect.h // 2)
            mus_handle_radius = 12
            mus_handle_color = (255, 255, 255)
            if dragging == "mus":
                mus_handle_color = HIGHLIGHT_COLOR
                mus_handle_radius = 14
            pygame.draw.circle(screen, mus_handle_color, mus_handle_pos, mus_handle_radius)
            if mus_rect.collidepoint(mouse_pos):
                hand_cursor = True
            
            all_rects["mus_slider"] = mus_rect
            current_y += 50
            
            # Music toggle
            music_toggle_rect = pygame.Rect(WIDTH // 2 - 60, current_y, 24, 24)
            pygame.draw.rect(screen, (0, 0, 0), music_toggle_rect)
            pygame.draw.rect(screen, (255, 255, 255), music_toggle_rect, 2)
            if music_on:
                pygame.draw.rect(screen, (50, 200, 80), music_toggle_rect.inflate(-8, -8))
            if music_toggle_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), music_toggle_rect, 3)
                hand_cursor = True
            draw_text_center("Music On", FONT_MED, TEXT_COLOR, screen, music_toggle_rect.right + 60, music_toggle_rect.centery)
            
            all_rects["music_toggle"] = music_toggle_rect

        # === GAME TAB ===
        elif settings_current_tab == "Game":
            current_y = content_y + 30
            
            # Board size
            draw_text_center("Board Size", FONT_MED, TEXT_COLOR, screen, WIDTH // 2, current_y)
            current_y += 36
            
            sz_w = 140
            sz_h = 36
            sz1_rect = pygame.Rect(WIDTH // 2 - sz_w - 10, current_y, sz_w, sz_h)
            sz2_rect = pygame.Rect(WIDTH // 2 + 10, current_y, sz_w, sz_h)
            
            for rect, label, size in [(sz1_rect, "Classic (3x3)", 3), (sz2_rect, "Connect 4 (4x4)", 4)]:
                if GAME_SIZE == size:
                    pygame.draw.rect(screen, (90, 160, 90), rect, border_radius=8)
                    pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
                else:
                    pygame.draw.rect(screen, (50, 50, 50), rect, border_radius=8)
                    pygame.draw.rect(screen, (120, 120, 120), rect, 2, border_radius=8)
                if rect.collidepoint(mouse_pos):
                    pygame.draw.rect(screen, (255, 220, 40), rect, 3, border_radius=8)
                    hand_cursor = True
                draw_text_center(label, FONT_SMALL, (255, 255, 255), screen, rect.centerx, rect.centery)
            
            all_rects["size_btns"] = [sz1_rect, sz2_rect]
            current_y += 66
            
            # Reset Scores button
            reset_scores_rect = pygame.Rect(WIDTH // 2 - 90, current_y, 180, 42)
            pygame.draw.rect(screen, (120, 20, 120), reset_scores_rect, border_radius=8)
            if reset_scores_rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), reset_scores_rect, 3, border_radius=8)
                hand_cursor = True
            else:
                pygame.draw.rect(screen, (255, 255, 255), reset_scores_rect, 2, border_radius=8)
            draw_text_center("Reset Scores", FONT_MED, (255, 255, 255), screen, reset_scores_rect.centerx, reset_scores_rect.centery)
            all_rects["reset_scores"] = reset_scores_rect

        # Bottom buttons: Save, Reset, Back
        btn_y = HEIGHT - 80
        btn_w = 130
        btn_h = 44
        btn_gap = 16
        total_btn_w = btn_w * 3 + btn_gap * 2
        btn_start_x = WIDTH // 2 - total_btn_w // 2
        
        save_rect = pygame.Rect(btn_start_x, btn_y, btn_w, btn_h)
        reset_rect = pygame.Rect(btn_start_x + btn_w + btn_gap, btn_y, btn_w, btn_h)
        back_rect = pygame.Rect(btn_start_x + (btn_w + btn_gap) * 2, btn_y, btn_w, btn_h)
        
        unsaved_shapes = has_unsaved_shape_changes(X_SHAPE, O_SHAPE, preview_x_shape, preview_o_shape)
        
        for rect, label, color in [
            (save_rect, "Save" + (" *" if unsaved_shapes else ""), (60, 180, 60)),
            (reset_rect, "Reset Settings", (80, 80, 200)),
            (back_rect, "Back", (180, 60, 60))
        ]:
            if pressed_button == label.split()[0].lower():
                color = tuple(max(0, c - 40) for c in color)
            pygame.draw.rect(screen, color, rect, border_radius=8)
            if rect.collidepoint(mouse_pos):
                pygame.draw.rect(screen, (255, 220, 40), rect, 3, border_radius=8)
                hand_cursor = True
            else:
                pygame.draw.rect(screen, (255, 255, 255), rect, 2, border_radius=8)
            # Use smaller font for Reset Settings button to fit text
            font_to_use = FONT_SMALL if "Reset Settings" in label else FONT_MED
            draw_text_center(label, font_to_use, (255, 255, 255), screen, rect.centerx, rect.centery)
        
        all_rects["save"] = save_rect
        all_rects["reset"] = reset_rect
        all_rects["back"] = back_rect

        # Set cursor
        try:
            if hand_cursor:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
            else:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
        except Exception:
            pass

        # Display input text overlay when typing in RGB boxes
        if selected_input:
            target, idx = selected_input
            # Find the corresponding input box rect
            if target in all_rects.get("inputs", {}):
                input_rects = all_rects["inputs"][target]
                if idx < len(input_rects):
                    input_box = input_rects[idx]
                    # Draw the input text in the box (highlighted)
                    pygame.draw.rect(screen, (60, 60, 100), input_box)
                    pygame.draw.rect(screen, (255, 220, 40), input_box, 2)
                    # Display the input_text being typed (blank if empty)
                    if input_text:
                        draw_text_center(input_text, FONT_SMALL, (255, 255, 100), screen, input_box.centerx, input_box.centery)

        present()

        # Event handling
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                set_display_mode(event.w, event.h, full=fullscreen)
                break
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                try:
                    if _SKIP_INPUT_FRAMES > 0:
                        continue
                except Exception:
                    pass
                mx, my = map_mouse_pos(event.pos)
                
                # Check if user clicked away from the selected input box
                clicked_on_input_box = False
                if selected_input and "inputs" in all_rects:
                    target, idx = selected_input
                    if target in all_rects["inputs"] and idx < len(all_rects["inputs"][target]):
                        if all_rects["inputs"][target][idx].collidepoint(mx, my):
                            clicked_on_input_box = True
                
                # If clicked elsewhere (not on the same input box), deselect and restore original value
                if selected_input and not clicked_on_input_box:
                    # Check if we're clicking on a different input box (handled later)
                    clicking_different_input = False
                    if "inputs" in all_rects:
                        for target in ["X", "O", "BG"]:
                            if target in all_rects["inputs"]:
                                for i, rect in enumerate(all_rects["inputs"][target]):
                                    if rect.collidepoint(mx, my):
                                        clicking_different_input = True
                                        break
                            if clicking_different_input:
                                break
                    
                    # If not clicking a different input, restore and deselect
                    if not clicking_different_input:
                        # Restore original value if input was empty or invalid
                        if not input_text or not input_text.isdigit():
                            target, idx = selected_input
                            # Restore the original value
                            if original_input_value.isdigit():
                                val = int(original_input_value)
                                if target == "X":
                                    X_COLOR = (X_COLOR[0] if idx != 0 else val,
                                              X_COLOR[1] if idx != 1 else val,
                                              X_COLOR[2] if idx != 2 else val)
                                elif target == "O":
                                    O_COLOR = (O_COLOR[0] if idx != 0 else val,
                                              O_COLOR[1] if idx != 1 else val,
                                              O_COLOR[2] if idx != 2 else val)
                                else:
                                    BG_COLOR = (BG_COLOR[0] if idx != 0 else val,
                                               BG_COLOR[1] if idx != 1 else val,
                                               BG_COLOR[2] if idx != 2 else val)
                        selected_input = None
                        input_text = ""
                        original_input_value = ""
                
                # Tab clicks
                for tr, tab_name in tab_rects:
                    if tr.collidepoint(mx, my):
                        settings_current_tab = tab_name
                        play_sound('menu')
                        break
                
                # Collapsible section headers
                for rect, action in all_rects.get("buttons", []):
                    if rect.collidepoint(mx, my):
                        if action == "toggle_colors":
                            settings_collapsed["colors"] = not settings_collapsed["colors"]
                        elif action == "toggle_themes":
                            settings_collapsed["themes"] = not settings_collapsed["themes"]
                        elif action == "toggle_shapes":
                            settings_collapsed["shapes"] = not settings_collapsed["shapes"]
                        elif action == "toggle_text_color":
                            settings_collapsed["text_color"] = not settings_collapsed["text_color"]
                        play_sound('menu')
                        break
                
                # Audio sliders
                if "eff_slider" in all_rects and all_rects["eff_slider"].collidepoint(mx, my):
                    dragging = "eff"
                    EFFECT_VOLUME = clamp01((mx - all_rects["eff_slider"].x) / all_rects["eff_slider"].w)
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                    play_sound('menu_select')
                    continue
                
                if "mus_slider" in all_rects and all_rects["mus_slider"].collidepoint(mx, my):
                    dragging = "mus"
                    MUSIC_VOLUME = clamp01((mx - all_rects["mus_slider"].x) / all_rects["mus_slider"].w)
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    play_sound('menu_select')
                    continue
                
                # Music toggle
                if "music_toggle" in all_rects and all_rects["music_toggle"].collidepoint(mx, my):
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
                
                # Color sliders (Appearance tab)
                if "sliders" in all_rects:
                    hit = False
                    for target in ["X", "O", "BG"]:
                        if target in all_rects["sliders"]:
                            for i, (rect, base_x) in enumerate(all_rects["sliders"][target]):
                                if rect.collidepoint(mx, my):
                                    dragging = (target, i)
                                    active_color = target
                                    new_color = update_color_from_mouse(target, i, mx, base_x, rect.w)
                                    set_color(target, new_color)
                                    hit = True
                                    break
                        if hit:
                            break
                    if hit:
                        continue
                
                # Numeric input boxes
                if "inputs" in all_rects:
                    clicked_box = False
                    for target in ["X", "O", "BG"]:
                        if target in all_rects["inputs"]:
                            for i, rect in enumerate(all_rects["inputs"][target]):
                                if rect.collidepoint(mx, my):
                                    selected_input = (target, i)
                                    # Store the original value
                                    if target == "X":
                                        original_input_value = str(int(X_COLOR[i]))
                                    elif target == "O":
                                        original_input_value = str(int(O_COLOR[i]))
                                    else:
                                        original_input_value = str(int(BG_COLOR[i]))
                                    # Clear the input text so box appears blank
                                    input_text = ""
                                    active_color = target
                                    clicked_box = True
                                    break
                                    active_color = target
                                    clicked_box = True
                                    break
                        if clicked_box:
                            break
                    if clicked_box:
                        continue
                
                # Color presets
                if "preset_colors" in all_rects:
                    for rect, col in all_rects["preset_colors"]:
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
                
                # Theme buttons
                if "themes" in all_rects:
                    for rect, theme_name in all_rects["themes"]:
                        if rect.collidepoint(mx, my):
                            theme = THEMES[theme_name]
                            X_COLOR = theme["x_color"]
                            O_COLOR = theme["o_color"]
                            BG_COLOR = theme["bg_color"]
                            TEXT_COLOR = theme["text_color"]
                            LINE_COLOR = theme["line_color"]
                            x_rels = rgb_to_rels(X_COLOR)
                            o_rels = rgb_to_rels(O_COLOR)
                            bg_rels = rgb_to_rels(BG_COLOR)
                            play_sound('menu')
                            break
                
                # Shape tokens
                if "shapes" in all_rects:
                    for tr, player, shape in all_rects["shapes"]:
                        if tr.collidepoint(mx, my):
                            if player == 'X':
                                preview_x_shape = shape
                            else:
                                preview_o_shape = shape
                            play_sound('menu')
                            break
                
                # Board size buttons
                if "size_btns" in all_rects:
                    if all_rects["size_btns"][0].collidepoint(mx, my):
                        pressed_button = 'size3'
                    elif all_rects["size_btns"][1].collidepoint(mx, my):
                        pressed_button = 'size4'
                
                # Text color buttons
                if "text_colors" in all_rects:
                    for rect, col in all_rects["text_colors"]:
                        if rect.collidepoint(mx, my):
                            TEXT_COLOR = col
                            play_sound('menu')
                            break
                
                # Reset Scores
                if "reset_scores" in all_rects and all_rects["reset_scores"].collidepoint(mx, my):
                    pressed_button = 'reset_scores'
                
                # Bottom buttons
                if all_rects["save"].collidepoint(mx, my):
                    pressed_button = 'save'
                elif all_rects["reset"].collidepoint(mx, my):
                    pressed_button = 'reset'
                elif all_rects["back"].collidepoint(mx, my):
                    pressed_button = 'back'

            elif event.type == pygame.MOUSEBUTTONUP:
                mx, my = event.pos
                
                if pressed_button == 'size3' and "size_btns" in all_rects and all_rects["size_btns"][0].collidepoint(mx, my):
                    set_game_size(3); play_sound('menu')
                elif pressed_button == 'size4' and "size_btns" in all_rects and all_rects["size_btns"][1].collidepoint(mx, my):
                    set_game_size(4); play_sound('menu')
                
                if pressed_button == 'save' and all_rects["save"].collidepoint(mx, my):
                    X_SHAPE = preview_x_shape
                    O_SHAPE = preview_o_shape
                    save_settings(); play_sound('menu')
                elif pressed_button == 'reset' and all_rects["reset"].collidepoint(mx, my):
                    X_COLOR = DEFAULT_X_COLOR
                    O_COLOR = DEFAULT_O_COLOR
                    BG_COLOR = DEFAULT_BG_COLOR
                    TEXT_COLOR = DEFAULT_TEXT_COLOR
                    EFFECT_VOLUME = 1.0
                    MUSIC_VOLUME = 1.0
                    x_rels = rgb_to_rels(X_COLOR)
                    o_rels = rgb_to_rels(O_COLOR)
                    bg_rels = rgb_to_rels(BG_COLOR)
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                    play_sound('menu')
                elif pressed_button == 'reset_scores' and "reset_scores" in all_rects and all_rects["reset_scores"].collidepoint(mx, my):
                    # Show confirmation dialog before resetting scores
                    if confirmation_dialog("Reset all scores?"):
                        x_wins = o_wins = draws = 0
                        play_sound('menu')
                    else:
                        play_sound('menu')
                elif pressed_button == 'back' and all_rects["back"].collidepoint(mx, my):
                    play_sound('menu')
                    return
                
                pressed_button = None
                dragging = None

            elif event.type == pygame.MOUSEMOTION:
                mx, my = event.pos
                if dragging == "eff" and "eff_slider" in all_rects:
                    EFFECT_VOLUME = clamp01((mx - all_rects["eff_slider"].x) / all_rects["eff_slider"].w)
                    try:
                        for s in SOUNDS.values():
                            if s: s.set_volume(EFFECT_VOLUME)
                    except Exception:
                        pass
                elif dragging == "mus" and "mus_slider" in all_rects:
                    MUSIC_VOLUME = clamp01((mx - all_rects["mus_slider"].x) / all_rects["mus_slider"].w)
                    try:
                        pygame.mixer.music.set_volume(MUSIC_VOLUME)
                    except Exception:
                        pass
                elif isinstance(dragging, tuple) and "sliders" in all_rects:
                    target, idx = dragging
                    if target in all_rects["sliders"] and idx < len(all_rects["sliders"][target]):
                        rect, base_x = all_rects["sliders"][target][idx]
                        new_color = update_color_from_mouse(target, idx, mx, base_x, rect.w)
                        set_color(target, new_color)

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    continue
                if (pygame.key.get_mods() & pygame.KMOD_CTRL) and event.key == pygame.K_d:
                    DEBUG_DISPLAY_OVERLAY = not DEBUG_DISPLAY_OVERLAY
                    play_sound('menu')
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
                        save_settings()
                        try:
                            force_reinit_display()
                        except Exception:
                            pass
                        return

        clock.tick(60)

# -------------------------
# Play loop & events
# -------------------------
def play_one_game():
    global player, _volume_changed_time, game_mode, move_history, game_start_time, move_count
    
    # ensure board is sized correctly before starting
    try:
        new_board()
    except Exception:
        pass
    
    # Only show the menu if game_mode hasn't been set yet
    if game_mode is None:
        reset_board()
    
    # Reset player to X and clear the board for a fresh game
    player = "X"
    move_history = []
    move_count = 0
    game_start_time = pygame.time.get_ticks()
    for r in range(BOARD_ROWS):
        for c in range(BOARD_COLS):
            board[r][c] = None
    
    # Button dimensions (constant)
    menu_btn_w, menu_btn_h = 180, 45
    new_game_btn_w, new_game_btn_h = 140, 45
    undo_btn_w, undo_btn_h = 120, 45
    btn_gap = 20  # Gap between buttons
    
    while running:
        # always ensure bgm is playing per user's selection 1
        start_bgm(loop=True)
        draw_lines(); draw_figures(); display_scoreboard()
        display_volume_hud_if_needed()
        display_undo_feedback()
        
        # Recalculate button positions every frame (so they stay centered after fullscreen toggle)
        total_btn_width = menu_btn_w + new_game_btn_w + undo_btn_w + (2 * btn_gap)
        start_x = (WIDTH - total_btn_width) // 2
        btn_y = HEIGHT - 70
        
        # Position buttons from left to right
        menu_btn_x = start_x
        back_to_menu_rect = pygame.Rect(menu_btn_x, btn_y, menu_btn_w, menu_btn_h)
        
        new_game_btn_x = menu_btn_x + menu_btn_w + btn_gap
        new_game_rect = pygame.Rect(new_game_btn_x, btn_y, new_game_btn_w, new_game_btn_h)
        
        undo_btn_x = new_game_btn_x + new_game_btn_w + btn_gap
        undo_rect = pygame.Rect(undo_btn_x, btn_y, undo_btn_w, undo_btn_h)
        
        # Draw "Back to Main Menu" button with hover effect
        mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
        pygame.draw.rect(screen, (180,60,60), back_to_menu_rect, border_radius=8)
        # Yellow border on hover
        if back_to_menu_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255,220,40), back_to_menu_rect, 3, border_radius=8)
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
            except Exception:
                pass
        else:
            pygame.draw.rect(screen, (255,255,255), back_to_menu_rect, 2, border_radius=8)
        draw_text_center("Back to Menu", FONT_SMALL, (255,255,255), screen, back_to_menu_rect.centerx, back_to_menu_rect.centery)
        
        # Draw "New Game" button with hover effect
        pygame.draw.rect(screen, (60,180,60), new_game_rect, border_radius=8)
        if new_game_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255,220,40), new_game_rect, 3, border_radius=8)
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
            except Exception:
                pass
        else:
            pygame.draw.rect(screen, (255,255,255), new_game_rect, 2, border_radius=8)
        draw_text_center("New Game", FONT_SMALL, (255,255,255), screen, new_game_rect.centerx, new_game_rect.centery)
        
        # Draw "Undo" button with hover effect
        undo_available = len(move_history) > 0
        undo_color = (80, 120, 180) if undo_available else (60, 60, 60)
        pygame.draw.rect(screen, undo_color, undo_rect, border_radius=8)
        if undo_available and undo_rect.collidepoint(mouse_pos):
            pygame.draw.rect(screen, (255,220,40), undo_rect, 3, border_radius=8)
            try:
                pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
            except Exception:
                pass
        else:
            outline_color = (255,255,255) if undo_available else (100,100,100)
            pygame.draw.rect(screen, outline_color, undo_rect, 2, border_radius=8)
            if not back_to_menu_rect.collidepoint(mouse_pos) and not undo_rect.collidepoint(mouse_pos):
                try:
                    pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
                except Exception:
                    pass
        undo_text_color = (255,255,255) if undo_available else (120,120,120)
        draw_text_center("Undo (Ctrl+Z)", FONT_SMALL, undo_text_color, screen, undo_rect.centerx, undo_rect.centery)
        
        # Draw tooltips for buttons on hover
        mx, my = mouse_pos
        if back_to_menu_rect.collidepoint(mouse_pos):
            draw_tooltip("Return to main menu", mx, my)
        elif new_game_rect.collidepoint(mouse_pos):
            draw_tooltip("Start a fresh game with same mode", mx, my)
        elif undo_rect.collidepoint(mouse_pos):
            if undo_available:
                tooltip_text = "Undo last move (undoes AI move too)" if game_mode in ["AI_EASY", "AI_MEDIUM", "AI_HARD"] else "Undo last move"
                draw_tooltip(tooltip_text, mx, my)
            else:
                draw_tooltip("No moves to undo", mx, my)
        
        present()
        for event in pygame.event.get():
            if event.type == pygame.VIDEORESIZE:
                set_display_mode(event.w, event.h, full=fullscreen)
                draw_lines(); draw_figures(); display_scoreboard(); present()
                continue
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                try:
                    if _SKIP_INPUT_FRAMES > 0:
                        now = pygame.time.get_ticks()
                        if getattr(play_one_game, '_last_skip_dbg_ms', 0) + 500 < now:
                            print(f"[INPUT-BLOCK] play loop skipping mouse (frames={_SKIP_INPUT_FRAMES})")
                            play_one_game._last_skip_dbg_ms = now
                        continue
                except Exception:
                    pass
                mx, my = map_mouse_pos(event.pos)
                
                # Check if "Undo" button was clicked
                if undo_rect.collidepoint(mx, my) and len(move_history) > 0:
                    if undo_last_move():
                        play_sound('menu')
                    continue
                
                # Check if "New Game" button was clicked
                if new_game_rect.collidepoint(mx, my):
                    # Reset the board for a fresh game with the same mode
                    player = "X"
                    move_history = []
                    move_count = 0
                    game_start_time = pygame.time.get_ticks()
                    for r in range(BOARD_ROWS):
                        for c in range(BOARD_COLS):
                            board[r][c] = None
                    play_sound('menu')
                    continue
                
                # Check if "Back to Main Menu" button was clicked
                if back_to_menu_rect.collidepoint(mx, my):
                    game_mode = None
                    save_settings()
                    try:
                        force_reinit_display()
                    except Exception:
                        pass
                    return False
                
                # map to board coords (support variable board size)
                if BOARD_LEFT <= mx < BOARD_LEFT + BOARD_COLS * SQUARE_SIZE and BOARD_TOP <= my < BOARD_TOP + BOARD_ROWS * SQUARE_SIZE:
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
                                draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop(f"Player {player} Wins!")
                            elif is_board_full():
                                handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop("It's a Draw!")
                            else:
                                player = "O" if player == "X" else "X"
                    elif game_mode in ("AI_EASY", "AI_MEDIUM", "AI_HARD"):
                        if available_square(cell_y, cell_x):
                            mark_square(cell_y, cell_x, player)
                            play_sound('move')
                            if check_win("X"):
                                win_cells = get_winning_line("X")
                                draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                                handle_win("X")
                                draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop("Player 1 Wins!")
                            elif is_board_full():
                                handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop("It's a Draw!")
                            # AI turn
                            if game_mode == "AI_EASY":
                                ai_move_easy()
                            elif game_mode == "AI_MEDIUM":
                                ai_move_medium()
                            else:
                                # Show loading indicator for Hard mode
                                if BOARD_ROWS >= 4:
                                    # Draw "AI Thinking..." overlay
                                    overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
                                    overlay.fill((0, 0, 0, 160))
                                    screen.blit(overlay, (0, 0))
                                    
                                    # Draw loading box
                                    box_w, box_h = 300, 100
                                    box_x = WIDTH // 2 - box_w // 2
                                    box_y = HEIGHT // 2 - box_h // 2
                                    box_rect = pygame.Rect(box_x, box_y, box_w, box_h)
                                    pygame.draw.rect(screen, (40, 40, 40), box_rect, border_radius=10)
                                    pygame.draw.rect(screen, (255, 220, 40), box_rect, 3, border_radius=10)
                                    
                                    # Draw text
                                    draw_text_center("AI Thinking...", FONT_LARGE, (255, 220, 40), screen, WIDTH // 2, HEIGHT // 2 - 5)
                                    
                                    # Draw spinner dots (simple animation)
                                    dot_y = HEIGHT // 2 + 25
                                    dot_spacing = 20
                                    dot_start_x = WIDTH // 2 - 30
                                    anim_phase = (pygame.time.get_ticks() // 200) % 4
                                    for i in range(4):
                                        alpha = 255 if i == anim_phase else 100
                                        dot_color = (255, 220, 40, alpha)
                                        dot_surf = pygame.Surface((10, 10), pygame.SRCALPHA)
                                        pygame.draw.circle(dot_surf, dot_color, (5, 5), 5)
                                        screen.blit(dot_surf, (dot_start_x + i * dot_spacing, dot_y))
                                    
                                    present()
                                
                                ai_move_hard()
                            if check_win("O"):
                                win_cells = get_winning_line("O")
                                draw_winning_line(win_cells); draw_pulsing_circles(win_cells)
                                handle_win("O")
                                draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop("Player 2 Wins!")
                            elif is_board_full():
                                handle_draw(); draw_lines(); draw_figures(); display_scoreboard(); present()
                                save_settings(); return end_screen_loop("It's a Draw!")
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_F11:
                    toggle_fullscreen()
                    draw_lines(); draw_figures(); display_scoreboard(); present()
                    continue
                # Ctrl+Z to undo move
                if (pygame.key.get_mods() & pygame.KMOD_CTRL) and event.key == pygame.K_z:
                    if undo_last_move():
                        play_sound('menu')
                        draw_lines(); draw_figures(); display_scoreboard(); present()
                    continue
                # Ctrl+D toggles debug overlay
                if (pygame.key.get_mods() & pygame.KMOD_CTRL) and event.key == pygame.K_d:
                    global DEBUG_DISPLAY_OVERLAY
                    DEBUG_DISPLAY_OVERLAY = not DEBUG_DISPLAY_OVERLAY
                    play_sound('menu')
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
    result = FONT_LARGE.render(message, True, TEXT_COLOR)
    screen.blit(result, (WIDTH//2 - result.get_width()//2, HEIGHT//2 - 120))
    
    # Get mouse position for hover detection
    mouse_pos = map_mouse_pos(pygame.mouse.get_pos())
    hand_cursor = False
    
    # clickable buttons
    restart_rect = pygame.Rect(WIDTH//2 - 220, HEIGHT//2 - 20, 200, 64)
    menu_rect = pygame.Rect(WIDTH//2 + 20, HEIGHT//2 - 20, 200, 64)
    
    # Draw buttons with hover effects
    pygame.draw.rect(screen, (60,180,60), restart_rect, border_radius=8)
    # Yellow border on hover for restart button
    if restart_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (255,220,40), restart_rect, 3, border_radius=8)
        hand_cursor = True
    else:
        pygame.draw.rect(screen, (255,255,255), restart_rect, 2, border_radius=8)
    
    pygame.draw.rect(screen, (180,60,60), menu_rect, border_radius=8)
    # Yellow border on hover for menu button
    if menu_rect.collidepoint(mouse_pos):
        pygame.draw.rect(screen, (255,220,40), menu_rect, 3, border_radius=8)
        hand_cursor = True
    else:
        pygame.draw.rect(screen, (255,255,255), menu_rect, 2, border_radius=8)
    
    draw_text_center("Restart", FONT_MED, (255,255,255), screen, restart_rect.centerx, restart_rect.centery)
    draw_text_center("Menu", FONT_MED, (255,255,255), screen, menu_rect.centerx, menu_rect.centery)
    
    # Set cursor based on hover state
    try:
        if hand_cursor:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_HAND))
        else:
            pygame.mouse.set_cursor(pygame.cursors.Cursor(pygame.SYSTEM_CURSOR_ARROW))
    except Exception:
        # some platforms may not support system cursors; ignore failures
        pass
    
    present()
    return restart_rect, menu_rect

def end_screen_loop(message):
    global game_mode, running
    global DEBUG_DISPLAY_OVERLAY
    clock = pygame.time.Clock()
    while True:
        # Redraw the end screen every frame to show hover effects
        restart_rect, menu_rect = display_end_options(message)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                save_settings(); pygame.quit(); sys.exit()
            if event.type == pygame.MOUSEBUTTONDOWN:
                try:
                    if _SKIP_INPUT_FRAMES > 0:
                        now = pygame.time.get_ticks()
                        if getattr(end_screen_loop, '_last_skip_dbg_ms', 0) + 500 < now:
                            print(f"[INPUT-BLOCK] end_screen_loop skipping mouse (frames={_SKIP_INPUT_FRAMES})")
                            end_screen_loop._last_skip_dbg_ms = now
                        continue
                except Exception:
                    pass
                mx, my = map_mouse_pos(event.pos)
                if restart_rect.collidepoint(mx, my):
                    # Return True to restart the current game mode (board will be cleared in play_one_game)
                    return True
                if menu_rect.collidepoint(mx, my):
                    game_mode = None
                    try:
                        force_reinit_display()
                    except Exception:
                        pass
                    return False
            if event.type == pygame.KEYDOWN:
                if event.key in (pygame.K_MINUS, pygame.K_KP_MINUS):
                    change_volume(-0.05)
                elif event.key in (pygame.K_EQUALS, pygame.K_PLUS, pygame.K_KP_PLUS):
                    change_volume(0.05)
                # Ctrl+D toggles debug overlay
                if (pygame.key.get_mods() & pygame.KMOD_CTRL) and event.key == pygame.K_d:
                    DEBUG_DISPLAY_OVERLAY = not DEBUG_DISPLAY_OVERLAY
                    continue
        
        clock.tick(60)

# -------------------------
# Main
# -------------------------
def main():
    # Initialize pygame subsystems early. Some platforms require calling
    # pygame.init() before initializing the mixer or creating surfaces.
    try:
        pygame.init()
    except Exception:
        pass
    # Try to initialize the mixer; if it fails we'll continue without audio.
    try:
        pygame.mixer.init()
    except Exception as e:
        print(f"[WARN] pygame.mixer.init() failed: {e}; continuing without audio.")

    load_settings()
    init_sounds()
    # Try to initialize a real display mode now that we're running.
    # This may fail in headless/CI environments; fall back to the headless Surface setup.
    global display_initialized
    display_initialized = False
    try:
        try:
            set_display_mode(WIDTH, HEIGHT, full=fullscreen)
            display_initialized = True
        except pygame.error as e:
            print(f"[INFO] pygame display init failed: {e}; running in headless fallback mode.")
            # keep logical_surf as the drawing surface; physical_display remains None
            display_initialized = False
        except Exception as e:
            print(f"[INFO] unexpected error while initializing display: {e}; continuing in headless fallback.")
            display_initialized = False
    except Exception:
        display_initialized = False
    # Perform an immediate atomic startup redraw to avoid a black window on some
    # platforms/compositors. Clear the physical display a few times, render the
    # menu to the logical surface, then manual-blit+flip to the physical display
    # so the user sees the menu immediately.
    try:
        ds_start = pygame.display.get_surface()
        if ds_start is not None:
            try:
                for _ in range(3):
                    ds_start.fill(BG_COLOR)
                    pygame.display.flip()
                    try:
                        pygame.time.delay(20)
                    except Exception:
                        pass
            except Exception:
                pass
        # redraw menu onto logical surface without presenting via present()
        try:
            draw_menu_with_shape_choices(globals().get('X_SHAPE', None), globals().get('O_SHAPE', None), {}, do_present=False)
        except Exception:
            pass
        # attempt direct manual blit to physical display if available
        try:
            if logical_surf is not None and pygame.display.get_surface() is not None:
                try:
                    phys = pygame.display.get_surface()
                    pw, ph = phys.get_size()
                    lw, lh = logical_surf.get_size()
                    scaled = pygame.transform.smoothscale(logical_surf, (pw, ph))
                    phys.blit(scaled, (0, 0))
                    pygame.display.flip()
                except Exception as e:
                    print(f"[STARTUP-INFO] manual startup blit failed: {e}")
        except Exception:
            pass
        try:
            present()
        except Exception:
            pass
        try:
            pygame.time.delay(40)
        except Exception:
            pass
    except Exception:
        pass
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
            # menu_loop is a placeholder; use reset_board() which contains the
            # interactive menu implementation (handles shape pickers and options)
            reset_board()
        restart_same = play_one_game()
        if restart_same:
            continue
        else:
            continue

if __name__ == "__main__":
    main()
