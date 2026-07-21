import pygame
import random
import sys
import os
import json

pygame.init()
pygame.mixer.init()

WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_GAP = 150
PIPE_WIDTH = 60
PIPE_SPEED = 3
GROUND_HEIGHT = 80
MAX_LEADERBOARD_ENTRIES = 5

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
YELLOW = (255, 220, 0)
BLACK = (0, 0, 0)
BLUE = (135, 206, 235)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
pygame.display.set_icon(pygame.image.load(os.path.join(os.path.dirname(__file__), "assets", "bird_mid.png")))
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 32)
button_font = pygame.font.SysFont(None, 36)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_SUBFOLDER = "assets"  # <-- change this if your folder has a different name
ASSET_DIR = os.path.join(SCRIPT_DIR, ASSET_SUBFOLDER)
LEADERBOARD_PATH = os.path.join(SCRIPT_DIR, "leaderboard.json")

# Game states
STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_LEADERBOARD = "leaderboard"


def load_image(filename):
    """Load an image if it exists, otherwise return None (fallback to shapes)."""
    path = os.path.join(ASSET_DIR, filename)
    if not os.path.exists(path):
        print(f"[warning] missing asset: {path}")
        return None
    return pygame.image.load(path).convert_alpha()


def load_sound(filename):
    path = os.path.join(ASSET_DIR, filename)
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


# ---------- Load assets ----------

# Bird flap animation (3 frames)
BIRD_FRAMES = [
    scale_to_width(load_image("bird_up.png"), 40),
    scale_to_width(load_image("bird_mid.png"), 40),
    scale_to_width(load_image("bird_down.png"), 40),
]
if BIRD_FRAMES[0] is None:
    BIRD_FRAMES = None

# Pipe: cap (the rim) + a tileable body strip, scaled to PIPE_WIDTH,
# then the body strip is repeated to reach whatever length each pipe needs
PIPE_CAP_IMG = scale_to_width(load_image("pipe_cap.png"), PIPE_WIDTH)
PIPE_BODY_IMG = scale_to_width(load_image("pipe_body.png"), PIPE_WIDTH)
PIPE_CAP_IMG_FLIPPED = pygame.transform.flip(PIPE_CAP_IMG, False, True) if PIPE_CAP_IMG else None

# Background (sky) stretched to fill the screen
BG_IMG = None
_bg_raw = load_image("background-day.png")
if _bg_raw:
    BG_IMG = pygame.transform.smoothscale(_bg_raw, (WIDTH, HEIGHT))

# Scrolling ground strip
GROUND_IMG = scale_to_height(load_image("base.png"), GROUND_HEIGHT)

# Score digits (sprite font)
DIGIT_IMGS = None
_digits_raw = [load_image(f"digit_{i}.png") for i in range(10)]
if all(d is not None for d in _digits_raw):
    DIGIT_IMGS = [scale_to_height(d, 36) for d in _digits_raw]

# Menu art: title logo + custom Start/Leaderboard button images
TITLE_IMG = scale_to_width(load_image("flappybird.png"), 280)
MESSAGE_IMG = scale_to_width(load_image("message.png"), 280)
GAME_OVER_IMG = scale_to_width(load_image("gameover.png"), 280)
PLAY_BUTTON_IMG = scale_to_width(load_image("play_button.png"), 180)
LEADERBOARD_BUTTON_IMG = scale_to_width(load_image("leaderboard_button.png"), 180)

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
        self.x = WIDTH // 2
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


def main():
    state = STATE_MENU
    bird = Bird()
    pipes = [Pipe(WIDTH + 100)]
    score = 0
    leaderboard = load_leaderboard()
    ground_offset = 0

    # Menu buttons (use custom images if available, otherwise drawn rectangles)
    start_button = Button(WIDTH // 2, 350, 180, 50, "Start", image=PLAY_BUTTON_IMG)

    # Leaderboard screen button
    back_button = Button(WIDTH // 2, 450, 180, 50, "Back", image=PLAY_BUTTON_IMG)

    # Game over buttons
    retry_button = Button(WIDTH // 2,350, 180, 50, "Retry", image=PLAY_BUTTON_IMG)
    leaderboard_button_game_over = Button(WIDTH // 2, 450, 180, 50,"Leaderboard", image=LEADERBOARD_BUTTON_IMG)

    def reset_game():
        nonlocal bird, pipes, score
        bird = Bird()
        pipes = [Pipe(WIDTH + 100)]
        score = 0

    while True:
        mouse_pos = pygame.mouse.get_pos()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN and event.key == pygame.K_SPACE:
                if state == STATE_MENU:
                        play_sound(SND_SWOOSH)
                        reset_game()
                        state = STATE_PLAYING
                if state == STATE_PLAYING:
                    bird.flap()
                elif state == STATE_GAME_OVER:
                    reset_game()
                    state = STATE_PLAYING

            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_MENU:
                        play_sound(SND_SWOOSH)
                        reset_game()
                        state = STATE_PLAYING
                
                elif state == STATE_PLAYING:
                    bird.flap()

                elif state == STATE_GAME_OVER:
                    if retry_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        reset_game()
                        state = STATE_PLAYING
                    elif leaderboard_button_game_over.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        state = STATE_LEADERBOARD

                elif state == STATE_LEADERBOARD:
                    if back_button.is_clicked(mouse_pos):
                        play_sound(SND_SWOOSH)
                        state = STATE_MENU

        # ---------- Update ----------
        if state == STATE_PLAYING:
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

            if bird.y - bird.radius < 0 or bird.y + bird.radius > HEIGHT - GROUND_HEIGHT:
                hit = True

            if hit:
                play_sound(SND_HIT)
                play_sound(SND_DIE)
                leaderboard = save_score(score)
                state = STATE_GAME_OVER

        # ---------- Draw ----------
        draw_background()

        if state == STATE_MENU:
            if TITLE_IMG:
                title_rect = TITLE_IMG.get_rect(center=(WIDTH // 2, HEIGHT // 4 ))
                screen.blit(TITLE_IMG, title_rect)
            else:
                draw_text_center("Flappy Bird", font, BLACK, HEIGHT // 4)
            if MESSAGE_IMG:
                MESSAGE_rect = MESSAGE_IMG.get_rect(center=(WIDTH // 2, HEIGHT // 2))
                screen.blit(MESSAGE_IMG, MESSAGE_rect)
            draw_ground(0)

        elif state == STATE_PLAYING:
            for pipe in pipes:
                pipe.draw()
            draw_ground(ground_offset)
            bird.draw()
            draw_score(score, 20)

        elif state == STATE_GAME_OVER:
            for pipe in pipes:
                pipe.draw()
            draw_ground(ground_offset)
            bird.draw()
            if GAME_OVER_IMG:
                game_over_rect = GAME_OVER_IMG.get_rect(center=(WIDTH // 2, HEIGHT // 2 - HEIGHT // 4))
                screen.blit(GAME_OVER_IMG, game_over_rect)
            else:
                draw_text_center("GAME OVER", font, BLACK, 100)
            draw_text_center(f"Score: {score}", small_font, BLACK, HEIGHT // 2 - HEIGHT // 10)
            retry_button.draw()
            leaderboard_button_game_over.draw()

        elif state == STATE_LEADERBOARD:
            draw_text_center("Leaderboard", font, BLACK, 80)
            if leaderboard:
                for i, s in enumerate(leaderboard):
                    draw_text_center(f"{i + 1}.  {s}", small_font, BLACK, 160 + i * 45)
            else:
                draw_text_center("No scores yet", small_font, BLACK, 200)
            back_button.draw()
            draw_ground(0)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
