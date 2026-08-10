# Binary Name Logo Generator

Generates an animated SVG banner that spells out a name using a scattered grid of binary digits (`0`/`1`). Each digit flickers independently, and the full name assembles itself on load via a staggered reveal animation.

## How it works

1. Renders the target text to an off-screen mask using a monospace font, to get the exact pixel shape of the letters.
2. Lays a grid over the canvas and keeps only the grid cells that fall inside the letter shapes.
3. For each kept cell, writes a `<text>` pair (a `0` and a `1`) with:
   - A random entrance delay, so the name scatters into place instead of popping in all at once.
   - A random flicker duration/offset, so digits toggle between `0` and `1` asynchronously rather than in sync.
4. Writes everything out as a single `.svg` file.

## Requirements

- Python 3
- [Pillow](https://pypi.org/project/Pillow/)

```bash
pip install Pillow
```

A monospace font is used for measuring letter shapes (`consola.ttf`, falling back to `DejaVuSansMono.ttf`, then Pillow's default font if neither is found). Font availability affects render quality but the script won't crash without one.

## Usage

```bash
python teerth_binary_logo.py
```

This produces `teerth_binary_logo.svg` in the working directory.

## Customization

All settings live at the top of the script:

| Variable | Description |
|---|---|
| `WIDTH`, `HEIGHT` | Canvas size in pixels |
| `OUTPUT` | Output file name |
| `GRID_SIZE` | Spacing between binary digits |
| `BINARY_FONT_SIZE` | Font size of each `0`/`1` character |
| `FONT_SIZE` | Font size of the underlying name text used to build the letter mask |
| `THICKNESS` | Sampling radius per grid cell (`0` = exact outline, higher = bolder/thicker fill) |
| `MAX_SCATTER_DELAY` | Max delay (seconds) before the last digit appears during entrance |

To change the name displayed, edit the `text` variable in the script.

## Output

The result is a self-contained SVG with inline CSS animations — no JavaScript required. It can be embedded directly in a GitHub README via:

```markdown
<img src="path/to/teerth_binary_logo.svg" width="900"/>
```
