#!/usr/bin/env python3
import asyncio
import logging
import os
import pickle
import sys
from random import randint, choice
from time import sleep
from typing import List, Any

import pygame
import pygame.gfxdraw
import pygame_menu
from pygame.locals import *

logging.basicConfig(level=logging.ERROR)

SIZE = WIDTH, HEIGHT = 1024, 768
BRICK_SIZE = 40, 20
HANDLE_SIZE = 160, 10
HANDLE_BONUS_TIME = 20000
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
DEEPSKYBLUE = pygame.Color('deepskyblue')
DARKORANGE = pygame.Color('darkorange')
DARKGREEN = pygame.Color('darkgreen')
ORANGE = pygame.Color('orange')
GRAY = pygame.Color("gray")
DARKGRAY = pygame.Color("darkgray")

BRICK_COLORS = {1: (WHITE, GRAY),
                2: (GREEN, DEEPSKYBLUE),
                3: (YELLOW, DARKORANGE),
                4: (RED, MAGENTA),
                5: (BLUE, YELLOW)}

BALL_COLORS = YELLOW

user_name = 'Vasya Pupkin'

# Пасхалочка включается в меню
IDDQD = False

pygame.init()
pygame.display.set_caption('ARCANOID')
pygame.font.init()

# для асинхронной отрисовки эффектов
ioloop = asyncio.get_event_loop()


def sound_load(sound_path: str = 'resource/sound') -> dict:
    # TODO: Не запускается на компьютерах без звука! Надеюсь таких не будет.
    """Загружает словарь звуков"""
    sound_files = [f for f in os.listdir(sound_path) if os.path.isfile(os.path.join(sound_path, f))]
    return {file_name.split('.')[0]: pygame.mixer.Sound(os.path.join(sound_path, file_name)) for file_name in
            sound_files}


# чтоб не мучатся с пробросом звуков делаем глобально
sounds = sound_load()


def load_image(name: str, colorkey=None):
    fullname = os.path.join('resource', 'img', name)
    #  если файл не существует, то выходим
    if not os.path.isfile(fullname):
        print(f"Файл с изображением '{fullname}' не найден")
        sys.exit()
    image = pygame.image.load(fullname)
    if colorkey is not None:
        image = image.convert()
        if colorkey == -1:
            colorkey = image.get_at((1, 1))
        image.set_colorkey(colorkey)
    else:
        image = image.convert_alpha()
    return image


