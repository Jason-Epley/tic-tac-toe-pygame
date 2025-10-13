# tic-tac-toe-pygame
Tic-Tac-Toe in Python/Pygame 🎮

Overview

  This is a customized version of Tic-Tac-Toe built in Python with Pygame. Unlike a standard tutorial version, this project includes:
  
  A graphical interface with custom design elements
  
  Player vs Player and Player vs AI modes
  
  Two AI difficulty levels (Easy = random, Hard = Minimax)
  
  Scoreboard and replay system
  
  Sound effects and simple animations
  
  Player name and symbol customization
  
  The game is designed as part of my NCLab Python Capstone Project and demonstrates problem solving, design decisions, and original enhancements beyond the basics.

Features

  🖥️ GUI Board with colors and symbols
  
  🤖 AI Opponent: choose Easy or Hard mode
  
  🎵 Sound Effects for moves and wins
  
  🏆 Scoreboard to track wins, losses, draws
  
  🔄 Replay Option without restarting
  
  🎨 Custom Symbols/Names for players

Installation Requirements

  Python 3.9+
  
  Pygame library

Setup

  Clone this repository:
  
  git clone https://github.com/Jason-Epley/tic-tac-toe-pygame.git
  cd tic-tac-toe-pygame


Install pygame:

  pip install pygame


Run the game:

  python main.py

How to Play

  Launch the game.
  
  Choose Player vs Player or Player vs AI mode.
  
  If AI mode, select Easy or Hard.
  
  Click an empty square to make your move.
  
  First to 3 in a row (horizontal, vertical, or diagonal) wins.
  
  Use the replay option to play again.

Screenshots attached.
![image alt](https://github.com/Jason-Epley/tic-tac-toe-pygame/blob/main/tic_tac_toe_pygame_img_3.PNG)
![image alt](https://github.com/Jason-Epley/tic-tac-toe-pygame/blob/main/tic_tac_toe_pygame_img_2.PNG)
![image alt](https://github.com/Jason-Epley/tic-tac-toe-pygame/blob/main/tic_tac_toe_pygame_img_1.PNG)

Project Structure
  tic-tac-toe-pygame/
  │── main.py          # Entry point
  │── game.py          # Core game logic
  │── ai.py            # AI logic (random + minimax)
  │── ui.py            # Pygame rendering and input
  │── assets/          # Images, sounds, fonts
  │── README.md        # Documentation

Future Improvements

  Support for larger board sizes (4x4, 5x5)
  
  Theming system (dark/light mode)
  
  Credits
  
  Developed by Jason Epley as part of NCLab Python Capstone
  
  Built with Python + Pygame


Development Roadmap for Tic-Tac-Toe (Pygame)
Phase 1 – Setup & Core Game

  ✅ Install Python 3.9+ and Pygame.
  
  ✅ Create GitHub repo + set up main.py (skeleton we wrote).
  
  ✅ Draw board lines using Pygame.
  
  ✅ Allow players to place X and O on clicks.
  
  ✅ Alternate turns (done in skeleton).
  
  Add win detection logic (check rows, columns, diagonals).
  
  Display game over message (temporary text in console or on screen).

Phase 2 – Polish Base Game

  Reset board when a game ends (new round without restarting).
  
  Add a scoreboard to track wins, losses, draws.
  
  Create a simple menu screen:
  
  Choose Player vs Player or Player vs AI.
  
  Choose player names/symbols.

Phase 3 – AI Opponent

  Implement Easy AI (random move).
  
  Implement Hard AI (Minimax algorithm for unbeatable AI).
  
  Add option in menu to pick Easy/Hard AI.

Phase 4 – User Experience Enhancements

  Add colors/graphics customization (different X/O styles, themes).
  
  Highlight the winning line when someone wins.
  
  Add sound effects (move sound, win sound).
  
  Smooth animations (e.g., fade-in moves, line draw).

Phase 5 – Final Touches

  Add replay button (instead of restart).
  
  Update README.md with screenshots and instructions.
  
  Record presentation demo.
  
  Push final version to GitHub with tags/releases.


Credits
⦁	"Background Music" bgm.ogg = chill background music #2.wav by ZHRØ -- https://freesound.org/s/703713/ -- License: Attribution 4.0
⦁	"Menu click" menu_select.wav = Click - Wooden 2 by GameAudio -- https://freesound.org/s/220196/ -- License: Creative Commons 0
⦁	"Lose sound" lose.wav = Jingle_Lose_01.wav by LittleRobotSoundFactory -- https://freesound.org/s/270334/ -- License: Attribution 4.0
⦁	"Draw sound" draw.wav = Retro You Lose SFX  by suntemple -- https://freesound.org/s/253174/ -- License: Creative Commons 0
⦁	"Win sound" win.wav = Electro success sound by Unlistenable -- https://freesound.org/s/391540/ -- License: Attribution NonCommercial 4.0
⦁	"AI move sound" move_ai.wav = Electro success sound by Unlistenable -- https://freesound.org/s/391540/ -- License: Attribution NonCommercial 4.0
⦁	"Move sound" move.wav = Click_1.wav by JonnyRuss01 -- https://freesound.org/s/478197/ -- License: Creative Commons 0
