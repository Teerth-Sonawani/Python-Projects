 
import pygame
import random
import sys
import os
from collections import deque

# --- Setup ---
pygame.init()

BOARD_SIZE = 8
SQ = 80
BOARD_PX = BOARD_SIZE * SQ
STATUS_H = 92
WIDTH = BOARD_PX
HEIGHT = BOARD_PX + STATUS_H

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Chess x Snake Fusion")
clock = pygame.time.Clock()

# Colors (I just copy-pasted these from a color picker, don't judge)
LT = (240, 217, 181)
DK = (181, 136, 99)
SELC = (106, 168, 79)
MVD = (60, 60, 60)
CAPR = (200, 40, 40)
ATKR = (255, 140, 0)
BAITATK = (80, 220, 255)
SHC = (30, 140, 30)
SBC = (60, 190, 60)
SFC = (120, 190, 230)
SEC = (0, 0, 0)
SBG = (25, 25, 25)
TC = (255, 255, 255)
DTC = (170, 170, 170)
GOBG = (0, 0, 0, 180)
BTC = (220, 60, 60)
BTR = (255, 220, 120)
TBG = (60, 45, 10, 230)
TTX = (255, 215, 120)
STF = (255, 215, 0)
BADGE_RING = (255, 215, 0)
BADGE_WHITE_BG = (255, 255, 255)
BADGE_BLACK_BG = (25, 25, 25)
TARGET_HL = (255, 0, 220)

# highlight fill colors (RGBA)
HILITE_MOVE      = (70,  70,  70,  95)
HILITE_CAPTURE   = (205, 40,  40, 120)
HILITE_SNAKE_ATK = (255, 140,  0, 130)
HILITE_BAIT_HIT  = (80, 220, 255, 130)
HILITE_SELECTED  = (106, 168, 79, 90)
HILITE_BAITSPOT  = (250, 210, 90, 70)
HILITE_PROMO_BG  = (18, 18, 24, 235)

STUN_HALF_MOVES = 6
STEP_DELAY_MS = 160

WHITE_GLYPH = {'P': '\u2659', 'N': '\u2658', 'B': '\u2657', 'R': '\u2656', 'Q': '\u2655', 'K': '\u2654'}
BLACK_GLYPH = {'P': '\u265F', 'N': '\u265E', 'B': '\u265D', 'R': '\u265C', 'Q': '\u265B', 'K': '\u265A'}

# Fonts - hope these exist on the user's system (im cooked)
pf = pygame.font.SysFont(['segoeuisymbol', 'dejavusans', 'arialunicodems', 'notosanssymbols2', None], 56)
sf = pygame.font.SysFont(['segoeui', 'arial', None], 22)
smf = pygame.font.SysFont(['segoeui', 'arial', None], 18)
bf = pygame.font.SysFont(['segoeui', 'arial', None], 46)
tf = pygame.font.SysFont(['segoeui', 'arial', None], 24)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_DIR_CANDIDATES = [os.path.join(SCRIPT_DIR, 'assets'), SCRIPT_DIR]

def loadimg(pth, sz):
    for base in ASSET_DIR_CANDIDATES:
        fpp = os.path.join(base, pth)
        if os.path.isfile(fpp):
            try:
                imz = pygame.image.load(fpp).convert_alpha()
                return pygame.transform.smoothscale(imz, sz)
            except pygame.error:
                continue
    return None

#Image stuff
PIECE_IMAGES = {}
for _color in ('w', 'b'):
    for _kind in ('P', 'N', 'B', 'R', 'Q', 'K'):
        PIECE_IMAGES[(_color, _kind)] = loadimg(f'pieces/{_color}{_kind}.png', (SQ, SQ))

SNAKE_HEAD_IMG = loadimg('snake/head.png', (SQ, SQ))
SNAKE_BODY_IMG = loadimg('snake/body.png', (SQ, SQ))
SNAKE_FROZEN_IMG = loadimg('snake/head_frozen.png', (SQ, SQ))
BOARD_LIGHT_IMG = loadimg('board/light.png', (SQ, SQ))
BOARD_DARK_IMG = loadimg('board/dark.png', (SQ, SQ))
BACKGROUND_IMG = loadimg('board/background.png', (WIDTH, HEIGHT))
BAIT_IMG = loadimg('bait/bait.png', (SQ, SQ))

SNAKE_TIERS = [
    {'dir': 'snake', 'speed': 1, 'turn_threshold': 0},
    {'dir': 'snake_1', 'speed': 2, 'turn_threshold': 30},
    {'dir': 'snake_2', 'speed': 3, 'turn_threshold': 60},
]

SNAKE_ASSET_KEYS = [
    'head_up', 'head_down', 'head_left', 'head_right',
    'head_up_stunned', 'head_down_stunned', 'head_left_stunned', 'head_right_stunned',
    'body_horizontal', 'body_vertical',
    'body_topleft', 'body_topright', 'body_bottomleft', 'body_bottomright',
    'tail_up', 'tail_down', 'tail_left', 'tail_right',
    'apple',
]

