#!/usr/bin/env python3
import asyncio
import logging
import os
import sys
from random import randint, choice

import pygame
import pygame.gfxdraw
from pygame.locals import *

logging.basicConfig(level=logging.WARNING)

# Пасхалочка
IDDQD = True

SIZE = WIDTH, HEIGHT = 1024, 768
BRICK_SIZE = 40, 20
HANDLE_SIZE = 160, 10
BALL_RADIUS = 5
BALL_SPEED = 300
LIVES = 5

# https://github.com/pygame/pygame/blob/main/src_py/colordict.py
WHITE = pygame.Color("white")
BLACK = pygame.Color("black")
RED = pygame.Color("red")
DARKRED = pygame.Color("darkred")
GREEN = pygame.Color("green")
BLUE = pygame.Color("blue")
YELLOW = pygame.Color("yellow")
BROWN = pygame.Color("brown")
MAGENTA = pygame.Color("magenta")
MAGENTA4 = pygame.Color("magenta4")
AQUAMARINE = pygame.Color('aquamarine')
DEEPSKYBLUUE = pygame.Color('deepskyblue')
DARKORANGE = pygame.Color('darkorange')
GRAY = pygame.Color("gray")
DARKGRAY = pygame.Color("darkgray")

BRICK_COLORS = {1: (WHITE, GRAY),
                2: (GREEN, DEEPSKYBLUUE),
                3: (YELLOW, DARKORANGE),
                4: (RED, MAGENTA),
                5: (DARKORANGE, AQUAMARINE)}

BALL_COLORS = YELLOW


pygame.init()
pygame.font.init()

sound_handle = pygame.mixer.Sound('sound/Arkanoid SFX (2).wav')
sound_brick_dead = pygame.mixer.Sound('sound/Arkanoid SFX (1).wav')
sound_spawn = pygame.mixer.Sound('sound/Arkanoid SFX (4).wav')
sound_brick_no_dead = pygame.mixer.Sound('sound/Arkanoid SFX (7).wav')
sound_game_over = pygame.mixer.Sound('sound/05_-_Arkanoid_-_ARC_-_Game_Over.ogg')
sound_game_start = pygame.mixer.Sound('sound/02_-_Arkanoid_-_ARC_-_Game_Start.ogg')
sound_next_level = pygame.mixer.Sound('sound/Arkanoid SFX (9).wav')

# pygame.mixer.music.load('sound/02_-_Arkanoid_-_ARC_-_Game_Start.ogg')
# pygame.mixer.music.play()

ioloop = asyncio.get_event_loop()


def load_image(name: str, colorkey=None):
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


