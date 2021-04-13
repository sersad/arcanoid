#!/usr/bin/env python3

import pygame
import pygame.gfxdraw
from pygame.locals import *

size = width, height = (1024, 768)
white = pygame.Color("white")
black = pygame.Color("black")

class World:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.bricks = []
        for x in range(20):
            for y in range(5):
                self.bricks.append(Brick(((10 + 50 * x, 40 + 30 * y))))
        self.handle = Handle((width // 2 - 30, height - 10 - 40))
        self.balls = []
        self.spawn_ball()

    def draw(self):
        self.handle.draw(self.screen)
        for i in self.bricks:
            i.draw(self.screen)

        for i in self.balls:
            i.draw(self.screen)

    def update(self):
        time = self.clock.get_time()
        self.handle.update(time)
        for i in self.balls:
            i.update(time)

        for ball in self.balls:
            if ball.position[1] > height:
                self.balls.remove(ball)

        if not self.balls:
            self.handle = Handle((width // 2 - 30, height - 10 - 40))
            self.spawn_ball()
            sound3.play()
            return

        new_bricks = []
        for i in self.bricks:
            for ball in self.balls:
                if i.is_inside(ball.position):
                    i.check_collision(ball)
                    sound2.play()
                    break
            else:
                new_bricks.append(i)

        self.bricks = new_bricks

        for ball in self.balls:
            if self.handle.is_inside(ball.position):
                self.handle.check_collision(ball)
                sound1.play()
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


class Brick:
    w_size = 40
    h_size = 20

    def __init__(self, position=None, color=white):
        self.position = list(position)
        self.color = white

    def draw(self, screen):
        pygame.gfxdraw.box(screen, pygame.Rect(self.position, (self.w_size, self.h_size)), self.color)

    def is_inside_hbounds(self, x):
        left_bound = self.position[0] - 5
        right_bound = self.position[0] + self.w_size + 5
        return (left_bound <= x <= right_bound)

    def is_inside_vbounds(self, y):
        up_bound = self.position[1] - 5
        down_bound = self.position[1] + self.h_size + 5
        return (up_bound <= y <= down_bound)

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
    w_size = 160
    h_size = 10

    def update(self, ticks):
        if pygame.key.get_pressed()[K_RIGHT]:
            self.position[0] += 500 * ticks / 1000

        if pygame.key.get_pressed()[K_LEFT]:
            self.position[0] -= 500 * ticks / 1000


class Ball:
    def __init__(self, position, color=white):
        self.position = list(position)
        self.color = white
        self.speed = [300, -300]
        self.prev_pos = self.position

    def draw(self, screen):
        pygame.gfxdraw.filled_circle(screen, int(self.position[0]), int(self.position[1]), 5, self.color)

    def update(self, ticks):
        self.prev_pos = self.position[:]

        if self.position[0] < 5 or self.position[0] >= (width - 5):
            self.speed[0] *= -1

        if self.position[1] < 5:
            self.speed[1] *= -1

        for i in (0, 1):
            self.position[i] += self.speed[i] * ticks / 1000


def main():
    global sound1, sound2, sound3
    pygame.init()
    pygame.mixer.music.load('sound/02_-_Arkanoid_-_ARC_-_Game_Start.ogg')
    pygame.mixer.music.play()

    sound1 = pygame.mixer.Sound('sound/Arkanoid SFX (2).wav')
    sound2 = pygame.mixer.Sound('sound/Arkanoid SFX (1).wav')
    sound3 = pygame.mixer.Sound('sound/Arkanoid SFX (4).wav')

    screen = pygame.display.set_mode(size)
    world = World(screen)

    while True:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                return

        screen.fill(black)
        world.update()
        world.draw()
        world.tick()
        pygame.display.flip()


if __name__ == '__main__':
    main()