def loadtiers():
    #Messy logic but i cba
    base_fallback = {
        'head_up': SNAKE_HEAD_IMG, 'head_down': SNAKE_HEAD_IMG,
        'head_left': SNAKE_HEAD_IMG, 'head_right': SNAKE_HEAD_IMG,
        'head_up_stunned': SNAKE_FROZEN_IMG, 'head_down_stunned': SNAKE_FROZEN_IMG,
        'head_left_stunned': SNAKE_FROZEN_IMG, 'head_right_stunned': SNAKE_FROZEN_IMG,
        'body_horizontal': SNAKE_BODY_IMG, 'body_vertical': SNAKE_BODY_IMG,
        'body_topleft': SNAKE_BODY_IMG, 'body_topright': SNAKE_BODY_IMG,
        'body_bottomleft': SNAKE_BODY_IMG, 'body_bottomright': SNAKE_BODY_IMG,
        'tail_up': SNAKE_BODY_IMG, 'tail_down': SNAKE_BODY_IMG,
        'tail_left': SNAKE_BODY_IMG, 'tail_right': SNAKE_BODY_IMG,
        'apple': BAIT_IMG,
    }
    tiers = []
    prev = dict(base_fallback)
    for tinfo in SNAKE_TIERS:
        cur = {}
        for key in SNAKE_ASSET_KEYS:
            img = loadimg(f"{tinfo['dir']}/{key}.png", (SQ, SQ))
            if img is None and key.endswith('_stunned'):
                img = loadimg(f"{tinfo['dir']}/{key[:-8]}.png", (SQ, SQ))
            if img is None:
                img = prev.get(key)
            cur[key] = img
        tiers.append(cur)
        prev = {k: (v if v is not None else prev.get(k)) for k, v in cur.items()}
    return tiers

SNAKE_ASSETS = loadtiers()
APPLE_BADGE_IMG = SNAKE_ASSETS[0].get('apple') or BAIT_IMG

def get_tier_idx(turn_count):
    idx = 0
    for i, tinfo in enumerate(SNAKE_TIERS):
        if turn_count >= tinfo['turn_threshold']:
            idx = i
    return idx

def get_speed(turn_count):
    return SNAKE_TIERS[get_tier_idx(turn_count)]['speed']

def get_axis(dr, dc):
    if dr < 0: return 'up'
    if dr > 0: return 'down'
    if dc < 0: return 'left'
    return 'right'

def get_seg_key(body, i, stunned_head=False):
    seg = body[i]
    n = len(body)
    if i == 0:
        if n > 1:
            nxt = body[1]
            dr, dc = seg[0] - nxt[0], seg[1] - nxt[1]
        else:
            dr, dc = 0, 1
        d = get_axis(dr, dc)
        return f'head_{d}_stunned' if stunned_head else f'head_{d}'
    if i == n - 1:
        p = body[i - 1]
        dr, dc = seg[0] - p[0], seg[1] - p[1]
        return f'tail_{get_axis(dr, dc)}'
    
    p = body[i - 1]
    nx = body[i + 1]
    pdr, pdc = p[0] - seg[0], p[1] - seg[1]
    ndr, ndc = nx[0] - seg[0], nx[1] - seg[1]
    dirs = {get_axis(pdr, pdc), get_axis(ndr, ndc)}
    
    if dirs == {'up', 'down'}: return 'body_vertical'
    if dirs == {'left', 'right'}: return 'body_horizontal'
    if dirs == {'up', 'left'}: return 'body_topleft'
    if dirs == {'up', 'right'}: return 'body_topright'
    if dirs == {'down', 'left'}: return 'body_bottomleft'
    if dirs == {'down', 'right'}: return 'body_bottomright'
    return 'body_horizontal'

# --- Chess Logic ---
def create_piece(sideColor, pieceKind, r, c):
      return {'color': sideColor, 'kind': pieceKind, 'row': r, 'col': c, 'alive': True}

def setup_board():
    grid = [[None for _ in range(8)] for _ in range(8)]
    backRank = ['R', 'N', 'B', 'Q', 'K', 'B', 'N', 'R']
    for col in range(8):
        grid[0][col] = create_piece('b', backRank[col], 0, col)
        grid[1][col] = create_piece('b', 'P', 1, col)
        grid[6][col] = create_piece('w', 'P', 6, col)
        grid[7][col] = create_piece('w', backRank[col], 7, col)
    return grid

def get_pieces(grid):
    found = []
    for r in range(8):
      for c in range(8):
        if grid[r][c] is not None:
            found.append(grid[r][c])
    return found

def is_on_board(r, c):
    return 0 <= r < 8 and 0 <= c < 8

def crawl_ray(grid, r0, c0, side, rayDirs, snakeCells, snakeHeadSq):
    results = []
    for stepR, stepC in rayDirs:
        pr, pc = r0 + stepR, c0 + stepC
        while is_on_board(pr, pc):
            if (pr, pc) in snakeCells:
                break
            if (pr, pc) == snakeHeadSq:
                results.append((pr, pc))
                break
            occupant = grid[pr][pc]
            if occupant is None:
                results.append((pr, pc))
            else:
                if occupant['color'] != side:
                    results.append((pr, pc))
                break
            pr += stepR
            pc += stepC
    return results

