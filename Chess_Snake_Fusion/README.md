# 🐍 Chess with a Hungry Snake

A twist on classic chess: a hungry, growing snake lives on the board and will eat *any* piece — yours or your opponent's — that it can path its way to. Outmaneuver your opponent **and** the snake to deliver checkmate.

![Python](https://img.shields.io/badge/python-3.8%2B-blue)
![Pygame](https://img.shields.io/badge/pygame-2.x-green)
![License](https://img.shields.io/badge/license-MIT-lightgrey)

---

## 🎮 Overview

This is standard chess played on an 8×8 board — with one major complication: a snake slithers around the board, hunting down pieces and devouring them. Every few turns it grows faster and hungrier, and the only way to slow it down is to strike its head or feed it bait. Checkmate still wins the game, but you'll need to manage the snake as carefully as you manage your position.

## ✨ Features

- **Full chess rules** — legal move generation, check/checkmate/stalemate detection, castling (kingside & queenside), en passant, and pawn promotion (Queen, Rook, Bishop, Knight).
- **A living, hunting snake**
  - Uses breadth-first search to path toward its current target and always takes the shortest route.
  - **Eats any piece** (white or black, except kings) that it reaches — permanently removing it from play.
  - **Grows by one segment** every time it eats, and its body blocks movement for both sides.
  - Retargets automatically when its current target dies or becomes unreachable, and prefers to keep attacking the side it just fed on.
- **Escalating difficulty** — the snake speeds up over time, moving multiple squares per player turn as the game goes on (three speed tiers).
- **Fight back** — instead of moving a piece, you can attack the snake's head directly with any piece that can legally reach it, stunning it for several turns.
- **Bait system** — every 5 turns, each side without one receives a piece of bait. Place it on an empty square to lure the snake away from your pieces and buy yourself time.
- **Animated movement** — the snake steps square-by-square with a short delay so you can watch it hunt in real time, instead of teleporting to its destination.
- **Graceful fallback rendering** — if custom sprite assets aren't found, the game automatically falls back to hand-drawn circles/shapes and Unicode chess glyphs, so it always runs.

## 🕹️ How to Play

| Action | How |
|---|---|
| Select a piece | Click on one of your pieces |
| Move it | Click a highlighted destination square |
| Attack the snake | Click the snake's head when it's highlighted as a legal move |
| Place bait | Click your bait badge (bottom corner), then click an empty square |
| Promote a pawn | Click your chosen piece in the promotion popup |

### Board Highlights

| Color | Meaning |
|---|---|
| 🟩 Green outline | Currently selected piece |
| ⬜ Gray tile | Regular legal move |
| 🟥 Red tile | Capturing an enemy piece |
| 🟠 Orange tile | Attacking the snake's head |
| 🔵 Cyan tile | Moving onto the bait |
| 🟡 Gold ring | King in check |
| 🩷 Magenta ring | The snake's current target |

## 🐍 Snake Behavior

- The snake targets one color at a time, choosing a random reachable non-king piece to hunt.
- If it can't reach any piece of its current target color, it switches sides — unless it just ate, in which case it stays locked onto that color for its next move.
- **Stunning:** Any piece that legally attacks the snake's head stuns it for 6 half-moves (roughly 3 full turns), during which it can't move but also can't be harmed further.
- **Bait:** Placed bait becomes the snake's top priority target, overriding whatever piece it was chasing.
- **Speed tiers:** The snake starts at normal speed and speeds up at set turn thresholds, taking multiple steps per player turn later in the game.

## ⚙️ Setup

### Requirements

- Python 3.8+
- [Pygame](https://www.pygame.org/)

```bash
pip install pygame
```

### Run

```bash
python main.py
```

### Custom Assets (optional)

The game looks for artwork in two possible locations, in this order:

1. `assets/<path>` — an `assets/` subfolder next to the script
2. `<path>` — the folders placed directly next to the script (no `assets/` wrapper)

Whichever is found first wins, so you can organize assets either way. If a file isn't found in either location, the game falls back to built-in placeholder graphics — nothing is required to run the game.

```
(either directly next to main.py, or nested one level under assets/)

board/
├── light.png
├── dark.png
└── background.png
pieces/
├── wP.png, wN.png, wB.png, wR.png, wQ.png, wK.png
└── bP.png, bN.png, bB.png, bR.png, bQ.png, bK.png
bait/
└── bait.png
snake/          (tier 1 — base speed)
snake_1/        (tier 2 — medium speed)
snake_2/        (tier 3 — fast)
```

Each snake tier folder can contain directional head/body/tail segments (e.g. `head_up.png`, `body_horizontal.png`, `tail_left.png`, stunned variants, and `apple.png` for bait). Any missing file automatically falls back to the previous tier's art, then to the generic snake sprites, then to simple shapes.

## 🏆 Winning

- **Checkmate** the opposing king — standard chess win condition.
- **Stalemate** results in a draw.
- If the **snake eats a king**, the *other* side wins by default.
- Capturing the enemy king directly (if somehow left exposed) is also a win.

## 🛠️ Tech Notes

- Built with `pygame` for rendering and input, and Python's `collections.deque` for BFS pathfinding.
- Chess logic (move generation, check detection, castling, en passant) is implemented from scratch — no external chess engine.
- Snake pathfinding treats both kings and its own body as obstacles, and recalculates its route every step.

---

Enjoy — and don't forget to watch your flank. The snake doesn't care whose piece it eats. 🐍♟️
