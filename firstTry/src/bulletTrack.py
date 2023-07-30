from math import cos, sin, sqrt, floor, ceil
from map import *


class BulletData:
    def __init__(self, id, bullet, time):
        self.id = id
        self.pos = bullet["position"]
        self.vel = bullet["velocity"]
        self.damage = bullet["damage"]
        self.bounces_left = 2


def linecast(start, velocity, walls: Map, destructables: Map) -> tuple[list[int], bool]:
    # |direction[0]| > |direction[1]|
    x = start[0] / CELL_SIZE
    y = start[1] / CELL_SIZE

    if abs(velocity[0]) > abs(velocity[1]):
        grad = velocity[1] / velocity[0]

        dx = 0
        if velocity[0] > 0:
            y += grad * (ceil(x) - x)
            dx = 1
        elif velocity[0] < 0:
            y += -grad * (x - floor(x))
            dx = -1

        end = False
        cx = floor(x)
        while not end:
            cx += dx
            cy = floor(y)

            if cx >= walls.width or cx < 0:
                return [cx, cy], True
            elif cy >= walls.height or cy < 0:
                return [cx, cy], False

            newy = y + grad * dx

            destructables.set(cx, cy, True)
            if walls.get(cx, cy):
                return [cx, cy], True

            if max(y, newy) + 0.25 > cy + 1 and walls.get(cx, cy + 1):
                return [cx, cy + 1], False

            if min(y, newy) - 0.25 < cy and walls.get(cx, cy - 1):
                return [cx, cy - 1], False

            y = newy
    else:
        grad = velocity[0] / velocity[1]

        dy = 0
        if velocity[1] > 0:
            x += grad * (ceil(y) - y)
            dy = 1
        elif velocity[1] < 0:
            x += -grad * (y - floor(y))
            dy = -1

        end = False
        cy = floor(y)
        while not end:
            cy += dy
            cx = floor(x)

            if cx >= walls.width or cx < 0:
                return [cx, cy], True
            elif cy >= walls.height or cy < 0:
                return [cx, cy], False

            newx = x + grad * dy

            destructables.set(cx, cy, True)
            if walls.get(cx, cy):
                return [cx, cy], False

            if max(x, newx) + 0.25 > cx + 1 and walls.get(cx + 1, cy):
                return [cx + 1, cy], True

            if min(x, newx) - 0.25 < cx and walls.get(cx - 1, cy):
                return [cx - 1, cy], True

            x = newx


m = Map(50, 50)
out = Map(50, 50)
m.set(24, 10, True)
print(m)
print(linecast([24 * 20, 24 * 20], [0, -1], m, out))
print(out)


class Path:
    def __init__(self, start, vel, time, walls, destructables):
        self.paths = []

    def pos(self, time) -> list[float]:
        return [0, 0]