def rawmoves(grid, r, c, snakeBody, snakeHead, baitSquare=None, ctx=None):
    piece = grid[r][c]
    if piece is None:
        return []
    side, kind = piece['color'], piece['kind']
    moves = []

    if kind == 'P':
        step = -1 if side == 'w' else 1
        homeRow = 6 if side == 'w' else 1
        fr = r + step
        if is_on_board(fr, c) and grid[fr][c] is None and (fr, c) not in snakeBody and (fr, c) != snakeHead:
            moves.append((fr, c))
            fr2 = r + 2 * step
            if r == homeRow and grid[fr2][c] is None and (fr2, c) not in snakeBody and (fr2, c) != snakeHead:
                moves.append((fr2, c))
        for dc in (-1, 1):
            fr, fc = r + step, c + dc
            if not is_on_board(fr, fc): continue
            if (fr, fc) == snakeHead:
                moves.append((fr, fc))
            elif (fr, fc) not in snakeBody and grid[fr][fc] is not None and grid[fr][fc]['color'] != side:
                moves.append((fr, fc))
            elif (fr, fc) not in snakeBody and baitSquare is not None and (fr, fc) == baitSquare:
                moves.append((fr, fc))
            elif ctx is not None and ctx.get('ep_target') == (fr, fc) and (fr, fc) not in snakeBody \
                    and grid[fr][fc] is None and grid[r][fc] is not None \
                    and grid[r][fc]['kind'] == 'P' and grid[r][fc]['color'] != side:
                moves.append((fr, fc))

    elif kind == 'N':
        hops = [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]
        for dr, dc in hops:
            fr, fc = r + dr, c + dc
            if not is_on_board(fr, fc) or (fr, fc) in snakeBody: continue
            if (fr, fc) == snakeHead or grid[fr][fc] is None or grid[fr][fc]['color'] != side:
                moves.append((fr, fc))

    elif kind == 'B':
        moves = crawl_ray(grid, r, c, side, [(-1, -1), (-1, 1), (1, -1), (1, 1)], snakeBody, snakeHead)

    elif kind == 'R':
        moves = crawl_ray(grid, r, c, side, [(-1, 0), (1, 0), (0, -1), (0, 1)], snakeBody, snakeHead)

    elif kind == 'Q':
        moves = crawl_ray(grid, r, c, side,
                          [(-1, -1), (-1, 1), (1, -1), (1, 1), (-1, 0), (1, 0), (0, -1), (0, 1)],
                          snakeBody, snakeHead)

    elif kind == 'K':
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0: continue
                fr, fc = r + dr, c + dc
                if not is_on_board(fr, fc) or (fr, fc) in snakeBody: continue
                if (fr, fc) == snakeHead or grid[fr][fc] is None or grid[fr][fc]['color'] != side:
                    moves.append((fr, fc))

        if ctx is not None:
            homeRow = 7 if side == 'w' else 0
            enemy = 'b' if side == 'w' else 'w'
            if r == homeRow and c == 4 and not ctx['king_moved'][side]:
                # -- kingside --
                if not ctx['rook_moved'][side][7]:
                    rookPc = grid[homeRow][7]
                    if rookPc is not None and rookPc['kind'] == 'R' and rookPc['color'] == side and rookPc['alive']:
                        gap = [(homeRow, 5), (homeRow, 6)]
                        clearGap = all(grid[gr][gc] is None and (gr, gc) not in snakeBody and (gr, gc) != snakeHead
                                       for gr, gc in gap)
                        if clearGap:
                            safePath = not any(is_threatened(grid, hr, hc, enemy, snakeBody)
                                                for hr, hc in [(homeRow, 4), (homeRow, 5), (homeRow, 6)])
                            if safePath: moves.append((homeRow, 6))

                # -- queenside --
                if not ctx['rook_moved'][side][0]:
                    rookPc = grid[homeRow][0]
                    if rookPc is not None and rookPc['kind'] == 'R' and rookPc['color'] == side and rookPc['alive']:
                        gap = [(homeRow, 1), (homeRow, 2), (homeRow, 3)]
                        clearGap = all(grid[gr][gc] is None and (gr, gc) not in snakeBody and (gr, gc) != snakeHead
                                       for gr, gc in gap)
                        if clearGap:
                            safePath = not any(is_threatened(grid, hr, hc, enemy, snakeBody)
                                                for hr, hc in [(homeRow, 4), (homeRow, 3), (homeRow, 2)])
                            if safePath: moves.append((homeRow, 2))
    return moves

def coveredBy(grid, r, c, snakeBody):
    p = grid[r][c]
    if p is None: return set()
    side, kind = p['color'], p['kind']
    hitset = set()
    if kind == 'P':
        step = -1 if side == 'w' else 1
        for dc in (-1, 1):
            fr, fc = r + step, c + dc
            if is_on_board(fr, fc) and (fr, fc) not in snakeBody: hitset.add((fr, fc))
    elif kind == 'N':
        for dr, dc in [(-2, -1), (-2, 1), (-1, -2), (-1, 2), (1, -2), (1, 2), (2, -1), (2, 1)]:
            fr, fc = r + dr, c + dc
            if is_on_board(fr, fc) and (fr, fc) not in snakeBody: hitset.add((fr, fc))
    elif kind == 'K':
        for dr in (-1, 0, 1):
            for dc in (-1, 0, 1):
                if dr == 0 and dc == 0: continue
                fr, fc = r + dr, c + dc
                if is_on_board(fr, fc) and (fr, fc) not in snakeBody: hitset.add((fr, fc))
    else:
        dirs = []
        if kind in ('B', 'Q'): dirs += [(-1, -1), (-1, 1), (1, -1), (1, 1)]
        if kind in ('R', 'Q'): dirs += [(-1, 0), (1, 0), (0, -1), (0, 1)]
        for dr, dc in dirs:
            fr, fc = r + dr, c + dc
            while is_on_board(fr, fc):
                if (fr, fc) in snakeBody: break
                hitset.add((fr, fc))
                if grid[fr][fc] is not None: break
                fr += dr
                fc += dc
    return hitset

def is_threatened(grid, r, c, byColor, snakeBody):
    for p in get_pieces(grid):
        if p['alive'] and p['color'] == byColor and (r, c) in coveredBy(grid, p['row'], p['col'], snakeBody):
            return True
    return False

def get_king_sq(grid, side):
    for p in get_pieces(grid):
        if p['alive'] and p['kind'] == 'K' and p['color'] == side:
            return (p['row'], p['col'])
    return None

def in_check(grid, side, snakeBody):
    kSq = get_king_sq(grid, side)
    if kSq is None: return False
    foe = 'b' if side == 'w' else 'w'
    return is_threatened(grid, kSq[0], kSq[1], foe, snakeBody)

