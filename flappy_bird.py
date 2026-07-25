import pygame
import random
import sys
import os
import json
import math
import webbrowser
import urllib.parse

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_GAP = 150
PIPE_WIDTH = 60
PIPE_SPEED = 3
GROUND_HEIGHT = 80
MAX_LEADERBOARD_ENTRIES = 10

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
YELLOW = (255, 220, 0)
BLACK = (0, 0, 0)
BLUE = (135, 206, 235)

# Resource base: when frozen by PyInstaller the bundle is unpacked to
# sys._MEIPASS; running from source it's just this file's folder.
if getattr(sys, "frozen", False):
    BASE_DIR = sys._MEIPASS
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

ASSET_SUBFOLDER = "assets"  # <-- change this if your folder has a different name
ASSET_DIR = os.path.join(BASE_DIR, ASSET_SUBFOLDER)
SPRITE_DIR = os.path.join(ASSET_DIR, "sprites")  # all .png images live here
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")    # all .wav sounds live here


def _user_data_dir():
    """A per-user, writable folder for save data (used by the packaged build)."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    path = os.path.join(base, "FlappyBird")
    os.makedirs(path, exist_ok=True)
    return path


# Save the leaderboard next to the script in dev, but in a writable user
# folder once packaged (the unpacked bundle folder is temporary/read-only).
if getattr(sys, "frozen", False):
    LEADERBOARD_PATH = os.path.join(_user_data_dir(), "leaderboard.json")
else:
    LEADERBOARD_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "leaderboard.json")

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
pygame.display.set_icon(pygame.image.load(os.path.join(SPRITE_DIR, "bird_up.png")))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 32)
button_font = pygame.font.SysFont(None, 36)

# Game states
STATE_START = "start"          # home page: title + bird + start/rate/score buttons
STATE_GET_READY = "get_ready"  # "tap to play" screen (message.png, no title)
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_LEADERBOARD = "leaderboard"


def load_image(filename):
    """Load an image from assets/sprites if it exists, otherwise return None (fallback to shapes)."""
    path = os.path.join(SPRITE_DIR, filename)
    if not os.path.exists(path):
        print(f"[warning] missing asset: {path}")
        return None
    return pygame.image.load(path).convert_alpha()


def load_sound(filename):
    path = os.path.join(SOUND_DIR, filename)
    if not os.path.exists(path):
        print(f"[warning] missing sound: {path}")
        return None
    try:
        return pygame.mixer.Sound(path)
    except pygame.error as e:
        print(f"[warning] could not load sound {filename}: {e}")
        return None


# Audio toggles (flipped from the start-page buttons)
SFX_ON = True
MUSIC_ON = True
MUSIC_LOADED = False


def play_sound(sound):
    if sound and SFX_ON:
        sound.play()


def toggle_sfx():
    global SFX_ON
    SFX_ON = not SFX_ON


def start_music():
    """Begin the looping background track (only if loaded and enabled)."""
    if MUSIC_LOADED and MUSIC_ON:
        pygame.mixer.music.play(-1)


def set_music(on):
    global MUSIC_ON
    MUSIC_ON = on
    if not MUSIC_LOADED:
        return
    if on:
        if pygame.mixer.music.get_busy():
            pygame.mixer.music.unpause()
        else:
            pygame.mixer.music.play(-1)
    else:
        pygame.mixer.music.pause()


def toggle_music():
    set_music(not MUSIC_ON)


def rate_game():
    """Open a page where the player can rate the game."""
    try:
        webbrowser.open("https://flappybird.io/")
    except Exception as e:
        print(f"[warning] could not open rate page: {e}")


def share_score(score):
    """Share the score via the system's default browser (a tweet intent)."""
    text = f"I scored {score} in Flappy Bird! Can you beat me?"
    url = "https://twitter.com/intent/tweet?text=" + urllib.parse.quote(text)
    try:
        webbrowser.open(url)
    except Exception as e:
        print(f"[warning] could not open share page: {e}")


def scale_to_width(img, target_width):
    """Scale preserving aspect ratio, driven by width."""
    if img is None:
        return None
    ratio = target_width / img.get_width()
    target_height = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (target_width, target_height))


def scale_to_height(img, target_height):
    """Scale preserving aspect ratio, driven by height."""
    if img is None:
        return None
    ratio = target_height / img.get_height()
    target_width = int(img.get_width() * ratio)
    return pygame.transform.smoothscale(img, (target_width, target_height))


def scale_to_height_crisp(img, target_height):
    """Scale small pixel-art (buttons) by height with nearest-neighbour so it stays sharp."""
    if img is None:
        return None
    ratio = target_height / img.get_height()
    target_width = int(round(img.get_width() * ratio))
    return pygame.transform.scale(img, (target_width, target_height))


# ---------- Load assets ----------

def _load_bird_frames(up, mid, down):
    frames = [
        scale_to_width(load_image(up), 40),
        scale_to_width(load_image(mid), 40),
        scale_to_width(load_image(down), 40),
    ]
    return frames if frames[0] is not None else None


