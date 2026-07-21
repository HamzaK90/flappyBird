import pygame
import random
import sys
import os

pygame.init()

WIDTH, HEIGHT = 400, 600
GRAVITY = 0.5
FLAP_STRENGTH = -8
PIPE_GAP = 150
PIPE_WIDTH = 60
PIPE_SPEED = 3

WHITE = (255, 255, 255)
GREEN = (0, 200, 0)
YELLOW = (255, 220, 0)
BLACK = (0, 0, 0)
BLUE = (135, 206, 235)

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Flappy Bird")
clock = pygame.time.Clock()
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 32)

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
ASSET_SUBFOLDER = "assets"
ASSET_DIR = os.path.join(SCRIPT_DIR, ASSET_SUBFOLDER)


def load_image(filename):
    """Load an image if it exists, otherwise return None (fallback to shapes)."""
    path = os.path.join(ASSET_DIR, filename)
    if not os.path.exists(path):
        print(f"[warning] missing asset: {path}")
        return None
    return pygame.image.load(path).convert_alpha()


def scale_to_width(img, target_width):
    """Scale preserving aspect ratio, driven by width."""
    if img is None:
        return None
    ratio = target_width / img.get_width()
    target_height = int(img.get_height() * ratio)
    return pygame.transform.smoothscale(img, (target_width, target_height))


# Bird: scale preserving its natural aspect ratio (no stretching/squishing)
BIRD_IMG = scale_to_width(load_image("bird.png"), 40)

# Pipe: cap (the rim) + a tileable body strip, scaled to PIPE_WIDTH,
# then the body strip is repeated to reach whatever length each pipe needs
PIPE_CAP_IMG = scale_to_width(load_image("pipe_cap.png"), PIPE_WIDTH)
PIPE_BODY_IMG = scale_to_width(load_image("pipe_body.png"), PIPE_WIDTH)
PIPE_CAP_IMG_FLIPPED = pygame.transform.flip(PIPE_CAP_IMG, False, True) if PIPE_CAP_IMG else None

BG_IMG = None
_bg_raw = load_image("backGround.png")
if _bg_raw:
    BG_IMG = pygame.transform.smoothscale(_bg_raw, (WIDTH, HEIGHT))


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
    bird = Bird()
    pipes = [Pipe(WIDTH + 100)]
    score = 0
    game_over = False

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    if game_over:
                        bird = Bird()
                        pipes = [Pipe(WIDTH + 100)]
                        score = 0
                        game_over = False
                    else:
                        bird.flap()
            if event.type == pygame.MOUSEBUTTONDOWN:
                if game_over:
                    bird = Bird()
                    pipes = [Pipe(WIDTH + 100)]
                    score = 0
                    game_over = False
                else:
                    bird.flap()

        if not game_over:
            bird.update()

            if pipes[-1].x < WIDTH - 200:
                pipes.append(Pipe(WIDTH + 20))

            for pipe in pipes:
                pipe.update()

            pipes = [p for p in pipes if not p.off_screen()]

            bird_rect = bird.get_rect()
            for pipe in pipes:
                top, bottom = pipe.get_rects()
                if bird_rect.colliderect(top) or bird_rect.colliderect(bottom):
                    game_over = True
                if not pipe.passed and pipe.x + PIPE_WIDTH < bird.x:
                    pipe.passed = True
                    score += 1

            if bird.y - bird.radius < 0 or bird.y + bird.radius > HEIGHT:
                game_over = True

        draw_background()
        for pipe in pipes:
            pipe.draw()
        bird.draw()

        score_surf = small_font.render(str(score), True, WHITE)
        screen.blit(score_surf, (WIDTH // 2 - 10, 20))

        if game_over:
            draw_text_center("GAME OVER", font, BLACK, HEIGHT // 2 - 30)
            draw_text_center("Press SPACE to restart", small_font, BLACK, HEIGHT // 2 + 10)

        pygame.display.flip()
        clock.tick(60)


if __name__ == "__main__":
    main()