def bleh(grid, fromSq, toSq, side, snakeBody):
    ghost = [row[:] for row in grid]
    fr, fc = fromSq
    tr, tc = toSq
    mover = dict(ghost[fr][fc])
    mover['row'], mover['col'] = tr, tc
    ghost[fr][fc] = None
    ghost[tr][tc] = mover
    return not in_check(ghost, side, snakeBody)

def filter_legal(grid, r, c, candidates, side, snakeHead, snakeBody):
    keep = []
    for mv in candidates:
        if snakeHead is not None and mv == snakeHead: continue
        if bleh(grid, (r, c), mv, side, snakeBody):
            keep.append(mv)
    return keep

def legal_moves(grid, r, c, snakeBody, snakeHead, baitSquare, side, ctx=None):
    rough = rawmoves(grid, r, c, snakeBody, snakeHead, baitSquare, ctx=ctx)
    alreadyInCheck = in_check(grid, side, snakeBody)
    ok = filter_legal(grid, r, c, rough, side, snakeHead, snakeBody)
    if (not alreadyInCheck) and snakeHead is not None and snakeHead in rough:
        ok.append(snakeHead)
    return ok

def legalcheck(grid, side, snakeBody, snakeHead, ctx=None):
    for p in get_pieces(grid):
        if p['alive'] and p['color'] == side:
            rough = rawmoves(grid, p['row'], p['col'], snakeBody, snakeHead, ctx=ctx)
            if filter_legal(grid, p['row'], p['col'], rough, side, snakeHead, snakeBody):
                return True
    return False

def fresh_castle_ctx():
    return {
        'king_moved': {'w': False, 'b': False},
        'rook_moved': {'w': {0: False, 7: False}, 'b': {0: False, 7: False}},
        'ep_target': None,
    }

def recordmove(ctx, movedPiece, fromRC, toRC, capturedPiece):
    side = movedPiece['color']
    fr, fc = fromRC
    if movedPiece['kind'] == 'K': ctx['king_moved'][side] = True
    if movedPiece['kind'] == 'R' and fc in (0, 7) and fr in (0, 7): ctx['rook_moved'][side][fc] = True
    if capturedPiece is not None and capturedPiece['kind'] == 'R':
        cr, cc = toRC
        if cc in (0, 7) and cr in (0, 7): ctx['rook_moved'][capturedPiece['color']][cc] = True

    if movedPiece['kind'] == 'P' and abs(toRC[0] - fromRC[0]) == 2:
        skippedRow = (fromRC[0] + toRC[0]) // 2
        ctx['ep_target'] = (skippedRow, fromRC[1])
    else:
        ctx['ep_target'] = None

class Snake:
    def __init__(self):
        self.body = [(3, 3), (3, 4), (3, 5)]
        self.target = None
        self.target_color = 'w'
        self.bait = None
        self.frozen_turns = 0
        self.alive = True
        self.last_message = "The snake awakens..."
        self.strict_next = False

    def head(self):
        return self.body[0] if self.alive and self.body else None

    def blk(self):
        
        if not self.alive: return set(), None
        bset = set(self.body)
        hed = self.body[0]
        if self.frozen_turns > 0: return bset, None
        return bset - {hed}, hed


    def reach(self, b):
        st = self.head()
        if st is None: return set()
        blocked = set(self.body[:-1])
        blocked |= {(p['row'], p['col']) for p in get_pieces(b) if p['alive'] and p['kind'] == 'K'}
        seen = {st}
        out = set()
        q = deque([st])
        while q:
            cr, cc = q.popleft()
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cr + dr, cc + dc
                nx = (nr, nc)
                if not is_on_board(nr, nc) or nx in seen or nx in blocked: continue
                seen.add(nx)
                out.add(nx)
                if b[nr][nc] is None: q.append(nx)
        return out

    @staticmethod
    def bfs(start, goal, blocked, b):
        #Pathfinding stuff
        seen = {start}
        par = {start: None}
        q = deque([start])
        while q:
            cur = q.popleft()
            if cur == goal: break
            for dr, dc in ((-1, 0), (1, 0), (0, -1), (0, 1)):
                nr, nc = cur[0] + dr, cur[1] + dc
                nx = (nr, nc)
                if not is_on_board(nr, nc) or nx in seen or nx in blocked: continue
                if nx != goal and b[nr][nc] is not None: continue
                seen.add(nx)
                par[nx] = cur
                q.append(nx)
        if goal not in par: return None
        path = []
        cur = goal
        while cur is not None:
            path.append(cur)
            cur = par[cur]
        path.reverse()
        return path

    def nextmv(self, b, goal):
        st = self.head()
        if st is None or goal is None or st == goal: return None
        blocked = set(self.body[:-1])
        blocked |= {(p['row'], p['col']) for p in get_pieces(b) if p['alive'] and p['kind'] == 'K'}
        path = self.bfs(st, goal, blocked, b)
        if path is None or len(path) < 2: return None
        return path[1]

    def pickt(self, b, rc=None, allow_fallback=True):
        op = [p for p in get_pieces(b) if p['alive'] and p['kind'] != 'K']
        if not op:
            self.target = None
            return
        if rc is None: rc = self.reach(b)

        pool = [p for p in op if p['color'] == self.target_color]
        reachable = [p for p in pool if (p['row'], p['col']) in rc]

        if not reachable and allow_fallback:
            other = 'b' if self.target_color == 'w' else 'w'
            pool2 = [p for p in op if p['color'] == other]
            reachable2 = [p for p in pool2 if (p['row'], p['col']) in rc]
            if reachable2:
                self.target_color = other
                reachable = reachable2

        self.target = random.choice(reachable) if reachable else None

    def hit(self):
        if not self.alive or not self.body: return
        if self.frozen_turns > 0:
            self.last_message = "The snake is already stunned and shrugs off the blow!"
            return
        self.frozen_turns = STUN_HALF_MOVES
        self.last_message = "The snake's head was struck! It's stunned for 3 turns."
        self.target = None
        if random.random() < 0.5: self.target_color = 'b' if self.target_color == 'w' else 'w'

    def clrbait(self, rr, cc):
        if self.bait is not None and (self.bait['row'], self.bait['col']) == (rr, cc):
            self.bait = None
            if self.target is self.bait: self.target = None

    def step(self, b):
        if not self.alive: return None

        if self.frozen_turns > 0:
            self.frozen_turns -= 1
            if self.frozen_turns > 0:
                whole_left = (self.frozen_turns + 1) // 2
                self.last_message = f"The snake is stunned ({whole_left} turn(s) left)."
            else:
                self.last_message = "The snake shakes it off and stirs again."
            return None

        rc = self.reach(b)
        strict = self.strict_next
        self.strict_next = False

        if self.bait is not None:
            self.target = self.bait
        else:
            need_new = (self.target is None or not self.target['alive'] or (self.target['row'], self.target['col']) not in rc)
            if need_new: self.pickt(b, rc, allow_fallback=not strict)
            
        if self.target is None:
            self.last_message = "The snake can't find a way to strike..."
            return None

        chosen = self.nextmv(b, (self.target['row'], self.target['col']))
        if chosen is None:
            self.target = None
            self.last_message = "The snake is boxed in..."
            return None

        eatn = b[chosen[0]][chosen[1]]
        if eatn is not None:
            eatn['alive'] = False
            b[chosen[0]][chosen[1]] = None

        bait_hit = (self.bait is not None and chosen == (self.bait['row'], self.bait['col']))
        if bait_hit:
            self.bait = None
            self.target = None

        self.body.insert(0, chosen)
        if eatn is None and not bait_hit:
            self.body.pop()
            self.last_message = "The snake slithers closer..."
        elif eatn is not None:
            nmz = {'P': 'a Pawn', 'N': 'a Knight', 'B': 'a Bishop', 'R': 'a Rook', 'Q': 'the Queen', 'K': 'a King'}[eatn['kind']]
            sidez = 'White' if eatn['color'] == 'w' else 'Black'
            self.last_message = f"The snake devoured {sidez}'s {nmz}!"
            self.target_color = 'b' if eatn['color'] == 'w' else 'w'
            self.strict_next = True
        else:
            self.last_message = "The snake gobbled up the bait!"
        return eatn

