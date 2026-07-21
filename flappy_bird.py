import pygame
import random
import sys
import os
import json

pygame.init()

WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_GAP = 150
PIPE_WIDTH = 60
PIPE_SPEED = 3
MAX_LEADERBOARD_ENTRIES = 5

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
DARK_GREEN = (0, 150, 0)
YELLOW = (255, 220, 0)
BLACK = (0, 0, 0)
BLUE = (135, 206, 235)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 32)
button_font = pygame.font.SysFont(None, 36)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_SUBFOLDER = "assets"
ASSET_DIR = os.path.join(SCRIPT_DIR, ASSET_SUBFOLDER)
LEADERBOARD_PATH = os.path.join(SCRIPT_DIR, "leaderboard.json")

STATE_MENU = "menu"
STATE_PLAYING = "playing"
STATE_GAME_OVER = "game_over"
STATE_LEADERBOARD = "leaderboard"


def load_image(filename):
    path = os.path.join(ASSET_DIR, filename)
    if not os.path.exists(path):
        print(f"[warning] missing asset: {path}")
        return None
    return pygame.image.load(path).convert_alpha()


def scale_to_width(img, target_width):
    if img is None:
        return None
    ratio = target_width / img.get_width()
    target_height = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (target_width, target_height))


BIRD_IMG = scale_to_width(load_image("bird.png"), 40)
PIPE_CAP_IMG = scale_to_width(load_image("pipe_cap.png"), PIPE_WIDTH)
PIPE_BODY_IMG = scale_to_width(load_image("pipe_body.png"), PIPE_WIDTH)
PIPE_CAP_IMG_FLIPPED = pygame.transform.flip(PIPE_CAP_IMG, False, True) if PIPE_CAP_IMG else None

BG_IMG = None
_bg_raw = load_image("backGround.png")
if _bg_raw:
    BG_IMG = pygame.transform.smoothscale(_bg_raw, (WIDTH, HEIGHT))

# Menu art: title logo + custom Start/Leaderboard button images
TITLE_IMG = scale_to_width(load_image("title.png"), 280)
PLAY_BUTTON_IMG = scale_to_width(load_image("play_button.png"), 180)
LEADERBOARD_BUTTON_IMG = scale_to_width(load_image("leaderboard_button.png"), 180)


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


class Button:
    def __init__(self, x, y, width, height, text, color=GREEN, hover_color=DARK_GREEN, image=None):
        self.text = text
        self.color = color
        self.hover_color = hover_color
        self.image = image
        if image:
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
        self.x = 80
        self.y = HEIGHT // 2
        self.velocity = 0
        self.radius = 15

    def flap(self):
        self.velocity = FLAP_STRENGTH

    def update(self):
        self.velocity += GRAVITY
        self.y += self.velocity

    def draw(self):
        if BIRD_IMG:
            angle = max(-25, min(90, -self.velocity * 5))
            rotated = pygame.transform.rotate(BIRD_IMG, angle)
            rect = rotated.get_rect(center=(self.x, int(self.y)))
            screen.blit(rotated, rect)
        else:
            pygame.draw.circle(screen, YELLOW, (self.x, int(self.y)), self.radius)
            pygame.draw.circle(screen, BLACK, (self.x, int(self.y)), self.radius, 2)

    def get_rect(self):
        return pygame.Rect(self.x - self.radius + 4, self.y - self.radius + 4,
                            (self.radius - 4) * 2, (self.radius - 4) * 2)


class Pipe:
    def __init__(self, x):
        self.x = x
        self.height = random.randint(80, HEIGHT - 80 - PIPE_GAP)
        self.passed = False

    def update(self):
        self.x -= PIPE_SPEED

    def _draw_column(self, top_y, bottom_y, cap_img, cap_at_bottom):
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
        if PIPE_CAP_IMG and PIPE_BODY_IMG:
            self._draw_column(0, self.height, PIPE_CAP_IMG_FLIPPED, cap_at_bottom=True)
            self._draw_column(self.height + PIPE_GAP, HEIGHT, PIPE_CAP_IMG, cap_at_bottom=False)
        else:
            pygame.draw.rect(screen, GREEN, (self.x, 0, PIPE_WIDTH, self.height))
            pygame.draw.rect(screen, GREEN, (self.x, self.height + PIPE_GAP,
                                              PIPE_WIDTH, HEIGHT - self.height - PIPE_GAP))

    def get_rects(self):
        top = pygame.Rect(self.x, 0, PIPE_WIDTH, self.height)
        bottom = pygame.Rect(self.x, self.height + PIPE_GAP,
                              PIPE_WIDTH, HEIGHT - self.height - PIPE_GAP)
        return top, bottom

    def off_screen(self):
        return self.x + PIPE_WIDTH < 0