def _scale_bg(name):
    raw = load_image(name)
    return pygame.transform.smoothscale(raw, (WIDTH, HEIGHT)) if raw else None


# Bird colours (yellow / blue / red)
BIRD_FRAMES_YELLOW = _load_bird_frames("bird_up.png", "bird_mid.png", "bird_down.png")
BIRD_FRAMES_BLUE = _load_bird_frames(
    "bluebird-upflap.png", "bluebird-midflap.png", "bluebird-downflap.png")
BIRD_FRAMES_RED = _load_bird_frames(
    "redBird-upFlap.png", "redBird-midFlap.png", "redBird-downFlap.png")

# Pipe: cap (the rim) + a tileable body strip, scaled to PIPE_WIDTH,
# then the body strip is repeated to reach whatever length each pipe needs
PIPE_CAP_GREEN = scale_to_width(load_image("pipe_cap.png"), PIPE_WIDTH)
PIPE_BODY_GREEN = scale_to_width(load_image("pipe_body.png"), PIPE_WIDTH)
PIPE_CAP_RED = scale_to_width(load_image("pipe_cap_red.png"), PIPE_WIDTH)
PIPE_BODY_RED = scale_to_width(load_image("pipe_body_red.png"), PIPE_WIDTH)

# Backgrounds (sky) stretched to fill the screen
BG_DAY = _scale_bg("background-day.png")
BG_NIGHT = _scale_bg("background-night.png")

# Each theme is a (bird colour + pipe colour + sky) combo. They auto-cycle
# during play; "dark" picks white UI text for readability over a dark sky.
THEMES = {
    "day":   {"bird": BIRD_FRAMES_YELLOW, "cap": PIPE_CAP_GREEN, "body": PIPE_BODY_GREEN, "bg": BG_DAY,   "dark": False},
    "dusk":  {"bird": BIRD_FRAMES_RED,    "cap": PIPE_CAP_RED,   "body": PIPE_BODY_RED,   "bg": BG_DAY,   "dark": False},
    "night": {"bird": BIRD_FRAMES_BLUE,   "cap": PIPE_CAP_RED,   "body": PIPE_BODY_RED,   "bg": BG_NIGHT, "dark": True},
}
THEME_ORDER = ["day", "dusk", "night"]
THEME_CHANGE_EVERY = 5  # advance to the next theme every N points scored

# Current-theme pointers (swapped by set_theme). The draw code reads these.
THEME = "day"
THEME_DARK = False
BIRD_FRAMES = None
PIPE_CAP_IMG = None
PIPE_BODY_IMG = None
PIPE_CAP_IMG_FLIPPED = None
BG_IMG = None


def set_theme(name):
    """Point the shared draw globals at the named theme's asset set."""
    global THEME, THEME_DARK, BIRD_FRAMES, PIPE_CAP_IMG, PIPE_BODY_IMG, PIPE_CAP_IMG_FLIPPED, BG_IMG
    cfg = THEMES.get(name, THEMES["day"])
    THEME = name
    THEME_DARK = cfg["dark"]
    BIRD_FRAMES, PIPE_CAP_IMG, PIPE_BODY_IMG, BG_IMG = cfg["bird"], cfg["cap"], cfg["body"], cfg["bg"]
    PIPE_CAP_IMG_FLIPPED = pygame.transform.flip(PIPE_CAP_IMG, False, True) if PIPE_CAP_IMG else None


def advance_theme():
    """Cycle to the next theme in THEME_ORDER (called automatically during play)."""
    idx = THEME_ORDER.index(THEME) if THEME in THEME_ORDER else 0
    set_theme(THEME_ORDER[(idx + 1) % len(THEME_ORDER)])


set_theme("day")

# Scrolling ground strip
GROUND_IMG = scale_to_height(load_image("base.png"), GROUND_HEIGHT)

# Score digits (sprite font)
DIGIT_IMGS = None
_digits_raw = [load_image(f"digit_{i}.png") for i in range(10)]
if all(d is not None for d in _digits_raw):
    DIGIT_IMGS = [scale_to_height(d, 36) for d in _digits_raw]

# Leaderboard sprite font: white "mid" digits + a dot separator, on a tall base
MID_DIGIT_H = 22
DIGIT_MID_IMGS = None
_mid_raw = [load_image(f"digit_{i}_mid.png") for i in range(10)]
if all(d is not None for d in _mid_raw):
    DIGIT_MID_IMGS = [scale_to_height(d, MID_DIGIT_H) for d in _mid_raw]
DOT_IMG = scale_to_height(load_image("dot.png"), 8)

# Tall ground for the leaderboard: base art on top, plain tan filled to the bottom
TAN_COLOR = (222, 216, 149)
LB_BASE_IMG = scale_to_width(load_image("base.png"), WIDTH)
LB_GRASS_TOP_Y = 150  # y of the top (grass) edge of the leaderboard ground

