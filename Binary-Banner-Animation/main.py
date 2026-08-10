from PIL import Image, ImageDraw, ImageFont
import random

WIDTH = 1400
HEIGHT = 400
OUTPUT = "teerth_binary_logo.svg"

GRID_SIZE = 10
BINARY_FONT_SIZE = 8
FONT_SIZE = 140

THICKNESS = 0

MAX_SCATTER_DELAY = 2.0

try:
    main_font = ImageFont.truetype("consola.ttf", FONT_SIZE)
except Exception:
    try:
        main_font = ImageFont.truetype("DejaVuSansMono.ttf", FONT_SIZE)
    except Exception:
        main_font = ImageFont.load_default()

mask = Image.new("L", (WIDTH, HEIGHT), 0)
draw = ImageDraw.Draw(mask)

text = "Teerth Sonawani"

bbox = draw.textbbox((0, 0), text, font=main_font)
text_width = bbox[2] - bbox[0]
text_height = bbox[3] - bbox[1]

x_offset = (WIDTH - text_width) // 2
y_offset = (HEIGHT - text_height) // 2 - bbox[1]

draw.text((x_offset, y_offset), text, font=main_font, fill=255)

pixels = []

for py_grid in range(0, HEIGHT, GRID_SIZE):
    for px_grid in range(0, WIDTH, GRID_SIZE):
        found = False

        for yy in range(-THICKNESS, THICKNESS + 1):
            for xx in range(-THICKNESS, THICKNESS + 1):
                px = px_grid + xx
                py = py_grid + yy

                if 0 <= px < WIDTH and 0 <= py < HEIGHT:
                    if mask.getpixel((px, py)) > 0:
                        found = True
                        break
            if found:
                break

        if found:
            pixels.append((px_grid, py_grid))

svg_lines = [
    f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {WIDTH} {HEIGHT}" width="100%" height="100%">',
    '  <style>',
    '    text {',
    '      fill: #00ff41;',
    '      font-family: Consolas, "Courier New", monospace;',
    f'     font-size: {BINARY_FONT_SIZE}px;',
    '      font-weight: bold;',
    '      dominant-baseline: hanging;',
    '      text-anchor: middle;',
    '    }',
    '    g.pixel {',
    '      animation: revealPixel 0.3s cubic-bezier(0.1, 0.9, 0.2, 1) forwards;',
    '    }',
    '    @keyframes revealPixel {',
    '      0% { opacity: 0; transform: scale(0.3); }',
    '      70% { opacity: 1; transform: scale(1.15); }',
    '      100% { opacity: 1; transform: scale(1); }',
    '    }',
    '    @keyframes digA {',
    '      0%, 17%, 43%, 68%, 89% { opacity: 1; }',
    '      18%, 42%, 69%, 88%, 100% { opacity: 0; }',
    '    }',
    '    @keyframes digB {',
    '      0%, 17%, 43%, 68%, 89% { opacity: 0; }',
    '      18%, 42%, 69%, 88%, 100% { opacity: 1; }',
    '    }',
    '  </style>',
    '  <g id="binary-matrix">'
]

random.shuffle(pixels)

for px, py in pixels:
    reveal_delay = round(random.uniform(0.05, MAX_SCATTER_DELAY), 3)

    flicker_duration = round(random.uniform(0.7, 2.4), 2)
    flicker_offset = round(random.uniform(0.0, 3.0), 2)

    style_a = f'animation: digA {flicker_duration}s step-end infinite -{flicker_offset}s;'
    style_b = f'animation: digB {flicker_duration}s step-end infinite -{flicker_offset}s;'

    cx = px + (GRID_SIZE // 2)

    svg_lines.append(
        f'    <g class="pixel" style="animation-delay: {reveal_delay}s;">'
        f'<text x="{cx}" y="{py}" style="{style_a}">0</text>'
        f'<text x="{cx}" y="{py}" style="{style_b}">1</text>'
        f'</g>'
    )

svg_lines.append('  </g>')
svg_lines.append('</svg>')

with open(OUTPUT, "w", encoding="utf-8") as f:
    f.write("\n".join(svg_lines))

print("IT HAS BEEN GENERATED!:", OUTPUT)
