import os
import sys

import pygame
from pygame.locals import *
import pygame.gfxdraw

TARGET_FPS = 60
BLACK = pygame.Color("black")
WHITE = pygame.Color("white")
RED = pygame.Color("red")
YELLOW = pygame.Color("yellow")
GRAY = pygame.Color("gray")
BRICK_SIZE = 60, 20
HANDLE_SIZE = 80, 20
WINDOW_SIZE = WIDTH, HEIGHT = 980, 700

pygame.init()

screen = pygame.display.set_mode(WINDOW_SIZE)
clock = pygame.time.Clock()

pygame.mixer.music.load('sound/02_-_Arkanoid_-_ARC_-_Game_Start.ogg')
pygame.mixer.music.play()

sound1 = pygame.mixer.Sound('sound/Arkanoid SFX (2).wav')
sound2 = pygame.mixer.Sound('sound/Arkanoid SFX (1).wav')
sound3 = pygame.mixer.Sound('sound/Arkanoid SFX (4).wav')


def load_image(name, colorkey=None):
    fullname = os.path.join('data', name)
    #  если файл не существует, то выходим
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((0, 0))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


class Ball(pygame.sprite.Sprite):
    def __init__(self, radius, x, y, color=RED):
        super().__init__(all_sprites)
        self.radius = radius
        self.image = pygame.Surface((2 * radius, 2 * radius),
                                    pygame.SRCALPHA, 32)
        # pygame.draw.circle(self.image, color,
        #                    (radius, radius), radius)
        pygame.gfxdraw.filled_circle(self.image, radius, radius, radius, color)
        self.rect = pygame.Rect(x, y, 2 * radius, 2 * radius)
        self.vx = -5
        self.vy = -5

    # движение с проверкой столкновение шара
    def update(self):
        """
        TODO: move spritecollide to Brick
        """
        self.rect = self.rect.move(self.vy, self.vx)
        # self.rect.move_ip(self.vx, self.vy)
        if pygame.sprite.spritecollideany(self, horizontal_borders):
            self.vx = -self.vx
        if pygame.sprite.spritecollideany(self, vertical_borders):
            self.vy = -self.vy
        if pygame.sprite.spritecollide(self, bricks, True):
            self.vx = -self.vx
            sound2.play()
        if pygame.sprite.spritecollideany(self, handle):
            self.vx = -self.vx
            sound1.play()


class Border(pygame.sprite.Sprite):
    # строго вертикальный или строго горизонтальный отрезок
    def __init__(self, x1, y1, x2, y2):
        super().__init__(all_sprites)
        if x1 == x2:  # вертикальная стенка
            self.add(vertical_borders)
            self.image = pygame.Surface([1, y2 - y1])
            self.rect = pygame.Rect(x1, y1, 1, y2 - y1)
        else:  # горизонтальная стенка
            self.add(horizontal_borders)
            self.image = pygame.Surface([x2 - x1, 1])
            self.rect = pygame.Rect(x1, y1, x2 - x1, 1)


class Brick(pygame.sprite.Sprite):
    def __init__(self, position: tuple, size: tuple = BRICK_SIZE, color=WHITE):
        super().__init__(all_sprites)
        self.position = list(position)
        self.size = size
        self.image = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        self.image.fill(GRAY)
        self.rect = pygame.Rect(*self.position, *self.size)
        pygame.draw.rect(self.image, color, (1, 1, self.size[0] - 2, self.size[1] - 2))
        self.add(bricks)


class Handle(pygame.sprite.Sprite):
    def __init__(self, position: tuple, size: tuple = HANDLE_SIZE, color=YELLOW):
        super().__init__(all_sprites)
        self.position = list(position)
        self.size = size
        self.image = pygame.Surface(self.size, pygame.SRCALPHA, 32)
        self.image.fill(GRAY)
        self.rect = pygame.Rect(*self.position, *self.size)
        pygame.draw.rect(self.image, color, (1, 1, self.size[0] - 2, self.size[1] - 2))
        self.add(handle)

    def update(self):
        if pygame.key.get_pressed()[K_RIGHT] and 0 <= self.rect[0] < WIDTH - HANDLE_SIZE[0]:
            self.rect.move_ip(5, 0)
        if pygame.key.get_pressed()[K_LEFT] and 0 // 2 < self.rect[0] <= WIDTH - HANDLE_SIZE[0]:
            self.rect.move_ip(-5, 0)


# группа, содержащая все спрайты
all_sprites = pygame.sprite.Group()
# горизонтальные стенки
horizontal_borders = pygame.sprite.Group()
# вертикальные стенки
vertical_borders = pygame.sprite.Group()
# кирпичи
bricks = pygame.sprite.Group()
# ракетка
handle = pygame.sprite.Group()

Border(5, 5, WIDTH - 5, 5)
Border(5, HEIGHT - 5, WIDTH - 5, HEIGHT - 5)
Border(5, 5, 5, HEIGHT - 5)
Border(WIDTH - 5, 5, WIDTH - 5, HEIGHT - 5)

Ball(10, WIDTH // 2, HEIGHT - BRICK_SIZE[1] * 2)
Handle((WIDTH // 2 - 30, HEIGHT - 30))

for w in range(5, WIDTH, BRICK_SIZE[0] + 5):
    for h in range(50, 150, BRICK_SIZE[1] + 5):
        Brick((w, h))


clock = pygame.time.Clock()

running = True
while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    screen.fill(BLACK)
    all_sprites.draw(screen)
    all_sprites.update()
    pygame.display.flip()

    clock.tick(TARGET_FPS)
pygame.quit()