# Menu art: title logo + "get ready" banner + tap indicator + game over banner
TITLE_IMG = scale_to_width(load_image("flappybird.png"), 210)
GET_READY_MSG_IMG = scale_to_width(load_image("getReadyMessage.png"), 240)
TAP_MSG_IMG = scale_to_width(load_image("tapMessage.png"), 130)
GAME_OVER_IMG = scale_to_width(load_image("gameover.png"), 220)
LEADERBOARD_TITLE_IMG = scale_to_width(load_image("leaderboard.png"), 260)

# Game-over score card + medals (places 1-4) + "new best" badge + small digits
SCORE_CARD_IMG = scale_to_width(load_image("scoreCard.png"), 300)
MEDAL_IMGS = {
    1: scale_to_height(load_image("gold.png"), 56),
    2: scale_to_height(load_image("silver.png"), 56),
    3: scale_to_height(load_image("bronze.png"), 56),
    4: scale_to_height(load_image("iron.png"), 56),
}
NEW_IMG = scale_to_height(load_image("new.png"), 20)
DIGIT_SML_IMGS = None
_sml_raw = [load_image(f"digit_{i}_sml.png") for i in range(10)]
if all(d is not None for d in _sml_raw):
    DIGIT_SML_IMGS = [scale_to_height(d, 22) for d in _sml_raw]

# Start-page buttons (larger art, smooth-scaled)
START_PLAY_BTN_IMG = scale_to_width(load_image("startButton.png"), 165)
LEADERBOARD_BTN_IMG = scale_to_height(load_image("leaderBoardButton.png"), 52)

# Pixel-art UI buttons (kept crisp with nearest-neighbour scaling)
BTN_HEIGHT = 46
RATE_BTN_IMG = scale_to_height(load_image("rateRec.png"), 52)
OK_BTN_IMG = scale_to_height_crisp(load_image("okRec.png"), BTN_HEIGHT)
MENU_BTN_IMG = scale_to_height_crisp(load_image("menuRec.png"), BTN_HEIGHT)
SHARE_BTN_IMG = scale_to_height_crisp(load_image("shareRec.png"), BTN_HEIGHT)

# Pause / resume buttons (square icons). A big resume is used in the centered menu.
PAUSE_BTN_IMG = scale_to_height(load_image("pauseButton.png"), 44)
RESUME_BTN_IMG = scale_to_height(load_image("resumeButton.png"), 44)
RESUME_BIG_IMG = scale_to_height(load_image("resumeButton.png"), 60)

# Semi-transparent dark layer drawn over the scene when paused
PAUSE_OVERLAY = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
PAUSE_OVERLAY.fill((0, 0, 0, 150))

# Solid black surface reused for the dark fade transition (alpha set per frame)
FADE_SURFACE = pygame.Surface((WIDTH, HEIGHT))
FADE_SURFACE.fill((0, 0, 0))
FADE_SPEED = 20  # alpha change per frame during the fade

# Sound effects
SND_WING = load_sound("wing.wav")
SND_POINT = load_sound("point.wav")
SND_HIT = load_sound("hit.wav")
SND_DIE = load_sound("die.wav")
SND_SWOOSH = load_sound("swoosh.wav")

# Music / SFX on-off toggle icons (shown on the start page only)
MUSIC_ON_IMG = scale_to_height(load_image("musicOnButton.png"), 44)
MUSIC_OFF_IMG = scale_to_height(load_image("musicOffButton.png"), 44)
SFX_ON_IMG = scale_to_height(load_image("soundOnButton.png"), 44)
SFX_OFF_IMG = scale_to_height(load_image("soundOffButton.png"), 44)

# Background music: streamed + looped, independent of the SFX channel.
# (The provided file is actually MP3 data, so prefer the .mp3 name.)
MUSIC_CANDIDATES = ["Flappy Bird Theme Song.mp3", "Flappy Bird Theme Song.wav"]
for _music_name in MUSIC_CANDIDATES:
    _music_path = os.path.join(SOUND_DIR, _music_name)
    if not os.path.exists(_music_path):
        continue
    try:
        pygame.mixer.music.load(_music_path)
        pygame.mixer.music.set_volume(0.4)
        MUSIC_LOADED = True
        break
    except pygame.error as e:
        print(f"[warning] could not load music {_music_name}: {e}")
if not MUSIC_LOADED:
    print("[warning] no playable background music found")


# ---------- Leaderboard persistence ----------

def load_leaderboard():
    if not os.path.exists(LEADERBOARD_PATH):
        return []
    try:
        with open(LEADERBOARD_PATH, "r") as f:
            data = json.load(f)
            if isinstance(data, list):
                return sorted([int(s) for s in data], reverse=True)[:MAX_LEADERBOARD_ENTRIES]
    except (json.JSONDecodeError, ValueError, OSError):
        pass
    return []