def new_game():
    return {
        'turn': 'w',
        'selected': None,
        'legal_moves': [],
        'game_over': False,
        'over_text': "",
        'turn_count': 0,
        'full_turn_count': 0,
        'bait_counts': {'w': 0, 'b': 0},
        'bait_mode': False,
        'toast_text': "",
        'toast_timer': 0,
        'castlectx': fresh_castle_ctx(),
        'promo_pending': None,
    }

def next_turn(S):
    S['turn_count'] += 1
    if S['turn_count'] % 5 == 0:
        gotit = False
        for sdx in ('w', 'b'):
            if S['bait_counts'][sdx] < 1:
                S['bait_counts'][sdx] = 1
                gotit = True
        if gotit:
            S['toast_text'] = "Bait time! Each side without one now has a Bait."
            S['toast_timer'] = 2000
    completing_round = S['turn'] == 'b'
    S['turn'] = 'b' if S['turn'] == 'w' else 'w'
    if completing_round: S['full_turn_count'] += 1

def after_action(S, b, SNK, king_captured=False):
    if king_captured:
        S['game_over'] = True
        winz = 'White' if S['turn'] == 'w' else 'Black'
        S['over_text'] = f"{winz} wins by capture!"
        return
    s_turn(S, b, SNK)

def s_endturn(S, b, SNK, king_eaten=None):
    if king_eaten is not None:
        S['game_over'] = True
        winz = 'Black' if king_eaten == 'w' else 'White'
        S['over_text'] = f"The snake ate the King! {winz} wins by default!"

    if not S['game_over']:
        next_turn(S)
        bodyonly, hed = SNK.blk()
        clr = S['turn']
        chk = in_check(b, clr, bodyonly)
        if not legalcheck(b, clr, bodyonly, hed, ctx=S['castlectx']):
            S['game_over'] = True
            if chk:
                winz = 'Black' if clr == 'w' else 'White'
                S['over_text'] = f"Checkmate! {winz} wins!"
            else:
                S['over_text'] = "Stalemate! It's a draw."
        elif chk:
            S['toast_text'] = f"{'White' if clr == 'w' else 'Black'} is in check!"
            S['toast_timer'] = 1500

def s_turn(S, b, SNK):
    if not SNK.alive:
        s_endturn(S, b, SNK)
        return

    spd = get_speed(S['full_turn_count'])
    king_eaten = None

    for _ in range(spd):
        was_frozen = SNK.frozen_turns > 0
        prev_body = list(SNK.body)
        eatn = SNK.step(b)
        moved = list(SNK.body) != prev_body

        if moved:
            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
            draw_all(b, S, SNK)
            pygame.display.flip()
            pygame.time.delay(STEP_DELAY_MS)

        if eatn is not None and eatn.get('kind') == 'K':
            king_eaten = eatn['color']
            break
        if was_frozen or not moved: break

    s_endturn(S, b, SNK, king_eaten=king_eaten)

def do_attack(S, b, SNK):
    SNK.hit()
    S['selected'] = None
    S['legal_moves'] = []
    after_action(S, b, SNK, king_captured=False)

def draw_square(rr, cc):
    x, y = cc * SQ, rr * SQ
    lite = (rr + cc) % 2 == 0
    imz = BOARD_LIGHT_IMG if lite else BOARD_DARK_IMG
    if imz is not None: screen.blit(imz, (x, y))
    else: pygame.draw.rect(screen, LT if lite else DK, (x, y, SQ, SQ))