class World:
    """
    Основное игровое поле
    """
    def __init__(self, screen) -> None:
        sound_game_start.play()
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.lives = LIVES
        self.level = 1
        self.score = 0
        self.bricks = []
        self.balls = []
        self.wall = None

        self.handle = Handle((WIDTH // 2 - HANDLE_SIZE[0] // 2, HEIGHT - HANDLE_SIZE[1] - 40))
        self.spawn_ball()
        self.map_generator()
        self.bonus = {0: lambda x=1: x,
                      1: self.bonus_add_wall,
                      2: self.bonus_add_lives,
                      3: self.bonus_add_balls,
                      4: self.bonus_next_level,
                      5: self.bonus_balls_increase_speed,
                      6: self.bonus_balls_decrease_speed,
                      }
        # Ну вы поняли :)
        if IDDQD:
            self.bonus_add_balls()
            self.bonus_add_balls()
            self.bonus_balls_increase_speed()
            self.bonus[0]()
            self.bonus_add_wall(lives=999)

    def map_generator(self) -> None:
        """
        Генератор карты. В зависимости от уровня меняется кол-во и тип кирпичей
        :return:
        """
        random_lives = []
        random_lives.extend([1] * 5)
        random_lives.extend([2] * self.level * 3)
        random_lives.extend([3] * self.level * 2)
        random_lives.extend([4] * self.level)
        print(random_lives)
        for x in range(0, 20):
            for y in range(1 + self.level if self.level < 11 else 10):
                lives = choice(random_lives)
                self.bricks.append(
                    Brick(((10 + (BRICK_SIZE[0] + 10) * x, 40 + (BRICK_SIZE[1] + 10) * y)),
                          lives=lives))

    def draw(self) -> None:
        self.handle.draw(self.screen)

        for brick in self.bricks:
            brick.draw(self.screen)

        for ball in self.balls:
            ball.draw(self.screen)

        self.text_draw()

    def text_draw(self) -> None:
        """
        Рисование жизней, очков и уровня на экране.
        Жизней больше 20 не рисует, но считает
        Если есть нижняя стенка то рисуем её жизни
        :return:
        """
        my_font = pygame.font.SysFont('Comic Sans MS', 14)
        lives_surface = my_font.render('LIVES:', False, MAGENTA4)
        score_surface = my_font.render(f'SCORE: {self.score:012d}', False, MAGENTA4)
        level_surface = my_font.render(f'LEVEL: {self.level:02d}', False, MAGENTA4)

        self.screen.blit(lives_surface, (WIDTH - 500, 5))
        self.screen.blit(score_surface, (WIDTH - 200, 5))
        self.screen.blit(level_surface, (10, 5))
        # жизни нижней стенки
        if any(True for brick in self.bricks if brick.w_size == WIDTH):
            lives = [brick for brick in self.bricks if brick.w_size == WIDTH][0].lives
            wall_surface = my_font.render(f'WALL LIVES: {lives}', False, DARKORANGE)
            self.screen.blit(wall_surface, (200, 5))

        for i in range(self.lives if self.lives < 21 else 20):
            pygame.gfxdraw.filled_circle(self.screen, WIDTH - (440 - i * 12), 15, 4, DARKORANGE)

    def update(self) -> None:
        time = self.clock.get_time()
        self.handle.update(time)
        for i in self.balls:
            i.update(time)
        # если мяч вылетел за пределы нижней линии то удаляем его
        for ball in self.balls:
            if ball.position[1] > HEIGHT:
                self.balls.remove(ball)
        # если все мячи кончились то -1 жизнь и добавляем мяч
        if not self.balls:
            self.handle = Handle((WIDTH // 2 - 30, HEIGHT - 10 - 40))
            self.spawn_ball()
            self.lives -= 1
            if self.lives < 1:
                self.game_over()
            return
        # проверяем столкновения с блоков с мячом
        new_bricks = []
        for brick in self.bricks:
            for ball in self.balls:
                if brick.is_inside(ball.position):
                    brick.check_collision(ball)
                    self.score += brick.lives * 100 if brick.lives < 5 else 0
                    brick.lives -= 1
                    wait_tasks = asyncio.wait([ioloop.create_task(brick.draw_destroy(self.screen))])
                    if brick.lives < 1:
                        sound_brick_dead.play()
                        ioloop.run_until_complete(wait_tasks)
                        # self.bonus_balls_decrease_speed()
                        break
                    sound_brick_no_dead.play()
                    ioloop.run_until_complete(wait_tasks)
            else:
                new_bricks.append(brick)
        # если кирпичи кончились генерируем новую карту и делаем новый уровень
        if not new_bricks or (len(new_bricks) <= 1 and any(True for brick in self.bricks if brick.w_size == WIDTH)):
            self.level += 1
            sound_next_level.play()
            self.map_generator()
            logging.warning(f'No bricks - next level {self.level}')
        else:
            self.bricks = new_bricks
        # проверяем столкновение мячей с ракеткой, если во время движения то меняем скорости мячей
        for ball in self.balls:
            if self.handle.is_inside(ball.position):
                self.handle.check_collision(ball)
                sound_handle.play()
                if pygame.key.get_pressed()[K_RIGHT]:
                    ball.speed[0] += 50

                if pygame.key.get_pressed()[K_LEFT]:
                    ball.speed[0] -= 50

    def tick(self):
        self.clock.tick(60)

    def spawn_ball(self):
        """
        Добавления мяча
        :return:
        """
        position = self.handle.position[:]
        position[0] += randint(15, 45)
        position[1] -= 5
        self.balls.append(Ball(position))
        sound_spawn.play()

    def game_over(self) -> None:
        """
        TODO: Надо написать
        Конец игры
        :return:
        """
        sound_game_over.play()
        logging.error('game over')

    def bonus_add_wall(self, lives=10):
        """
        Бонус добавляем нижнюю стенку с 10 жизнями
        :return:
        """
        self.score += 20000
        # если была то добавляем 10 жизней
        for brick in self.bricks:
            if brick.w_size == WIDTH:
                brick.lives += lives
                logging.warning(f'bonus_add_wall WALL add lives = {brick.lives}')
                return
        # иначе добавляем
        wall = Brick((0, HEIGHT-5), lives=lives)
        wall.bonus = 0
        wall.h_size = 5
        wall.w_size = WIDTH
        self.bricks.append(wall)
        logging.warning(f'bonus_add_wall add new WALL')

    def bonus_add_lives(self) -> None:
        """
        Бонус добавляет 3 жизни
        :return:
        """
        self.lives += 3
        self.score += 20000
        logging.warning(f'bonus_add_lives lives = {self.lives}')

    def bonus_add_balls(self):
        """
        Бонус + 3 шарика
        :return:
        """
        self.score += 20000
        for _ in range(3):
            self.spawn_ball()
        logging.warning(f'bonus_add_balls balls = {len(self.balls)}')

    def bonus_balls_increase_speed(self):
        """
        Бонус увеличение скорости
        :return:
        """
        self.score += 20000
        for ball in self.balls:
            if abs(ball.speed[0]) < 600 and abs(ball.speed[1]) < 600:
                ball.speed[0] *= 1.1
                ball.speed[1] *= 1.1
        logging.warning(f'bonus_balls_increase_speed')

    def bonus_balls_decrease_speed(self):
        """
        Бонус увеличение скорости
        :return:
        """
        self.score += 20000
        for ball in self.balls:
            if abs(ball.speed[0]) > 150 and abs(ball.speed[1]) > 150:
                ball.speed[0] *= 0.9
                ball.speed[1] *= 0.9
        logging.warning(f'bonus_balls_decrease_speed')

    def bonus_next_level(self) -> None:
        """
        Бонус переход на сл уровень
        :return:
        """
        self.score += 20000
        self.level += 1
        sound_next_level.play()
        logging.warning(f'bonus_next_level level = {self.level}')
        if any(True for brick in self.bricks if brick.w_size == WIDTH):
            self.bricks = []
            self.map_generator()
            self.bonus_add_wall()
            logging.warning(f'bonus_next_level with WALL')
        else:
            self.bricks = []
            self.map_generator()
            logging.warning(f'bonus_next_level with NO WALL')


class Brick:
    """
    Класс блоков
    """
    w_size = BRICK_SIZE[0]
    h_size = BRICK_SIZE[1]

    def __init__(self, position=None, lives=1):
        self.position = list(position)
        self.lives = lives
        self.color = BRICK_COLORS.get(lives, BRICK_COLORS[1])
        self.bonus = choice([[0] * 10, [1], [2], [3]])

    def draw(self, screen: pygame.Surface) -> None:
        """
        Рисование блока с градиентной заливкой и тенью.
        Рисуем Surface 2x2, пару линий в нем и растягиваем его до размеров блока.
        :param screen:
        :return:
        """
        self.color = BRICK_COLORS.get(self.lives, BRICK_COLORS[1])
        pygame.gfxdraw.box(screen, pygame.Rect((self.position[0] + 1, self.position[1] + 1),
                                               (self.w_size + 1, self.h_size + 1)), DARKGRAY)
        colour_rect = pygame.Surface((2, 2))
        pygame.draw.line(colour_rect, self.color[1], (0, 0), (0, 1))
        pygame.draw.line(colour_rect, self.color[0], (1, 0), (1, 1))
        colour_rect = pygame.transform.smoothscale(colour_rect, (self.w_size, self.h_size))
        screen.blit(colour_rect, self.position)

    async def draw_destroy(self, screen: pygame.Surface) -> None:
        """
        Эффект уменьшения жизней у блока или его смерти.
        Работает асинхронно, т.е. рисуется независимо от остального кода чтоб не подтормаживало игру.
        Если жизнь просто уменьшилась, отрисовывается рамка старого цвета вокруг блока
        Если смерть то отрисовывается красный цвет.
        :param screen:
        :return:
        """
        if self.lives < 1:
            pygame.gfxdraw.box(screen, pygame.Rect((self.position[0] - 10, self.position[1] - 10),
                                                   (self.w_size + 20, self.h_size + 20)), RED)
            pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), BLUE)
        else:
            pygame.gfxdraw.box(screen, pygame.Rect((self.position[0] - 10, self.position[1] - 10),
                                                   (self.w_size + 20, self.h_size + 20)), self.color[1])
            pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), BLUE)
        # await sleep(0.1)

    def is_inside_hbounds(self, x):
        left_bound = self.position[0] - BALL_RADIUS
        right_bound = self.position[0] + self.w_size + BALL_RADIUS
        return left_bound <= x <= right_bound

    def is_inside_vbounds(self, y):
        up_bound = self.position[1] - BALL_RADIUS
        down_bound = self.position[1] + self.h_size + BALL_RADIUS
        return up_bound <= y <= down_bound

    def is_inside(self, position):
        x, y = position
        return self.is_inside_hbounds(x) and self.is_inside_vbounds(y)

    def is_h_collide(self, x1, x2):
        return not self.is_inside_hbounds(x1) and self.is_inside_hbounds(x2)

    def is_v_collide(self, y1, y2):
        return not self.is_inside_vbounds(y1) and self.is_inside_vbounds(y2)

    def check_collision(self, ball):
        if self.is_h_collide(ball.prev_pos[0], ball.position[0]):
            ball.speed[0] *= -1
        if self.is_v_collide(ball.prev_pos[1], ball.position[1]):
            ball.speed[1] *= -1