def save_score(score):
    scores = load_leaderboard()
    scores.append(score)
    scores = sorted(scores, reverse=True)[:MAX_LEADERBOARD_ENTRIES]
    try:
        with open(LEADERBOARD_PATH, "w") as f:
            json.dump(scores, f)
    except OSError as e:
        print(f"[warning] could not save leaderboard: {e}")
    return scores


# ---------- UI Button ----------

class Button:
    def __init__(self, x, y, width, height, text, color=GREEN, hover_color=DARK_GREEN, image=None):
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.image = image
        if image:
            # center the button on (x, y) using the image's own size
            self.rect = image.get_rect(center=(x, y))
        else:
            self.rect = pygame.Rect(x - width // 2, y - height // 2, width, height)

    def draw(self, dy=0):
        rect = self.rect.move(0, dy)
        if self.image:
            screen.blit(self.image, rect)
        else:
            mouse_pos = pygame.mouse.get_pos()
            is_hover = rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, self.hover_color if is_hover else self.color, rect, border_radius=8)
            pygame.draw.rect(screen, BLACK, rect, 2, border_radius=8)
            text_surf = button_font.render(self.text, True, WHITE)
            text_rect = text_surf.get_rect(center=rect.center)
            screen.blit(text_surf, text_rect)

    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)


