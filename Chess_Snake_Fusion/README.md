# Chess with a Hungry Snake ♟️🐍

A full game of chess... except there's a snake loose on the board, and it's hunting your pieces.

Built with Python and Pygame. Every standard chess rule is implemented — castling, en passant, pawn promotion, check, checkmate, stalemate — but the snake is a living hazard that both players have to react to, work around, and occasionally fight back against.

## How It Works

### The Snake

- The snake starts as a 3-segment body in the middle of the board and is **not aligned to either player** — it picks a side to hunt and goes after that side's pieces.
- Each turn, the snake picks a target piece (of whichever color it's currently hunting) that it can actually path to, and moves one step closer to it using pathfinding across empty squares. It cannot pass through its own body or through a King's square.
- If the snake reaches a piece, **it eats it** — the piece is removed from the board, just like a capture.
- **If the snake eats a King, that side loses immediately.** The other player wins by default, even mid-game with no checkmate involved.
- After eating a piece, there's a 50% chance the snake switches its hunt to the *other* color next.
- The snake **speeds up** the longer the game goes on — it moves multiple squares per turn instead of one, based on how many full rounds have been played:
  - Turns 0–29: normal speed (1 square/turn)
  - Turns 30–59: fast (2 squares/turn)
  - Turns 60+: very fast (3 squares/turn)

### Fighting Back: Attacking the Snake

- The snake's head is a legal move target for your pieces, exactly like a normal capture square. If one of your pieces can legally reach the snake's head, you can move onto it to strike the snake.
- A successful strike **stuns the snake for 3 of your turns** (6 half-moves). While stunned, the snake doesn't move.
- Striking the snake also has a 50% chance of making it switch which color it's hunting.
- You can't strike an already-stunned snake — it just shrugs it off.

### Bait

- Every 5 turns, any side that doesn't currently hold a bait token automatically receives one (shown as a badge on the bottom corner of the board matching your color).
- If you have a bait token, you can click your badge to enter **bait placement mode**, then click any empty square (not occupied by a piece or the snake) to drop bait there. This uses your turn.
- Once bait is on the board, the snake will beeline for it over any piece — a way to lure it away from your King or a piece it's stalking.
- You can't place bait while your King is in check.

### Standard Chess Rules (Still Fully in Play)

All of this happens on top of normal chess:
- Legal moves for every piece type, including check detection (the snake's body and head count as obstacles/threats when calculating legality).
- **Castling** (kingside and queenside), with the usual conditions — King and Rook haven't moved, squares between them are clear (of pieces *and* the snake), and the King doesn't pass through check.
- **En passant** capture.
- **Pawn promotion** — reaching the back rank opens a selection prompt for Queen, Rook, Bishop, or Knight.
- **Checkmate** and **stalemate** detection, accounting for the snake occupying or threatening squares.
- Standard win by capturing the enemy King directly, on top of the snake-related win condition above.

## Controls

Mouse only:

| Action | How |
|---|---|
| Select a piece | Click on one of your pieces |
| Move / capture | Click a highlighted legal square |
| Attack the snake | Click the snake's head when it's a highlighted legal move |
| Enter bait mode | Click your bait badge (bottom-left for White, bottom-right for Black) |
| Place bait | While in bait mode, click any empty square |
| Cancel bait mode | Click your badge again |
| Promote a pawn | Click your chosen piece in the promotion popup |

**Highlight colors:**
- Green outline — selected piece
- Gray — normal move
- Red — capture
- Orange — attacking the snake's head
- Cyan — moving onto bait
- Yellow — legal bait-drop squares (while in bait mode)
- Red ring around King — King is in check

## Requirements

- Python 3.x
- [Pygame](https://www.pygame.org/)

Install the dependency:

```bash
pip install pygame
```

Run the game:

```bash
python Chess_Snake_Fusion.py
```

(Use whatever the actual filename is in this folder.)

## Assets

The game looks for artwork in an `assets/` folder next to the script, but **it doesn't require it** — anything missing falls back to simple drawn shapes and Unicode chess glyphs, so it runs out of the box.

If you want to add your own art, the expected structure is:

```
assets/
├── pieces/
│   ├── wP.png, wN.png, wB.png, wR.png, wQ.png, wK.png
│   └── bP.png, bN.png, bB.png, bR.png, bQ.png, bK.png
├── board/
│   ├── light.png
│   ├── dark.png
│   └── background.png
├── bait/
│   └── bait.png
├── snake/          # base speed tier
├── snake_1/         # tier unlocked at turn 30
├── snake_2/         # tier unlocked at turn 60
└── (each snake_* folder can contain: head_up/down/left/right.png,
     head_*_stunned.png, body_horizontal/vertical.png,
     body_topleft/topright/bottomleft/bottomright.png,
     tail_up/down/left/right.png, apple.png)
```

Each snake tier can have its own look — useful for visually signaling that the snake has sped up.

## Credits

Created by **Teerth Sonawani**.

## License

This project is licensed under **CC BY-ND 4.0** — you're free to share it as-is with credit, but you may not modify/remix it and redistribute your own version. See [`LICENSE`](./LICENSE) for the full terms.
