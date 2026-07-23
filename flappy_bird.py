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

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_SUBFOLDER = "assets"  # <-- change this if your folder has a different name
ASSET_DIR = os.path.join(SCRIPT_DIR, ASSET_SUBFOLDER)
SPRITE_DIR = os.path.join(ASSET_DIR, "sprites")  # all .png images live here
SOUND_DIR = os.path.join(ASSET_DIR, "sounds")    # all .wav sounds live here
LEADERBOARD_PATH = os.path.join(SCRIPT_DIR, "leaderboard.json")

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


def play_sound(sound):
    if sound:
        sound.play()


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

# Sound effects
SND_WING = load_sound("wing.wav")
SND_POINT = load_sound("point.wav")
SND_HIT = load_sound("hit.wav")
SND_DIE = load_sound("die.wav")
SND_SWOOSH = load_sound("swoosh.wav")


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

    def draw(self):
        if self.image:
            screen.blit(self.image, self.rect)
        else:
            mouse_pos = pygame.mouse.get_pos()
            is_hover = self.rect.collidepoint(mouse_pos)
            pygame.draw.rect(screen, self.hover_color if is_hover else self.color, self.rect, border_radius=8)
            pygame.draw.rect(screen, BLACK, self.rect, 2, border_radius=8)
            text_surf = button_font.render(self.text, True, WHITE)
            text_rect = text_surf.get_rect(center=self.rect.center)
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


# ---------- Leaderboard page ----------

LB_SCORE_TOP = 205    # y-center of the first score row
LB_SCORE_PITCH = 29   # vertical spacing between rows


def draw_leaderboard_ground():
    """Tall base: the grass strip near the top, plain tan filled down to the bottom."""
    if LB_BASE_IMG:
        screen.blit(LB_BASE_IMG, (0, LB_GRASS_TOP_Y))
        base_bottom = LB_GRASS_TOP_Y + LB_BASE_IMG.get_height()
    else:
        base_bottom = LB_GRASS_TOP_Y
    if base_bottom < HEIGHT:
        pygame.draw.rect(screen, TAN_COLOR, (0, base_bottom, WIDTH, HEIGHT - base_bottom))


def draw_leaderboard_row(rank, score, cy):
    """Rank (right-aligned) . score (left-aligned) drawn with the white mid-digit sprites."""
    if not DIGIT_MID_IMGS:
        draw_text_center(f"{rank}.  {score}", small_font, BLACK, cy)
        return
    baseline = cy + MID_DIGIT_H // 2  # digits and the dot rest their bottoms here
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


def main():
    state = STATE_START
    paused = False
    bird = Bird()
    pipes = [Pipe(WIDTH + 100)]
    score = 0
    leaderboard = load_leaderboard()
    ground_offset = 0

    # Start (home) page buttons:
    #   big PLAY button in the middle, LEADERBOARD + RATE in a row beneath it.
    start_button = Button(WIDTH // 2, 300, 165, 97, "Start", image=START_PLAY_BTN_IMG)
    leaderboard_button = Button(141, 430, 88, 52, "Leaderboard", image=LEADERBOARD_BTN_IMG)
    rate_button = Button(258, 430, 93, 52, "Rate", image=RATE_BTN_IMG)

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

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if state == STATE_START:
                    play_sound(SND_SWOOSH)
                    reset_game()
                    state = STATE_GET_READY
                elif state == STATE_GET_READY and not paused:
                    state = STATE_PLAYING
                    bird.flap()
                elif state == STATE_PLAYING and not paused:
                    bird.flap()

            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_START:
                    if start_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        reset_game()
                        state = STATE_GET_READY
                    elif rate_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        rate_game()
                    elif leaderboard_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        state = STATE_LEADERBOARD

                elif state == STATE_GET_READY:
                    if paused:
                        # Centered pause menu: resume (stay here) or menu (home)
                        if resume_center_button.is_clicked(mouse_pos):
                            play_sound(SND_SWOOSH)
                            paused = False
                        elif pause_menu_button.is_clicked(mouse_pos):
                            play_sound(SND_SWOOSH)
                            paused = False
                            state = STATE_START
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
                        reset_game()
                        state = STATE_GET_READY
                    elif share_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        share_score(score)

                elif state == STATE_LEADERBOARD:
                    if menu_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        state = STATE_START

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
                leaderboard = save_score(score)
                state = STATE_GAME_OVER

        # ---------- Draw ----------
        draw_background()

        if state == STATE_START:
            # Title with the yellow bird perched beside it, then the buttons.
            title_y = 150
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
            start_button.draw()
            leaderboard_button.draw()
            rate_button.draw()
            draw_ground(0)

        elif state == STATE_GET_READY:
            # "Get Ready!" banner on top, tap indicator below (same spot as the
            # old combined message art).
            if GET_READY_MSG_IMG:
                gr_rect = GET_READY_MSG_IMG.get_rect(center=(WIDTH // 2, 215))
                screen.blit(GET_READY_MSG_IMG, gr_rect)
            else:
                draw_text_center("Get Ready!", font, ui_text_color(), 215)
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
            draw_text_center(f"Score: {score}", small_font, ui_text_color(), HEIGHT // 2 - HEIGHT // 10)
            ok_button.draw()
            share_button.draw()

        elif state == STATE_LEADERBOARD:
            draw_leaderboard_ground()
            draw_text_center("Leaderboard", font, ui_text_color(), 80)
            if leaderboard:
                for i, s in enumerate(leaderboard):
                    draw_leaderboard_row(i + 1, s, LB_SCORE_TOP + i * LB_SCORE_PITCH)
            else:
                draw_text_center("No scores yet", small_font, BLACK, 300)
            menu_button.draw()

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