def draw_piece(pcx, pos=None):
    if pos is None: x, y = pcx['col'] * SQ, pcx['row'] * SQ
    else: x, y = pos
    imz = PIECE_IMAGES.get((pcx['color'], pcx['kind']))
    if imz is not None:
        screen.blit(imz, (x, y))
        return
    #Fallback
    glf = WHITE_GLYPH[pcx['kind']] if pcx['color'] == 'w' else BLACK_GLYPH[pcx['kind']]
    outc = (0, 0, 0) if pcx['color'] == 'w' else (255, 255, 255)
    filc = (255, 255, 255) if pcx['color'] == 'w' else (20, 20, 20)
    basz = pf.render(glf, True, filc)
    outz = pf.render(glf, True, outc)
    cx = x + SQ // 2 - basz.get_width() // 2
    cy = y + SQ // 2 - basz.get_height() // 2
    for ox, oy in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
        screen.blit(outz, (cx + ox, cy + oy))
    screen.blit(basz, (cx, cy))

def draw_segment(img, x, y, key):
    if img is not None:
        screen.blit(img, (x, y))
        return
    cx, cy = x + SQ // 2, y + SQ // 2
    if key.startswith('head'):
        stunned = 'stunned' in key
        pygame.draw.circle(screen, SFC if stunned else SHC, (cx, cy), SQ // 2 - 6)
        pygame.draw.circle(screen, SEC, (cx - 8, cy - 6), 4)
        pygame.draw.circle(screen, SEC, (cx + 8, cy - 6), 4)
        if stunned: pygame.draw.circle(screen, SFC, (cx, cy), SQ // 2 - 2, 3)
    else:
        pygame.draw.circle(screen, SBC, (cx, cy), SQ // 2 - 6)

def draw_snake(SNK, S):
    if not SNK.alive: return
    assets = SNAKE_ASSETS[get_tier_idx(S['full_turn_count'])]
    stunned = SNK.frozen_turns > 0
    body = SNK.body
    for i, (rr, cc) in enumerate(body):
        x, y = cc * SQ, rr * SQ
        key = get_seg_key(body, i, stunned_head=(stunned and i == 0))
        draw_segment(assets.get(key), x, y, key)

def draw_target(SNK):
    if not SNK.alive or SNK.target is None: return
    rr, cc = SNK.target['row'], SNK.target['col']
    x, y = cc * SQ, rr * SQ
    cx, cy = x + SQ // 2, y + SQ // 2
    pygame.draw.rect(screen, TARGET_HL, (x + 3, y + 3, SQ - 6, SQ - 6), 4, border_radius=10)
    pygame.draw.circle(screen, TARGET_HL, (cx, cy), 6)

def draw_bait(SNK, S):
    if SNK.bait is None: return
    rr, cc = SNK.bait['row'], SNK.bait['col']
    x, y = cc * SQ, rr * SQ
    cx, cy = x + SQ // 2, y + SQ // 2
    tier_idx = get_tier_idx(S['full_turn_count'])
    imz = SNAKE_ASSETS[tier_idx].get('apple') or BAIT_IMG
    if imz is not None:
        screen.blit(imz, (x, y))
    else:
        #Fallback
        pygame.draw.circle(screen, BTC, (cx, cy), SQ // 2 - 20)
        pygame.draw.circle(screen, (255, 255, 255), (cx, cy), SQ // 2 - 20, 2)
        lbz = smf.render("B", True, (255, 255, 255))
        lrz = lbz.get_rect(center=(cx, cy))
        screen.blit(lbz, lrz)
    pygame.draw.circle(screen, BTR, (cx, cy), SQ // 2 - 6, 2)

def draw_badge(rect, bgc, ringon):
    pygame.draw.rect(screen, bgc, rect, border_radius=8)
    bdc = (0, 0, 0) if bgc == BADGE_WHITE_BG else (255, 255, 255)
    pygame.draw.rect(screen, bdc, rect, 2, border_radius=8)
    cx, cy = rect.center
    if APPLE_BADGE_IMG is not None:
        scz = pygame.transform.smoothscale(APPLE_BADGE_IMG, (rect.width - 10, rect.height - 10))
        screen.blit(scz, scz.get_rect(center=(cx, cy)))
    else:
        pygame.draw.circle(screen, BTC, (cx, cy), rect.width // 2 - 8)
        txc = (255, 255, 255) if bgc == BADGE_BLACK_BG else (30, 30, 30)
        lbz = smf.render("B", True, txc)
        screen.blit(lbz, lbz.get_rect(center=(cx, cy)))
    if ringon:
        pygame.draw.rect(screen, BADGE_RING, rect.inflate(6, 6), 3, border_radius=10)

def draw_status(S, SNK):
    pygame.draw.rect(screen, SBG, (0, BOARD_PX, WIDTH, STATUS_H))

    if S['promo_pending'] is not None:
        ln1 = "Choose a piece to promote to..."
    elif S['bait_mode']:
        ln1 = "Click an empty square to place your bait..."
    else:
        ln1 = f"{'White' if S['turn'] == 'w' else 'Black'} to move  |  {SNK.last_message}"
    txs = sf.render(ln1, True, TC)
    screen.blit(txs, (72, BOARD_PX + 10))

    tlft = 5 - (S['turn_count'] % 5)
    spd = get_speed(S['full_turn_count'])
    ln2 = f"Turns played: {S['full_turn_count']}   |   Next bait in {tlft} turn(s)   |   Snake speed: x{spd}"
    ln2s = smf.render(ln2, True, DTC)
    screen.blit(ln2s, (72, BOARD_PX + 40))

    if S['bait_counts']['w'] > 0:
        rngz = S['bait_mode'] and S['turn'] == 'w'
        draw_badge(pygame.Rect(14, BOARD_PX + 16, 48, 48), BADGE_WHITE_BG, rngz)
    if S['bait_counts']['b'] > 0:
        rngz = S['bait_mode'] and S['turn'] == 'b'
        draw_badge(pygame.Rect(WIDTH - 62, BOARD_PX + 16, 48, 48), BADGE_BLACK_BG, rngz)

    if S['toast_timer'] > 0 and S['toast_text']:
        tsz = tf.render(S['toast_text'], True, TTX)
        padx, pady = 18, 10
        bxz = pygame.Surface((tsz.get_width() + padx * 2, tsz.get_height() + pady * 2), pygame.SRCALPHA)
        bxz.fill(TBG)
        bxr = bxz.get_rect(center=(WIDTH // 2, 34))
        screen.blit(bxz, bxr)
        screen.blit(tsz, (bxr.x + padx, bxr.y + pady))

def paint_highlight(rowIdx, colIdx, rgba, *, ringOnly=False, inset=0):
    tile = pygame.Surface((SQ, SQ), pygame.SRCALPHA)
    x0, y0 = colIdx * SQ, rowIdx * SQ
    if ringOnly:
          pygame.draw.rect(tile, rgba, (4 + inset, 4 + inset, SQ - 8 - inset * 2, SQ - 8 - inset * 2), width=5, border_radius=12)
    else:
          pygame.draw.rect(tile, rgba, (inset, inset, SQ - inset * 2, SQ - inset * 2), border_radius=6)
          edge = (rgba[0], rgba[1], rgba[2], min(255, rgba[3] + 70))
          pygame.draw.rect(tile, edge, (inset, inset, SQ - inset * 2, SQ - inset * 2), width=3, border_radius=6)
    screen.blit(tile, (x0, y0))

def prom_rects():
    order = ['Q', 'R', 'B', 'N']
    boxw = 64
    gap = 10
    total = len(order) * boxw + (len(order) - 1) * gap
    startx = WIDTH // 2 - total // 2
    y = HEIGHT // 2 - boxw // 2
    out = []
    for i, kd in enumerate(order):
        out.append((kd, pygame.Rect(startx + i * (boxw + gap), y, boxw, boxw)))
    return out

def draw_promo(S):
    pend = S['promo_pending']
    if pend is None: return
    veil = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 150))
    screen.blit(veil, (0, 0))
    caption = tf.render("Promote pawn to:", True, TTX)
    screen.blit(caption, caption.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 60)))
    for kd, rct in prom_rects():
        pygame.draw.rect(screen, HILITE_PROMO_BG, rct, border_radius=10)
        pygame.draw.rect(screen, STF, rct, 2, border_radius=10)
        fakepc = {'color': pend['color'], 'kind': kd, 'row': 0, 'col': 0}
        draw_piece(fakepc, pos=(rct.x + (rct.w - SQ) // 2, rct.y + (rct.h - SQ) // 2))

def draw_all(bbb, S, SNK):
    if BACKGROUND_IMG is not None: screen.blit(BACKGROUND_IMG, (0, 0))
    for rr in range(8):
        for cc in range(8): draw_square(rr, cc)

    baitrc = (SNK.bait['row'], SNK.bait['col']) if SNK.bait is not None else None

    if S['selected'] is not None:
        sr, sc = S['selected']
        paint_highlight(sr, sc, HILITE_SELECTED, ringOnly=True)
        hedz = SNK.head()
        for mr, mc in S['legal_moves']:
            if hedz is not None and (mr, mc) == hedz: paint_highlight(mr, mc, HILITE_SNAKE_ATK)
            elif baitrc is not None and (mr, mc) == baitrc: paint_highlight(mr, mc, HILITE_BAIT_HIT)
            elif bbb[mr][mc] is not None: paint_highlight(mr, mc, HILITE_CAPTURE)
            else: paint_highlight(mr, mc, HILITE_MOVE, inset=10)

    if S['bait_mode']:
        for rr in range(8):
            for cc in range(8):
                if bbb[rr][cc] is None and not (SNK.alive and (rr, cc) in SNK.body):
                    paint_highlight(rr, cc, HILITE_BAITSPOT, inset=18)

    draw_snake(SNK, S)
    draw_target(SNK)
    draw_bait(SNK, S)

    bodyonly, _ = SNK.blk()
    if in_check(bbb, S['turn'], bodyonly):
        kp = get_king_sq(bbb, S['turn'])
        if kp is not None: paint_highlight(kp[0], kp[1], (255, 30, 30, 100), ringOnly=True)

    for pcx in get_pieces(bbb): draw_piece(pcx)
    draw_status(S, SNK)
    if S['promo_pending'] is not None: draw_promo(S)

    if S['game_over']:
        ovl = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        ovl.fill(GOBG)
        screen.blit(ovl, (0, 0))
        txs = bf.render(S['over_text'], True, (255, 60, 60))
        rct = txs.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        screen.blit(txs, rct)

def apply_moves(S, BRD, SNK, srcRC, dstRC):
    sr, sc = srcRC
    rr, cc = dstRC
    movingPc = BRD[sr][sc]
    ctx = S['castlectx']
    ep_before = ctx['ep_target']
    capturedPc = BRD[rr][cc]

    isEnPassant = (movingPc['kind'] == 'P' and (rr, cc) == ep_before and capturedPc is None and sc != cc)
    epVictimSq = None
    if isEnPassant:
        epVictimSq = (sr, cc)
        capturedPc = BRD[epVictimSq[0]][epVictimSq[1]]

    isCastle = (movingPc['kind'] == 'K' and abs(cc - sc) == 2)
    BRD[sr][sc] = None
    BRD[rr][cc] = movingPc
    movingPc['row'], movingPc['col'] = rr, cc

    if isEnPassant and epVictimSq is not None: BRD[epVictimSq[0]][epVictimSq[1]] = None

    if isCastle:
        homeRow = sr
        if cc == 6:
            rookPc = BRD[homeRow][7]
            BRD[homeRow][7] = None
            BRD[homeRow][5] = rookPc
            if rookPc is not None: rookPc['row'], rookPc['col'] = homeRow, 5
        elif cc == 2:
            rookPc = BRD[homeRow][0]
            BRD[homeRow][0] = None
            BRD[homeRow][3] = rookPc
            if rookPc is not None: rookPc['row'], rookPc['col'] = homeRow, 3

    recordmove(ctx, movingPc, (sr, sc), (rr, cc), capturedPc)
    kingcap = capturedPc is not None and capturedPc['kind'] == 'K'
    if capturedPc is not None: capturedPc['alive'] = False

    SNK.clrbait(rr, cc)
    needsPromo = (movingPc['kind'] == 'P' and (rr == 0 or rr == 7) and not kingcap)
    if needsPromo:
        S['promo_pending'] = {'row': rr, 'col': cc, 'color': movingPc['color']}
        return False

    after_action(S, BRD, SNK, king_captured=kingcap)
    return kingcap

def promotion(S, BRD, SNK, chosenKind):
    pend = S['promo_pending']
    if pend is None: return
    pc = BRD[pend['row']][pend['col']]
    if pc is not None: pc['kind'] = chosenKind
    S['promo_pending'] = None
    after_action(S, BRD, SNK, king_captured=False)

def main():
    BRD = setup_board()
    SNK = Snake()
    S = new_game()

    while True:
        dtx = clock.tick(60)
        for evz in pygame.event.get():
            if evz.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if evz.type == pygame.MOUSEBUTTONDOWN and not S['game_over']:
                mx, my = evz.pos
                if S['promo_pending'] is not None:
                    for kd, rct in prom_rects():
                        if rct.collidepoint(mx, my):
                            promotion(S, BRD, SNK, kd)
                            break
                    continue

                lbdg = pygame.Rect(14, BOARD_PX + 16, 48, 48)
                rbdg = pygame.Rect(WIDTH - 62, BOARD_PX + 16, 48, 48)

                # Bait logic 
                if S['bait_counts']['w'] > 0 and lbdg.collidepoint(mx, my):
                    if S['turn'] != 'w':
                        S['toast_text'] = "It's not White's turn."
                        S['toast_timer'] = 1200
                    elif S['bait_mode']: S['bait_mode'] = False
                    elif in_check(BRD, 'w', SNK.blk()[0]):
                        S['toast_text'] = "Can't place bait while in check!"
                        S['toast_timer'] = 1200
                    else:
                        S['bait_mode'] = True
                        S['selected'] = None
                        S['legal_moves'] = []
                    continue

                if S['bait_counts']['b'] > 0 and rbdg.collidepoint(mx, my):
                    if S['turn'] != 'b':
                        S['toast_text'] = "It's not Black's turn."
                        S['toast_timer'] = 1200
                    elif S['bait_mode']: S['bait_mode'] = False
                    elif in_check(BRD, 'b', SNK.blk()[0]):
                        S['toast_text'] = "Can't place bait while in check!"
                        S['toast_timer'] = 1200
                    else:
                        S['bait_mode'] = True
                        S['selected'] = None
                        S['legal_moves'] = []
                    continue

                if my >= BOARD_PX: continue
                cc, rr = mx // SQ, my // SQ

                if S['bait_mode']:
                    occbypc = BRD[rr][cc] is not None
                    occbysnk = SNK.alive and (rr, cc) in SNK.body
                    if not occbypc and not occbysnk:
                        SNK.bait = {'row': rr, 'col': cc, 'alive': True, 'kind': 'BAIT'}
                        S['bait_counts'][S['turn']] -= 1
                        S['bait_mode'] = False
                        after_action(S, BRD, SNK, king_captured=False)
                    else:
                        S['toast_text'] = "Can't place bait there."
                        S['toast_timer'] = 1200
                    continue

                bodyonly, hedz = SNK.blk()
                baitrc = (SNK.bait['row'], SNK.bait['col']) if SNK.bait is not None else None

                if S['selected'] is None:
                    pcx = BRD[rr][cc]
                    if pcx is not None and pcx['color'] == S['turn']:
                        S['selected'] = (rr, cc)
                        S['legal_moves'] = legal_moves(BRD, rr, cc, bodyonly, hedz, baitrc, S['turn'], ctx=S['castlectx'])
                else:
                    if (rr, cc) in S['legal_moves']:
                        sr, sc = S['selected']
                        atkhed = (hedz is not None and (rr, cc) == hedz)
                        S['selected'] = None
                        S['legal_moves'] = []
                        if atkhed: do_attack(S, BRD, SNK)
                        else: apply_moves(S, BRD, SNK, (sr, sc), (rr, cc))
                    else:
                        pcx = BRD[rr][cc]
                        if pcx is not None and pcx['color'] == S['turn']:
                            S['selected'] = (rr, cc)
                            S['legal_moves'] = legal_moves(BRD, rr, cc, bodyonly, hedz, baitrc, S['turn'], ctx=S['castlectx'])
                        else:
                            S['selected'] = None
                            S['legal_moves'] = []

        if S['toast_timer'] > 0:
            S['toast_timer'] -= dtx
            if S['toast_timer'] <= 0:
                S['toast_timer'] = 0
                S['toast_text'] = ""

        draw_all(BRD, S, SNK)
        pygame.display.flip()

if __name__ == '__main__':
    main()