def draw_background():
    if BG_IMG:
        screen.blit(BG_IMG, (0, 0))
    else:
        screen.fill(BLUE)


def draw_text_center(text, font_obj, color, y):
    surf = font_obj.render(text, True, color)
    rect = surf.get_rect(center=(WIDTH // 2, y))
    screen.blit(surf, rect)


def main():
    state = STATE_MENU
    bird = Bird()
    pipes = [Pipe(WIDTH + 100)]
    score = 0
    leaderboard = load_leaderboard()

    start_button = Button(WIDTH // 2, 350, 180, 50, "Start", image=PLAY_BUTTON_IMG)
    leaderboard_button = Button(WIDTH // 2, 440, 180, 50, "Leaderboard", image=LEADERBOARD_BUTTON_IMG)
    back_button = Button(WIDTH // 2, HEIGHT - 65, 180, 50, "Back")
    retry_button = Button(WIDTH // 2, HEIGHT // 2 + 65, 180, 50, "Retry")
    menu_button = Button(WIDTH // 2, HEIGHT // 2 + 125, 180, 50, "Menu")

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
                if state == STATE_PLAYING:
                    bird.flap()
                elif state == STATE_GAME_OVER:
                    reset_game()
                    state = STATE_PLAYING

            if event.type == pygame.MOUSEBUTTONDOWN:
                if state == STATE_MENU:
                    if start_button.is_clicked(mouse_pos):
                        reset_game()
                        state = STATE_PLAYING
                    elif leaderboard_button.is_clicked(mouse_pos):
                        leaderboard = load_leaderboard()
                        state = STATE_LEADERBOARD

                elif state == STATE_PLAYING:
                    bird.flap()

                elif state == STATE_GAME_OVER:
                    if retry_button.is_clicked(mouse_pos):
                        reset_game()
                        state = STATE_PLAYING
                    elif menu_button.is_clicked(mouse_pos):
                        state = STATE_MENU

                elif state == STATE_LEADERBOARD:
                    if back_button.is_clicked(mouse_pos):
                        state = STATE_MENU

        if state == STATE_PLAYING:
            bird.update()

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

            if bird.y - bird.radius < 0 or bird.y + bird.radius > HEIGHT:
                hit = True

            if hit:
                leaderboard = save_score(score)
                state = STATE_GAME_OVER

        draw_background()

        if state == STATE_MENU:
            if TITLE_IMG:
                title_rect = TITLE_IMG.get_rect(center=(WIDTH // 2, 180))
                screen.blit(TITLE_IMG, title_rect)
            else:
                draw_text_center("Flappy Bird", font, BLACK, 180)
            start_button.draw()
            leaderboard_button.draw()

        elif state == STATE_PLAYING:
            for pipe in pipes:
                pipe.draw()
            bird.draw()
            score_surf = small_font.render(str(score), True, WHITE)
            screen.blit(score_surf, (WIDTH // 2 - 10, 20))

        elif state == STATE_GAME_OVER:
            for pipe in pipes:
                pipe.draw()
            bird.draw()
            draw_text_center("GAME OVER", font, BLACK, HEIGHT // 2 - 60)
            draw_text_center(f"Score: {score}", small_font, BLACK, HEIGHT // 2 - 15)
            retry_button.draw()
            menu_button.draw()

        elif state == STATE_LEADERBOARD:
            draw_text_center("Leaderboard", font, BLACK, 80)
            if leaderboard:
                for i, s in enumerate(leaderboard):
                    draw_text_center(f"{i + 1}.  {s}", small_font, BLACK, 160 + i * 45)
            else:
                draw_text_center("No scores yet", small_font, BLACK, 200)
            back_button.draw()

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
