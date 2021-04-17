#!/usr/bin/env python3
import os
import sys
from random import randint, random
from time import sleep

import pygame
import pygame.gfxdraw
from pygame.locals import *


SIZE = WIDTH, HEIGHT = 1024, 768
BRICK_SIZE = 40, 20
HANDLE_SIZE = 160, 10
BALL_RADIUS = 5

# https://github.com/pygame/pygame/blob/main/src_py/colordict.py
WHITE = pygame.Color("WHITE")
BLACK = pygame.Color("BLACK")
RED = pygame.Color("red")
DARKRED = pygame.Color("darkred")
GREEN = pygame.Color("green")
BLUE = pygame.Color("blue")
YELLOW = pygame.Color("yellow")
MAGENTA = pygame.Color("magenta")
MAGENTA4 = pygame.Color("magenta4")
GRAY = pygame.Color("gray")
DARKGRAY = pygame.Color("darkgray")
BRICK_COLORS = {0: WHITE, 1: WHITE, 2: GREEN, 3: YELLOW, 4: RED}


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


class World:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.bricks = []
        for x in range(20):
            for y in range(5):
                lives = randint(1, 4)
                self.bricks.append(Brick(((10 + (BRICK_SIZE[0] + 10) * x, 40 + (BRICK_SIZE[1] + 10) * y)),
                                         lives=lives))
        self.handle = Handle((WIDTH // 2 - HANDLE_SIZE[0] // 2, HEIGHT - HANDLE_SIZE[1] - 40))
        self.balls = []
        self.spawn_ball()

    def draw(self):
        self.handle.draw(self.screen)
        for brick in self.bricks:
            brick.draw(self.screen)

        for ball in self.balls:
            ball.draw(self.screen)

    def update(self):
        time = self.clock.get_time()
        self.handle.update(time)
        for i in self.balls:
            i.update(time)

        for ball in self.balls:
            if ball.position[1] > HEIGHT:
                self.balls.remove(ball)

        if not self.balls:
            self.handle = Handle((WIDTH // 2 - 30, HEIGHT - 10 - 40))
            self.spawn_ball()
            return

        new_bricks = []
        for brick in self.bricks:
            for ball in self.balls:
                if brick.is_inside(ball.position):
                    brick.check_collision(ball)
                    brick.lives -= 1
                    if brick.lives < 1:
                        sound_brick_dead.play()
                        brick.draw_destroy(self.screen)
                        break
                    sound_brick_no_dead.play()
                    brick.draw_destroy(self.screen)
            else:
                new_bricks.append(brick)

        self.bricks = new_bricks

        for ball in self.balls:
            if self.handle.is_inside(ball.position):
                self.handle.check_collision(ball)
                sound_handle.play()
                if pygame.key.get_pressed()[K_RIGHT]:
                    ball.speed[0] += 50

                if pygame.key.get_pressed()[K_LEFT]:
                    ball.speed[0] -= 50

    def tick(self):
        self.clock.tick(120)

    def spawn_ball(self):
        position = self.handle.position[:]
        position[0] += 30
        position[1] -= 5
        self.balls.append(Ball(position))
        sound_spawn.play()


class Brick:
    w_size = BRICK_SIZE[0]
    h_size = BRICK_SIZE[1]

    def __init__(self, position=None, lives=1):
        self.position = list(position)
        self.lives = lives
        self.color = BRICK_COLORS[lives]
        self.tick = 0

    def draw(self, screen):
        self.color = BRICK_COLORS[self.lives]
        pygame.gfxdraw.box(screen, pygame.Rect((self.position[0] + 1, self.position[1] + 1),
                                               (self.w_size + 1, self.h_size + 1)), DARKGRAY)
        pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), self.color)
        # if randint(0, 1) and self.lives > 1:
        #         pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), self.color.correct_gamma(randint(0, 255)))
        # if randint(0, 4) and self.lives > 3:
        # if self.lives > 3:
        #     pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), self.color.correct_gamma(randint(0, 100)))
            # if randint(0, 1):
            #     pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), DARKRED)

    def draw_destroy(self, screen):
        self.color = BRICK_COLORS[self.lives]
        pygame.gfxdraw.box(screen, pygame.Rect((self.position[0] + 1, self.position[1] + 1),
                                               (self.w_size + 1, self.h_size + 1)), MAGENTA4)
        pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), MAGENTA)

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
    w_size = HANDLE_SIZE[0]
    h_size = HANDLE_SIZE[1]

    def update(self, ticks):
        if pygame.key.get_pressed()[K_RIGHT] and 0 <= self.position[0] < WIDTH - HANDLE_SIZE[0] - 4:
            self.position[0] += 500 * ticks / 1000

        if pygame.key.get_pressed()[K_LEFT] and 4 < self.position[0] <= WIDTH - HANDLE_SIZE[0]:
            self.position[0] -= 500 * ticks / 1000


class Ball:
    def __init__(self, position, color=WHITE):
        self.position = list(position)
        self.color = WHITE
        self.speed = [300, -300]
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
    global sound_handle, sound_brick_dead, sound_brick_no_dead, sound_spawn, sound_game_over
    pygame.init()
    # pygame.mixer.music.load('sound/02_-_Arkanoid_-_ARC_-_Game_Start.ogg')
    # pygame.mixer.music.play()

    sound_handle = pygame.mixer.Sound('sound/Arkanoid SFX (2).wav')
    sound_brick_dead = pygame.mixer.Sound('sound/Arkanoid SFX (1).wav')
    sound_spawn = pygame.mixer.Sound('sound/Arkanoid SFX (4).wav')
    sound_brick_no_dead = pygame.mixer.Sound('sound/Arkanoid SFX (7).wav')
    sound_game_over = pygame.mixer.Sound('sound/05_-_Arkanoid_-_ARC_-_Game_Over.ogg')


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