class World:
    """
    Основное игровое поле
    """
    def __init__(self, screen) -> None:
        sounds['sound_game_start'].play()
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.lives = LIVES
        self.level = 1
        self.score = 0
        self.bricks = []
        self.balls = []
        self.bonuses = []
        self.start = True
        self.handle = Handle((WIDTH // 2 - HANDLE_SIZE[0] // 2, HEIGHT - HANDLE_SIZE[1] - 40))
        self.over = None
        self.spawn_ball()
        self.map_generator()
        self.bonus = {0: lambda x=1: x,
                      1: self.bonus_add_wall,
                      2: self.bonus_add_lives,
                      3: self.bonus_add_balls,
                      4: self.bonus_next_level,
                      5: self.bonus_balls_increase_speed,
                      6: self.bonus_balls_decrease_speed,
                      7: self.bonus_handle_decrease,
                      8: self.bonus_handle_increase,
                      }
        # Ну вы поняли :)
        if IDDQD:
            for i in range(1, 9):
                self.bonuses.append(Bonus(bonus_id=i, position=(100 * i, 10)))
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
        self.bricks.clear()
        random_lives = []
        random_lives.extend([1] * 5)
        random_lives.extend([2] * self.level * 3)
        random_lives.extend([3] * self.level * 2)
        random_lives.extend([4] * self.level)
        logging.warning(f'LEVEL={self.level} random lives: {random_lives}')
        for x in range(0, 20):
            for y in range(1 + self.level if self.level < 12 else 12):
                lives = choice(random_lives)
                self.bricks.append(
                    Brick(((10 + (BRICK_SIZE[0] + 10) * x, 40 + (BRICK_SIZE[1] + 10) * y)),
                          lives=lives))

    def draw(self) -> None:
        """
        Асинхронное рисование мира.
        Сначала создаем задачи на рисование и дальше запускаем асинхнорнное выполнение.
        Убирает возможные лаги
        :return: None
        """
        tasks = [self.handle.draw(self.screen)]

        for brick in self.bricks:
            tasks.append(ioloop.create_task(brick.draw(self.screen)))

        for ball in self.balls:
            tasks.append(ioloop.create_task(ball.draw(self.screen)))

        for bonus in self.bonuses:
            tasks.append(ioloop.create_task(bonus.draw(self.screen)))

        tasks.append(ioloop.create_task(self.text_draw()))

        if self.over:
            tasks.append(ioloop.create_task(self.over.draw(self.screen)))

        wait_tasks = asyncio.wait(tasks)
        ioloop.run_until_complete(wait_tasks)

    async def text_draw(self) -> None:
        """
        Асинхронное Рисование жизней, очков и уровня на экране.
        Жизней больше 20 не рисует, но считает
        Если есть нижняя стенка то рисуем её жизни
        :return:
        """
        my_font = pygame.font.Font(os.path.join('resource', 'fonts', 'iomanoid.ttf'), 24)
        lives_surface = my_font.render('LIVES:', False, MAGENTA4)
        score_surface = my_font.render(f'SCORE: {self.score:012d}', False, MAGENTA4)
        level_surface = my_font.render(f'LEVEL: {self.level:02d}', False, MAGENTA4)

        self.screen.blit(lives_surface, (WIDTH - 620, 5))
        self.screen.blit(score_surface, (WIDTH - 265, 5))
        self.screen.blit(level_surface, (10, 5))
        # жизни нижней стенки
        if any(True for brick in self.bricks if brick.w_size == WIDTH):
            lives = [brick for brick in self.bricks if brick.w_size == WIDTH][0].lives
            wall_surface = my_font.render(f'WALL LIVES: {lives}', False, DARKORANGE)
            self.screen.blit(wall_surface, (200, 5))

        for i in range(self.lives if self.lives < 21 else 20):
            pygame.gfxdraw.filled_circle(self.screen, WIDTH - (540 - i * 12), 23, 4, DARKORANGE)

    def update(self) -> None:
        """
        Основной процесс обновления и отслеживания взаимодействий
        :return: None
        """
        time = self.clock.get_time()
        if not self.start:
            return

        if self.over:
            self.over.update(time)

        # обновляем ракетку
        self.handle.update(time)
        # обновляем мячи
        for ball in self.balls:
            ball.update(time)
        # если мяч вылетел за пределы нижней линии то удаляем его
        for ball in self.balls:
            if ball.position[1] > HEIGHT:
                self.balls.remove(ball)
        # обновляем бонусы
        for bonus in self.bonuses:
            bonus.update(time)
        # если бонус вылетел за пределы экрана удаляем его
        for bonus in self.bonuses:
            if bonus.position[1] > HEIGHT:
                self.bonuses.remove(bonus)
                sounds['sound_lost_bonus'].play()
                logging.warning(f'bonus remove bonus id = {bonus.bonus_id}')

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
                        sounds['sound_brick_dead'].play()
                        ioloop.run_until_complete(wait_tasks)
                        # если кирпич с бонусом то добавляем бонус
                        if brick.bonus:
                            self.bonuses.append(Bonus(brick.bonus, position=brick.position))
                        break
                    sounds['sound_brick_no_dead'].play()
                    ioloop.run_until_complete(wait_tasks)
            else:
                new_bricks.append(brick)
        # если кирпичи кончились генерируем новую карту и делаем новый уровень
        if not new_bricks or (len(new_bricks) <= 1 and any(True for brick in self.bricks if brick.w_size == WIDTH)):
            self.level += 1
            sounds['sound_next_level'].play()
            # если была стенка перегенерируем её снова
            if any(True for brick in self.bricks if brick.w_size == WIDTH):
                self.map_generator()
                self.bonus_add_wall()
            else:
                self.map_generator()

            logging.warning(f'No bricks - next level {self.level}')
        else:
            self.bricks = new_bricks

        # проверяем столкновение мячей с ракеткой, если во время движения то меняем скорости мячей
        for ball in self.balls:
            if self.handle.is_inside(ball.position):
                self.handle.check_collision(ball)
                sounds['sound_handle'].play()
                if pygame.key.get_pressed()[K_RIGHT]:
                    ball.speed[0] += 50

                if pygame.key.get_pressed()[K_LEFT]:
                    ball.speed[0] -= 50

        # проверяем столкновение бонуса с ракеткой если оно произошло то дергаем бонус и бонус удаляем
        for bonus in self.bonuses:
            if bonus.is_inside(self.handle.position, self.handle.w_size):
                logging.warning(f'handle get bonus id = {bonus.bonus_id}')
                self.bonus[bonus.bonus_id]()
                wait_tasks = asyncio.wait([ioloop.create_task(bonus.draw_destroy(self.screen))])
                ioloop.run_until_complete(wait_tasks)
                sounds['sound_get_bonus'].play()
                self.bonuses.remove(bonus)

    def tick(self) -> None:
        self.clock.tick(60)

    def spawn_ball(self):
        """
        Добавления мяча c небольшим рандомом размещения на ракетке
        :return:
        """
        if not self.over:
            position = self.handle.position[:]
            position[0] += HANDLE_SIZE[0] // 2 + randint(-40, 40)
            position[1] -= 5
            self.balls.append(Ball(position))
            sounds['sound_spawn'].play()

    def game_over(self) -> None:
        """
        Конец игры
        :return:
        """
        sounds['sound_game_over'].play()
        logging.warning('game over')
        self.over = GameOver(self.score, self.level)

    def bonus_add_wall(self, lives: int = 10) -> None:
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
        wall = Brick((0, HEIGHT - 5), lives=lives)
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
        Бонус + 3 шарика и сейчас не больше 20 мячей
        :return:
        """
        self.score += 20000
        if len(self.balls) < 20:
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
        Бонус уменьшения скорости
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
        self.score += 50000
        self.level += 1
        sounds['sound_next_level'].play()
        logging.warning(f'bonus_next_level level = {self.level}')
        if any(True for brick in self.bricks if brick.w_size == WIDTH):
            self.map_generator()
            self.bonus_add_wall()
            logging.warning(f'bonus_next_level with WALL')
        else:
            self.map_generator()
            logging.warning(f'bonus_next_level with NO WALL')

    def bonus_handle_decrease(self) -> None:
        """
        Бонус уменьшения ракетки
        :return:
        """
        self.score += 20000
        self.handle.bonus_time += HANDLE_BONUS_TIME
        if self.handle.w_size > HANDLE_SIZE[0] // 1.7:
            self.handle.w_size = int(self.handle.w_size / 1.3)
        logging.warning(f'bonus_handle_decrease')

    def bonus_handle_increase(self) -> None:
        """
        Бонус увеличения ракетки
        :return:
        """
        self.score += 20000
        self.handle.bonus_time += HANDLE_BONUS_TIME
        if self.handle.w_size < HANDLE_SIZE[0] * 2:
            self.handle.w_size = int(self.handle.w_size * 1.3)
        logging.warning(f'bonus_handle_increase = {self.level}')


class Brick:
    """
    Класс блоков
    В блоке может быть рандомный бонус
    """

    def __init__(self, position=None, lives=1):
        self.w_size = BRICK_SIZE[0]
        self.h_size = BRICK_SIZE[1]
        self.position = list(position)
        self.lives = lives
        self.color = BRICK_COLORS.get(lives, BRICK_COLORS[1])
        rnd_bonus = [0] * 40
        # bonus_add_wall
        rnd_bonus.extend([1] * 2)
        # bonus_add_lives
        rnd_bonus.extend([2] * 3)
        # bonus_add_balls
        rnd_bonus.extend([3] * 4)
        # bonus_next_level
        rnd_bonus.extend([4])
        # bonus_balls_increase_speed
        rnd_bonus.extend([5] * 1)
        # bonus_balls_decrease_speed
        rnd_bonus.extend([6] * 1)
        # bonus_handle_decrease
        rnd_bonus.extend([7] * 2)
        # bonus_handle_increase
        rnd_bonus.extend([8] * 2)
        self.bonus = choice(rnd_bonus)
        # logging.warning(f'brick bonus {self.bonus}')

    async def draw(self, screen: pygame.Surface) -> None:
        """
        Рисование блока с градиентной заливкой и тенью.
        Рисуем Surface 2x2, пару линий в нем и растягиваем его до размеров блока.
        :param screen:
        :return: None
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

    # логика проверки взаимодействий мяча и блока,
    # разный отскок в зависимости от попадания мяча
    # в вертикальную часть или горизонтальную часть блока
    def is_inside_hbounds(self, x: int) -> None:
        left_bound = self.position[0] - BALL_RADIUS
        right_bound = self.position[0] + self.w_size + BALL_RADIUS
        return left_bound <= x <= right_bound

    def is_inside_vbounds(self, y: int) -> None:
        up_bound = self.position[1] - BALL_RADIUS
        down_bound = self.position[1] + self.h_size + BALL_RADIUS
        return up_bound <= y <= down_bound

    def is_inside(self, position: list, handle_w_size: int = None) -> bool:
        x, y = position
        return bool(self.is_inside_hbounds(x) and self.is_inside_vbounds(y))

    def is_h_collide(self, x1: int, x2: int) -> bool:
        return not self.is_inside_hbounds(x1) and self.is_inside_hbounds(x2)

    def is_v_collide(self, y1: int, y2: int) -> bool:
        return not self.is_inside_vbounds(y1) and self.is_inside_vbounds(y2)

    def check_collision(self, ball: Any) -> None:
        if self.is_h_collide(ball.prev_pos[0], ball.position[0]):
            ball.speed[0] *= -1
        if self.is_v_collide(ball.prev_pos[1], ball.position[1]):
            ball.speed[1] *= -1


class Handle(Brick):
    """
    Класс ракетки, в целом это тоже что и обычный блок и отличается одним методом
    """
    def __init__(self, position=None, lives=1):
        super(Handle, self).__init__(position, lives)
        self.bonus = 0
        self.w_size = HANDLE_SIZE[0]
        self.h_size = HANDLE_SIZE[1]
        self.bonus_time = HANDLE_BONUS_TIME

    def update(self, ticks: int) -> None:
        """
        Изменение координат ракетки в зависимости от нажатых клавиш
        Возврат размера ракетки по таймеру после бонусов изменения размера
        :param ticks: int
        :return: None
        """
        if self.bonus_time > 0:
            self.bonus_time -= ticks
        if self.bonus_time < 0:
            logging.warning('handle bonus timeout')
            self.w_size = HANDLE_SIZE[0]
            self.h_size = HANDLE_SIZE[1]
            self.bonus_time = 0

        if pygame.key.get_pressed()[K_RIGHT] and self.position[0] < WIDTH - self.w_size:
            self.position[0] += int(600 * ticks / 1000)

        if pygame.key.get_pressed()[K_LEFT] and self.position[0] >= 0:
            self.position[0] -= int(600 * ticks / 1000)


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

    async def draw(self, screen: pygame.Surface) -> None:
        """
        Асинхроноое рисование шара
        :param screen:
        :return:
        """
        pygame.gfxdraw.filled_circle(screen, int(self.position[0]), int(self.position[1]), self.radius, self.color)

    def update(self, ticks: int) -> None:
        """
        Меняем координаты шарика и если доходим до границ меняем скорость на обратную
        :param ticks: int
        :return: None
        """
        self.prev_pos = self.position[:]

        for i in (0, 1):
            self.position[i] += self.speed[i] * ticks / 1000

        # исправление возможной ошибки и залипание вдоль границ мира
        self.position[0] = max(self.position[0], self.radius)
        self.position[0] = min(self.position[0], WIDTH - self.radius)
        self.position[1] = max(self.position[1], self.radius)

        if self.position[0] <= self.radius or self.position[0] >= (WIDTH - self.radius):
            self.speed[0] *= -1

        if self.position[1] <= self.radius:
            self.speed[1] *= -1


class Bonus(Brick):
    """
    Класс падающего бонуса
    В зависимости от типа рисуется по разному.
    """
    def __init__(self, bonus_id, position=None):
        super(Bonus, self).__init__(position, lives=1)
        self.w_size = BRICK_SIZE[0] * 2
        self.position = [int(position[0] + BRICK_SIZE[0] // 2), int(position[1] + BRICK_SIZE[1])]
        self.color = BRICK_COLORS[5]
        self.speed = 200
        self.bonus_id = bonus_id
        self.prev_pos = self.position
        self.surface = pygame.Surface((self.w_size, self.h_size), pygame.SRCALPHA)

    async def draw(self, screen: pygame.Surface) -> None:
        """
        Асинхронное рисование бонусов
        Тип рисование зависит от его id
        :param screen: pygame.Surface
        :return: None
        """
        my_font = pygame.font.Font(os.path.join('resource', 'fonts', 'iomanoid.ttf'), 20)
        x, y = self.position
        if self.bonus_id == 1:
            # bonus_add_wall
            pygame.gfxdraw.filled_polygon(self.surface, [
                (0, 0),
                (self.w_size, 0),
                (self.w_size, self.h_size // 2),
                (0, self.h_size // 2),
            ],
                                          DARKORANGE)
            screen.blit(self.surface, (x, y))
        elif self.bonus_id == 2:
            # bonus_add_lives
            pygame.gfxdraw.filled_circle(screen, x + BALL_RADIUS * 2 + 4, y, BALL_RADIUS + 2, DARKORANGE)
            pygame.gfxdraw.filled_circle(screen, x, y, BALL_RADIUS + 2, DARKORANGE)
            pygame.gfxdraw.filled_circle(screen, x - BALL_RADIUS * 2 - 4, y, BALL_RADIUS + 2, DARKORANGE)
        elif self.bonus_id == 3:
            # bonus_add_balls
            pygame.gfxdraw.filled_circle(screen, x + BALL_RADIUS * 2, y + BALL_RADIUS * 2, BALL_RADIUS + 2, BLUE)
            pygame.gfxdraw.filled_circle(screen, x, y, BALL_RADIUS + 2, ORANGE)
            pygame.gfxdraw.filled_circle(screen, x - BALL_RADIUS * 2, y + BALL_RADIUS * 2, BALL_RADIUS + 2, GREEN)
        elif self.bonus_id == 4:
            # bonus_next_level
            surface = my_font.render('NEXT', True, DARKORANGE)
            screen.blit(surface, (x, y))
        elif self.bonus_id == 5:
            # bonus_balls_increase_speed ↑
            surface = my_font.render('SPEED UP', True, DARKORANGE)
            screen.blit(surface, (x, y))
        elif self.bonus_id == 6:
            # bonus_balls_decrease_speed ↓
            surface = my_font.render('SPEED DOWN', True, DARKORANGE)
            screen.blit(surface, (x, y))
        elif self.bonus_id == 7:
            # bonus_handle_decrease →→  ←←
            pygame.gfxdraw.filled_polygon(self.surface, [
                (self.h_size // 2, self.h_size // 2),
                (0, 0),
                (self.h_size // 2, self.h_size // 4),
                (self.w_size - self.h_size // 2, self.h_size // 4),
                (self.w_size, 0),
                (self.w_size - self.h_size // 2, self.h_size // 2),
                (self.w_size, self.h_size),
                (self.w_size - self.h_size // 2, self.h_size - self.h_size // 4),
                (self.h_size // 2, self.h_size - self.h_size // 4),
                (0, self.h_size),
            ],
                                          DARKORANGE)
            screen.blit(self.surface, (x, y))
        elif self.bonus_id == 8:
            # bonus_handle_increase ←←  →→
            pygame.gfxdraw.filled_polygon(self.surface, [
                (0, self.h_size // 2),
                (self.h_size // 2, 0),
                (self.h_size // 2, self.h_size // 4),
                (self.w_size - self.h_size // 2, self.h_size // 4),
                (self.w_size - self.h_size // 2, 0),
                (self.w_size, self.h_size // 2),
                (self.w_size - self.h_size // 2, self.h_size),
                (self.w_size - self.h_size // 2,
                 self.h_size - self.h_size // 4),
                (self.h_size // 2, self.h_size - self.h_size // 4),
                (self.h_size // 2, self.h_size),
            ],
                                          DARKORANGE)
            screen.blit(self.surface, (x, y))

    def update(self, ticks: int) -> None:
        """
        Обновляем координаты и опускаем бонус
        :param ticks: int
        :return: None
        """
        self.prev_pos = self.position[:]
        self.position[1] += int(self.speed * ticks / 1000)

    def is_inside(self, position: list, handle_w_size: int = None) -> bool:
        """
        Для отлавливания коллизии с делаем два прямоугольника
        rect1 - handle
        rect2 - падающий бонус
        и методом colliderect ищем пересечение
        :param position:
        :param handle_w_size:
        :return: boll
        """
        x, y = position
        rect1 = pygame.Rect(x, y, handle_w_size, 10)
        rect2 = pygame.Rect(self.position[0],
                            self.position[1],
                            self.w_size,
                            self.h_size)

        return bool(rect1.colliderect(rect2))


class GameOver:
    """
    Рисует выплывающая картинка GameOver
    """
    def __init__(self, score, level):
        self.image = load_image("over.png", colorkey=-1)
        self.rect = self.image.get_rect()
        self.rect.x = -WIDTH
        self.rect.y = HEIGHT // 2
        self.score = score
        self.level = level

    async def draw(self, screen: pygame.Surface):
        """
        Асинхронное рисование
        :param screen: pygame.Surface
        :return: None
        """
        screen.blit(self.image, (self.rect.x, self.rect.y))

    def update(self, time: int) -> None:
        """
        Выплываем слева на право
        :param time:
        :return:
        """
        if self.rect.x >= WIDTH // 2 - self.rect[2] // 2:
            sleep(3)
            menu_start(score=self.score, level=self.level)
        else:
            self.rect.x += 1 * time


# MENU

def change_name(value):
    """
    Меняем глобальное имя пользователя, опять же чтоб не мучаться с пробром имени между меню и игрой.
    :param value:
    :return:
    """
    global user_name
    user_name = value


def high_scores(level: int = 1, scores: int = 0, name: str = user_name) -> List[tuple]:
    """
    Записывает результаты игры если scores попали в топ 10 и возвращает топ 10
    Для читеров не пишется результат
    :param level: int
    :param scores: int
    :param name: str
    :return: List[tuple]
    """
    file = 'resource/.records.pickle'
    if not os.path.isfile(file):
        with open(file, 'wb') as f:
            pickle.dump([('__________', 0, 0000000)] * 10, f)

    with open(file, 'rb') as f:
        result = pickle.load(f)
        # для читеров рекорды не пишем ;)
        if IDDQD:
            return result
        if scores:
            result.append((name, level, scores))
        result.sort(key=lambda x: (-x[2], -x[1]))
    result = result[:10]
    with open(file, 'wb') as f:
        pickle.dump(result, f)
    return result


def set_difficulty(value, difficulty):
    """
    Задаем уровень сложности если уровень читерский то включем небольшую отладку в консоль
    :param value:
    :param difficulty:
    :return:
    """
    logging.warning(f'set_difficulty {value}')
    global IDDQD
    if difficulty == 3:
        IDDQD = True
        logging.basicConfig(level=logging.WARNING)
    else:
        IDDQD = False
        logging.basicConfig(level=logging.ERROR)


def set_sound_volume(value: Any, volume: float) -> None:
    """
    PyGame mixer не поддерживает глобальной громкости для звуков,
    поэтому нужно каждый звук регулировать отдельно.
    Пробегаем по инстансу звуков и выставляем громкость
    :param value: Any
    :param volume: float
    :return: None
    """
    for k, v in sounds.items():
        sounds[k].set_volume(volume)


def menu_start(score: int = 0, level: int = 1) -> None:
    """
    стартовое меню игры
    :param score: int
    :param level: int
    :return: None
    """
    logging.warning(f'score = {score} level = {level} name = {user_name}')
    scores = high_scores(scores=score, level=level, name=user_name)

    ABOUT = ['pygame project от преподавателя Яндекс Лицея',
             'Author: Lord Voldemort (нельзя себя называть, увы)',
             'Email: _____ почта тоже в секрете']

    HELP = ['Управление кнопками вправо и влево. Пауза клавиша <p>',
            'Скорость мяча меняется при столкновении с движущейся ракеткой',
            '',
            'В игре 8 типов бонусов:',
            '- защитная стена снизу с 10 жизнями, ',
            '  жизнь стены уменьшается при попадании по ней мяча;',
            '- 3 дополнительные жизни;',
            '- 3 дополнительных мяча;',
            '- переход на следующий уровень;',
            '- ускорение мячей;',
            '- замедление мячей;'
            '- увеличение и уменьшение ракетки.']

    screen = pygame.display.set_mode(SIZE)

    # menu ABOUT
    about_theme = pygame_menu.themes.THEME_DARK.copy()
    about_theme.widget_margin = (0, 0)
    about_menu = pygame_menu.Menu(
        height=HEIGHT * 0.6,
        theme=about_theme,
        title='About',
        width=WIDTH * 0.6,
        mouse_enabled=False
    )

    for m in ABOUT:
        about_menu.add.label(m, align=pygame_menu.locals.ALIGN_CENTER, font_size=20)
    about_menu.add.vertical_margin(30)
    about_menu.add.button('Return to menu', pygame_menu.events.BACK)

    # menu HELP
    help_theme = pygame_menu.themes.THEME_DARK.copy()
    help_theme.widget_margin = (0, 0)
    help_menu = pygame_menu.Menu(
        height=HEIGHT * 0.9,
        theme=help_theme,
        title='Help',
        width=WIDTH * 0.7,
        mouse_enabled=False
    )
    for m in HELP:
        help_menu.add.label(m, margin=(30, 0), align=pygame_menu.locals.ALIGN_LEFT, font_size=20)
    help_menu.add.vertical_margin(30)
    help_menu.add.button('Return to menu', pygame_menu.events.BACK)

    # menu SCORES
    scores_theme = pygame_menu.themes.THEME_DARK
    scores_theme.widget_margin = (0, 0)
    scores_menu = pygame_menu.Menu(
        height=HEIGHT * 0.9,
        theme=scores_theme,
        title='High scores',
        width=WIDTH * 0.7,
        mouse_enabled=False
    )

    scores_menu.add.label(f'##       SCORES       LEVEL     NAME',
                          align=pygame_menu.locals.ALIGN_LEFT,
                          font_size=28,
                          font_color=DEEPSKYBLUE,
                          margin=(100, 0)
                          )
    for n, m in enumerate(scores, 1):
        scores_menu.add.label(f'{n:02d} - {m[2]:012d} - {m[1]:02d} - {m[0]}',
                              align=pygame_menu.locals.ALIGN_LEFT,
                              font_size=28,
                              font_color={1: RED, 2: DARKORANGE, 3: DARKGREEN}.get(n, DARKGRAY),
                              margin=(100, 0)
                              )
    scores_menu.add.vertical_margin(30)
    scores_menu.add.button('Return to menu', pygame_menu.events.BACK)

    # main MENU
    menu = pygame_menu.Menu(height=HEIGHT,
                            width=WIDTH,
                            title='ARCANOID',
                            theme=pygame_menu.themes.THEME_DARK,
                            mouse_enabled=False
                            )
    # img = os.path.join(os.path.dirname(pygame_menu.__file__), 'sound', 'logo.png')
    img = os.path.join('resource', 'img', 'logo.png')
    menu.add.image(img, scale=(0.6, 0.6), scale_smooth=True)

    menu.add.button('Play', start_the_game)
    menu.add.text_input('Name: ', default=user_name, onchange=change_name)
    menu.add.selector('Difficulty: ', [('Easy', 1), ('Cheats', 3)], onchange=set_difficulty)
    menu.add.selector('Volume: ', [(f'{i}%', i / 100) for i in range(0, 101, 10)], default=5, onchange=set_sound_volume)
    menu.add.button('High scores', scores_menu)
    menu.add.button('Help', help_menu)
    menu.add.button('About', about_menu)
    menu.add.button('Quit', pygame_menu.events.EXIT)
    menu.mainloop(screen)


def start_the_game() -> None:
    """
    Запускает игровой цикл, по выходу из игры запускает меню
    :return: None
    """
    screen = pygame.display.set_mode(SIZE)
    world = World(screen)
    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                menu_start()
                pygame.quit()
                return
            if event.type == pygame.KEYDOWN:
                if pygame.key.get_pressed()[K_p]:
                    world.start = not world.start
                    logging.warning('game toggle start')
                if pygame.key.get_pressed()[K_ESCAPE] or pygame.key.get_pressed()[K_q]:
                    logging.warning('game exit by keys')
                    menu_start()
                    pygame.quit()
                    return
        screen.fill(BLACK)
        world.update()
        world.draw()
        world.tick()
        pygame.display.flip()


if __name__ == '__main__':
    menu_start()
    # main()