class Bird:
    def __init__(self):
        self.x = WIDTH // 2 - 100
        self.y = HEIGHT // 2
        self.velocity = 0
        self.radius = 15

    def flap(self):
        self.velocity = FLAP_STRENGTH
        play_sound(SND_WING)

    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity

    def draw(self):
        if BIRD_FRAMES:
            frame = BIRD_FRAMES[(pygame.time.get_ticks() // 100) % 3]
            angle = max(-25, min(90, -self.velocity * 5))
            rotated = pygame.transform.rotate(frame, angle)
            rect = rotated.get_rect(center=(self.x, int(self.y)))
            screen.blit(rotated, rect)
        else:
            pygame.draw.circle(screen, YELLOW, (self.x, int(self.y)), self.radius)
            pygame.draw.circle(screen, BLACK, (self.x, int(self.y)), self.radius, 2)

    def get_rect(self):
        # slightly shrink hitbox so image collisions feel fair
        return pygame.Rect(self.x - self.radius + 4, self.y - self.radius + 4,
                            (self.radius - 4) * 2, (self.radius - 4) * 2)


class Pipe:
    def __init__(self, x):
        self.x = x
        max_top = HEIGHT - GROUND_HEIGHT - 80 - PIPE_GAP
        self.height = random.randint(80, max(81, max_top))
        self.passed = False

    def update(self):
        self.x -= PIPE_SPEED

    def _draw_column(self, top_y, bottom_y, cap_img, cap_at_bottom):
        """Fill the vertical span [top_y, bottom_y] with tiled body + one cap.
        cap_at_bottom=True draws the cap at bottom_y (used for the top pipe,
        whose opening faces down); otherwise the cap sits at top_y."""
        cap_h = cap_img.get_height()
        body_h = PIPE_BODY_IMG.get_height()

        if cap_at_bottom:
            screen.blit(cap_img, (self.x, bottom_y - cap_h))
            fill_bottom = bottom_y - cap_h
            y = fill_bottom
            while y > top_y:
                y -= body_h
                screen.blit(PIPE_BODY_IMG, (self.x, y))
        else:
            screen.blit(cap_img, (self.x, top_y))
            y = top_y + cap_h
            while y < bottom_y:
                screen.blit(PIPE_BODY_IMG, (self.x, y))
                y += body_h

    def draw(self):
        ground_y = HEIGHT - GROUND_HEIGHT
        if PIPE_CAP_IMG and PIPE_BODY_IMG:
            self._draw_column(0, self.height, PIPE_CAP_IMG_FLIPPED, cap_at_bottom=True)
            self._draw_column(self.height + PIPE_GAP, ground_y, PIPE_CAP_IMG, cap_at_bottom=False)
        else:
            pygame.draw.rect(screen, GREEN, (self.x, 0, PIPE_WIDTH, self.height))
            pygame.draw.rect(screen, GREEN, (self.x, self.height + PIPE_GAP,
                                              PIPE_WIDTH, ground_y - self.height - PIPE_GAP))

    def get_rects(self):
        ground_y = HEIGHT - GROUND_HEIGHT
        top = pygame.Rect(self.x, 0, PIPE_WIDTH, self.height)
        bottom = pygame.Rect(self.x, self.height + PIPE_GAP,
                              PIPE_WIDTH, ground_y - self.height - PIPE_GAP)
        return top, bottom

    def off_screen(self):
        return self.x + PIPE_WIDTH < 0


def draw_background():
    if BG_IMG:
        screen.blit(BG_IMG, (0, 0))
    else:
        screen.fill(BLUE)


def draw_ground(offset):
    ground_y = HEIGHT - GROUND_HEIGHT
    if GROUND_IMG:
        tile_w = GROUND_IMG.get_width()
        x = -(offset % tile_w)
        while x < WIDTH:
            screen.blit(GROUND_IMG, (x, ground_y))
            x += tile_w
    else:
        pygame.draw.rect(screen, (222, 216, 149), (0, ground_y, WIDTH, GROUND_HEIGHT))


def draw_text_center(text, font_obj, color, y):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH // 2, y))
    screen.blit(surf, rect)


def ui_text_color():
    """White text reads better over a dark (night) sky; black over a light sky."""
    return WHITE if THEME_DARK else BLACK


def draw_audio_toggles(music_rect, sfx_rect):
    """Draw the music and SFX on/off icons reflecting their current state."""
    mimg = MUSIC_ON_IMG if MUSIC_ON else MUSIC_OFF_IMG
    simg = SFX_ON_IMG if SFX_ON else SFX_OFF_IMG
    if mimg:
        screen.blit(mimg, mimg.get_rect(center=music_rect.center))
    if simg:
        screen.blit(simg, simg.get_rect(center=sfx_rect.center))


def draw_score_sprites(score, y):
    """Draw the score using the sprite digit font, centered horizontally."""
    digits = [DIGIT_IMGS[int(d)] for d in str(score)]
    total_width = sum(d.get_width() for d in digits) + (len(digits) - 1) * 2
    x = WIDTH // 2 - total_width // 2
    for d in digits:
        screen.blit(d, (x, y))
        x += d.get_width() + 2


def draw_score(score, y):
    if DIGIT_IMGS:
        draw_score_sprites(score, y)
    else:
        surf = small_font.render(str(score), True, WHITE)
        rect = surf.get_rect(center=(WIDTH // 2, y + 15))
        screen.blit(surf, rect)


def draw_sml_number(n, cx, cy):
    """Draw a number centered at (cx, cy) with the small card digits; returns its width."""
    if not DIGIT_SML_IMGS:
        surf = small_font.render(str(n), True, BLACK)
        screen.blit(surf, surf.get_rect(center=(cx, cy)))
        return surf.get_width()
    digits = [DIGIT_SML_IMGS[int(c)] for c in str(n)]
    total = sum(d.get_width() for d in digits) + (len(digits) - 1) * 2
    x = cx - total // 2
    for d in digits:
        screen.blit(d, (x, cy - d.get_height() // 2))
        x += d.get_width() + 2
    return total


def draw_score_card(cx, cy, last_score, best_score, rank, is_new):
    """Game-over card: medal (top-4 finish only), this game's score, and the best score."""
    if not SCORE_CARD_IMG:
        draw_text_center(f"Score: {last_score}", small_font, ui_text_color(), cy - 12)
        draw_text_center(f"Best: {best_score}", small_font, ui_text_color(), cy + 16)
        return
    rect = SCORE_CARD_IMG.get_rect(center=(cx, cy))
    screen.blit(SCORE_CARD_IMG, rect)
    # medal in the left circle, only when the last game placed in the top 4
    if 1 <= rank <= 4 and last_score > 0:
        medal = MEDAL_IMGS.get(rank)
        if medal:
            mc = (rect.left + int(0.22 * rect.width), rect.top + int(0.53 * rect.height))
            screen.blit(medal, medal.get_rect(center=mc))
    # this game's score (under SCORE) and the best score (under BEST), on the right
    value_x = rect.left + int(0.80 * rect.width)
    draw_sml_number(last_score, value_x, rect.top + int(0.35 * rect.height))
    best_y = rect.top + int(0.71 * rect.height)
    best_w = draw_sml_number(best_score, value_x, best_y)
    # "NEW" badge beside the best when the last game set a new record (#1)
    if is_new and NEW_IMG:
        screen.blit(NEW_IMG, NEW_IMG.get_rect(midright=(value_x - best_w // 2 - 15, best_y - 27)))


# ---------- Leaderboard page ----------

LB_SCORE_TOP = 205    # y-center of the first score row
LB_SCORE_PITCH = 29   # vertical spacing between rows

# Entrance animation: the base grows, then the title and rows fall from the sky.
LB_GRASS_START_Y = HEIGHT - GROUND_HEIGHT  # where the ground sits before it grows
LB_SKY_Y = -40             # off-screen start height for falling items
LB_GROW_FRAMES = 14        # frames for the base to grow to full height
LB_TITLE_TARGET_Y = 80     # final y-center of the title
LB_TITLE_START = 4         # frame the title starts falling
LB_ROWS_START = 14         # frame the first row starts falling
LB_ROW_STAGGER = 2         # extra delay per row
LB_FALL_DUR = 14           # frames each item takes to fall into place
LB_ANIM_CAP = 240          # cap the animation counter


def ease_out(p):
    """Decelerating ease for 0..1 (fast start, soft landing)."""
    p = 0.0 if p < 0 else (1.0 if p > 1 else p)
    return 1 - (1 - p) * (1 - p)


def fall_y(target_y, start_frame, anim):
    """Y of an item falling from the sky into target_y over LB_FALL_DUR frames."""
    p = ease_out((anim - start_frame) / LB_FALL_DUR)
    return LB_SKY_Y + (target_y - LB_SKY_Y) * p


def draw_leaderboard_ground(grass_top_y):
    """Tall base: the grass strip at grass_top_y, plain tan filled down to the bottom."""
    top = int(grass_top_y)
    if LB_BASE_IMG:
        screen.blit(LB_BASE_IMG, (0, top))
        base_bottom = top + LB_BASE_IMG.get_height()
    else:
        base_bottom = top
    if base_bottom < HEIGHT:
        pygame.draw.rect(screen, TAN_COLOR, (0, base_bottom, WIDTH, HEIGHT - base_bottom))


def draw_leaderboard_title(cy):
    """The Leaderboard banner png, or a text fallback if it's missing."""
    if LEADERBOARD_TITLE_IMG:
        screen.blit(LEADERBOARD_TITLE_IMG, LEADERBOARD_TITLE_IMG.get_rect(center=(WIDTH // 2, int(cy))))
    else:
        draw_text_center("Leaderboard", font, ui_text_color(), int(cy))


def draw_leaderboard_row(rank, score, cy):
    """Rank (right-aligned) . score (left-aligned) drawn with the white mid-digit sprites."""
    if not DIGIT_MID_IMGS:
        draw_text_center(f"{rank}.  {score}", small_font, BLACK, int(cy))
        return
    baseline = int(cy) + MID_DIGIT_H // 2  # digits and the dot rest their bottoms here
    rank_right_x, dot_x, score_left_x = 176, 186, 202
    # rank, right-aligned so the dots line up in a column
    x = rank_right_x
    for ch in reversed(str(rank)):
        img = DIGIT_MID_IMGS[int(ch)]
        x -= img.get_width()
        screen.blit(img, (x, baseline - img.get_height()))
        x -= 2
    if DOT_IMG:
        screen.blit(DOT_IMG, (dot_x, baseline - DOT_IMG.get_height()))
    # score, left-aligned from a fixed column
    x = score_left_x
    for ch in str(score):
        img = DIGIT_MID_IMGS[int(ch)]
        screen.blit(img, (x, baseline - img.get_height()))
        x += img.get_width() + 2


# ---------- Start-page entrance ----------

START_ANIM_FRAMES = 16   # frames for a button to slide up into place
START_SLIDE_DIST = 320   # how far below its target a button starts
START_BTN_STAGGER = 3    # per-button delay so they arrive one after another


def start_slide(anim, delay):
    """Vertical offset (px, positive = below target) for a start-page button sliding up."""
    p = ease_out((anim - delay) / START_ANIM_FRAMES)
    return int((1 - p) * START_SLIDE_DIST)


def main():
    state = STATE_START
    paused = False
    bird = Bird()
    pipes = [Pipe(WIDTH + 100)]
    score = 0
    leaderboard = load_leaderboard()
    ground_offset = 0
    lb_anim = 0            # leaderboard entrance-animation frame counter
    start_anim = 0        # start-page button slide-in frame counter
    last_rank = 0         # this game's placement (1 = best); 0 = outside the board
    is_new_best = False   # did this game set a new #1 best?
    go_anim = 0           # game-over card/buttons slide-in frame counter

    # Dark fade transition (used for start -> get ready)
    fade_state = None      # None | "out" | "in"
    fade_alpha = 0
    fade_target = None     # state to switch to at peak darkness
    fade_reset = False     # whether to reset_game() at the switch

    # Start (home) page buttons:
    #   big PLAY button in the middle, LEADERBOARD + RATE in a row beneath it.
    start_button = Button(WIDTH // 2, 300, 165, 97, "Start", image=START_PLAY_BTN_IMG)
    leaderboard_button = Button(141, 430, 88, 52, "Leaderboard", image=LEADERBOARD_BTN_IMG)
    rate_button = Button(258, 430, 93, 52, "Rate", image=RATE_BTN_IMG)

    # Music / SFX toggles in the top corners of the start page
    music_rect = pygame.Rect(0, 0, 44, 44)
    music_rect.center = (34, 40)
    sfx_rect = pygame.Rect(0, 0, 44, 44)
    sfx_rect.center = (366, 40)

    # Pause / resume live in the same top-left spot (tap-to-play + during play)
    pause_button = Button(38, 38, 44, 44, "Pause", image=PAUSE_BTN_IMG)
    resume_corner_button = Button(38, 38, 44, 44, "Resume", image=RESUME_BTN_IMG)

    # Centered pause menu, shown when pausing from the tap-to-play screen
    resume_center_button = Button(WIDTH // 2, 270, 60, 60, "Resume", image=RESUME_BIG_IMG)
    pause_menu_button = Button(WIDTH // 2, 350, 128, 46, "Menu", image=MENU_BTN_IMG)

    # "Menu" (back to start) button at the bottom of the leaderboard, below the scores
    menu_button = Button(WIDTH // 2, 555, 128, 46, "Menu", image=MENU_BTN_IMG)

    # Game over buttons: OK (back to tap-to-play) + Share
    ok_button = Button(138, 450, 128, 46, "OK", image=OK_BTN_IMG)
    share_button = Button(282, 450, 131, 46, "Share", image=SHARE_BTN_IMG)

    def reset_game():
        nonlocal bird, pipes, score
        bird = Bird()
        pipes = [Pipe(WIDTH + 100)]
        score = 0
        set_theme("day")  # every run starts on day; it auto-cycles as you score

    start_music()  # loop the theme from the start (until toggled off)

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if fade_state is not None:
                continue  # ignore input while a fade transition is running

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if state == STATE_START:
                    play_sound(SND_SWOOSH)
                    fade_state, fade_target, fade_reset = "out", STATE_GET_READY, True
                elif state == STATE_GET_READY and not paused:
                    state = STATE_PLAYING
                    bird.flap()
                elif state == STATE_PLAYING and not paused:
                    bird.flap()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_START:
                    if start_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        fade_state, fade_target, fade_reset = "out", STATE_GET_READY, True
                    elif rate_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        rate_game()
                    elif leaderboard_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        lb_anim = 0
                        state = STATE_LEADERBOARD
                    elif music_rect.collidepoint(mouse_pos):
                        play_sound(SND_SWOOSH)
                        toggle_music()
                    elif sfx_rect.collidepoint(mouse_pos):
                        play_sound(SND_SWOOSH)
                        toggle_sfx()

                elif state == STATE_GET_READY:
                    if paused:
                        # Centered pause menu: resume (stay here) or menu (home)
                        if resume_center_button.is_clicked(mouse_pos):
                            play_sound(SND_SWOOSH)
                            paused = False
                        elif pause_menu_button.is_clicked(mouse_pos):
                            play_sound(SND_SWOOSH)
                            paused = False
                            fade_state, fade_target, fade_reset = "out", STATE_START, False
                    elif pause_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        paused = True
                    else:
                        play_sound(SND_SWOOSH)
                        state = STATE_PLAYING
                        bird.flap()

                elif state == STATE_PLAYING:
                    if paused:
                        if resume_corner_button.is_clicked(mouse_pos):
                            play_sound(SND_SWOOSH)
                            paused = False
                    elif pause_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        paused = True
                    else:
                        bird.flap()

                elif state == STATE_GAME_OVER:
                    if ok_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        fade_state, fade_target, fade_reset = "out", STATE_GET_READY, True
                    elif share_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        share_score(score)

                elif state == STATE_LEADERBOARD:
                    if menu_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        fade_state, fade_target, fade_reset = "out", STATE_START, False

        # ---------- Fade transition ----------
        if fade_state == "out":
            fade_alpha += FADE_SPEED
            if fade_alpha >= 255:
                fade_alpha = 255
                if fade_reset:
                    reset_game()
                if fade_target == STATE_START:
                    start_anim = 0  # replay the button slide-in on the start page
                state = fade_target
                fade_state = "in"
        elif fade_state == "in":
            fade_alpha -= FADE_SPEED
            if fade_alpha <= 0:
                fade_alpha = 0
                fade_state = None

        # ---------- Update ----------
        if state == STATE_PLAYING and not paused:
            bird.update()
            ground_offset += PIPE_SPEED

            if pipes[-1].x < WIDTH - 200:
                pipes.append(Pipe(WIDTH + 20))

            for pipe in pipes:
                pipe.update()

            pipes = [p for p in pipes if not p.off_screen()]

            bird_rect = bird.get_rect()
            hit = False
            for pipe in pipes:
                top, bottom = pipe.get_rects()
                if bird_rect.colliderect(top) or bird_rect.colliderect(bottom):
                    hit = True
                if not pipe.passed and pipe.x + PIPE_WIDTH < bird.x:
                    pipe.passed = True
                    score += 1
                    play_sound(SND_POINT)
                    if score % THEME_CHANGE_EVERY == 0:
                        advance_theme()

            if bird.y - bird.radius < 0 or bird.y + bird.radius > HEIGHT - GROUND_HEIGHT:
                hit = True

            if hit:
                play_sound(SND_HIT)
                play_sound(SND_DIE)
                prev_best = leaderboard[0] if leaderboard else 0
                leaderboard = save_score(score)
                last_rank = 1 + sum(1 for s in leaderboard if s > score)
                is_new_best = score > prev_best
                go_anim = 0
                state = STATE_GAME_OVER

        # ---------- Draw ----------
        draw_background()

        if state == STATE_START:
            # Title + the bird beside it hover together (same vertical bob).
            title_y = int(150 + math.sin(pygame.time.get_ticks() * 0.005) * 6)
            if TITLE_IMG:
                title_rect = TITLE_IMG.get_rect(midleft=(68, title_y))
                screen.blit(TITLE_IMG, title_rect)
                bird_x = title_rect.right + 28
            else:
                draw_text_center("Flappy Bird", font, ui_text_color(), title_y)
                bird_x = WIDTH // 2 + 120
            if BIRD_FRAMES:
                frame = BIRD_FRAMES[(pygame.time.get_ticks() // 150) % 3]
                bird_rect = frame.get_rect(center=(bird_x, title_y))
                screen.blit(frame, bird_rect)
            else:
                pygame.draw.circle(screen, YELLOW, (bird_x, title_y), 15)
                pygame.draw.circle(screen, BLACK, (bird_x, title_y), 15, 2)
            # Buttons slide up from the bottom into place when the page opens.
            start_anim = min(start_anim + 1, START_ANIM_FRAMES + 3 * START_BTN_STAGGER)
            start_button.draw(start_slide(start_anim, 0))
            leaderboard_button.draw(start_slide(start_anim, START_BTN_STAGGER))
            rate_button.draw(start_slide(start_anim, 2 * START_BTN_STAGGER))
            draw_audio_toggles(music_rect, sfx_rect)
            draw_ground(0)

        elif state == STATE_GET_READY:
            # "Get Ready!" banner on top, a bird to the left of the tap indicator below.
            if GET_READY_MSG_IMG:
                gr_rect = GET_READY_MSG_IMG.get_rect(center=(WIDTH // 2, 215))
                screen.blit(GET_READY_MSG_IMG, gr_rect)
            else:
                draw_text_center("Get Ready!", font, ui_text_color(), 215)
            if BIRD_FRAMES:
                gr_frame = BIRD_FRAMES[(pygame.time.get_ticks() // 150) % 3]
                screen.blit(gr_frame, gr_frame.get_rect(center=(105, 330)))
            if TAP_MSG_IMG:
                tap_rect = TAP_MSG_IMG.get_rect(center=(WIDTH // 2, 330))
                screen.blit(TAP_MSG_IMG, tap_rect)
            draw_ground(0)
            if paused:
                screen.blit(PAUSE_OVERLAY, (0, 0))
                resume_center_button.draw()
                pause_menu_button.draw()
            else:
                pause_button.draw()

        elif state == STATE_PLAYING:
            for pipe in pipes:
                pipe.draw()
            draw_ground(ground_offset)
            bird.draw()
            draw_score(score, 20)
            if paused:
                screen.blit(PAUSE_OVERLAY, (0, 0))
                resume_corner_button.draw()
            else:
                pause_button.draw()

        elif state == STATE_GAME_OVER:
            for pipe in pipes:
                pipe.draw()
            draw_ground(ground_offset)
            bird.draw()
            if GAME_OVER_IMG:
                game_over_rect = GAME_OVER_IMG.get_rect(center=(WIDTH // 2, HEIGHT // 2 - HEIGHT // 4))
                screen.blit(GAME_OVER_IMG, game_over_rect)
            else:
                draw_text_center("GAME OVER", font, ui_text_color(), 100)
            # Card + buttons slide up from the bottom (staggered).
            go_anim = min(go_anim + 1, START_ANIM_FRAMES + 3 * START_BTN_STAGGER)
            best = leaderboard[0] if leaderboard else score
            draw_score_card(WIDTH // 2, 300 + start_slide(go_anim, 0), score, best, last_rank, is_new_best)
            ok_button.draw(start_slide(go_anim, 2 * START_BTN_STAGGER))
            share_button.draw(start_slide(go_anim, 3 * START_BTN_STAGGER))

        elif state == STATE_LEADERBOARD:
            lb_anim = min(lb_anim + 1, LB_ANIM_CAP)
            # the base grows up to full height...
            grow = ease_out(lb_anim / LB_GROW_FRAMES)
            grass_top = LB_GRASS_START_Y + (LB_GRASS_TOP_Y - LB_GRASS_START_Y) * grow
            draw_leaderboard_ground(grass_top)
            # ...then the title and score records fall from the sky into the list
            draw_leaderboard_title(fall_y(LB_TITLE_TARGET_Y, LB_TITLE_START, lb_anim))
            if leaderboard:
                for i, s in enumerate(leaderboard):
                    target = LB_SCORE_TOP + i * LB_SCORE_PITCH
                    cy = fall_y(target, LB_ROWS_START + i * LB_ROW_STAGGER, lb_anim)
                    draw_leaderboard_row(i + 1, s, cy)
            elif lb_anim >= LB_ROWS_START:
                draw_text_center("No scores yet", small_font, BLACK, 300)
            if lb_anim >= LB_GROW_FRAMES:
                menu_button.draw()

        # Dark fade overlay (drawn last so it covers everything)
        if fade_alpha > 0:
            FADE_SURFACE.set_alpha(fade_alpha)
            screen.blit(FADE_SURFACE, (0, 0))

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