class Handle(Brick):
    """
    Класс ракетки, в целом это тоже что и обычный блок и отличается одним методом
    """
    w_size = HANDLE_SIZE[0]
    h_size = HANDLE_SIZE[1]

    def __init__(self, position=None, lives=1):
        super(Handle, self).__init__(position, lives)
        self.bonus = 0

    def update(self, ticks):
        if pygame.key.get_pressed()[K_RIGHT] and self.position[0] < WIDTH - HANDLE_SIZE[0]:
            self.position[0] += int(500 * ticks / 1000)

        if pygame.key.get_pressed()[K_LEFT] and self.position[0] >= 0:
            self.position[0] -= int(500 * ticks / 1000)


class Ball:
    """
    Класс мяча
    Небольшой рандом в скоростях
    """
    def __init__(self, position, color=BALL_COLORS):
        self.position = list(position)
        self.color = color
        self.speed = [BALL_SPEED * choice([0.8, 0.9, 1, 1.1, 1.2]), -BALL_SPEED * choice([0.8, 0.9, 1, 1.1, 1.2])]
        self.prev_pos = self.position
        self.radius = BALL_RADIUS

    def draw(self, screen):
        pygame.gfxdraw.filled_circle(screen, int(self.position[0]), int(self.position[1]), self.radius, self.color)

    def update(self, ticks):
        self.prev_pos = self.position[:]

        if self.position[0] < self.radius or self.position[0] >= (WIDTH - self.radius):
            self.speed[0] *= -1

        if self.position[1] < self.radius:
            self.speed[1] *= -1

        for i in (0, 1):
            self.position[i] += self.speed[i] * ticks / 1000


def main():
    screen = pygame.display.set_mode(SIZE)
    world = World(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        screen.fill(BLACK)
        world.update()
        world.draw()
        world.tick()
        pygame.display.flip()


if __name__ == '__main__':
    main()
