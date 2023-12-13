import time

import comms
from object_types import ObjectTypes

import sys
from math import sin, cos, atan, radians, degrees, floor, ceil, sqrt
from map import Map, worldToCell, cellToWorld, CELL_SIZE

DELTA_TIME = 0.25
BOUNDARY_SPEED = 10


def log(text):
    print(text, file=sys.stderr)


def vect2Angle(x, y):
    if x == 0:
        x = 0.001
    angle = degrees(atan(y / x))
    if x < 0:
        angle = 180 + angle

    return angle


def angleToVect(degrees):
    rads = radians(degrees)
    return cos(rads), sin(rads)


def scaleVect(scale: float, vect: list[float]):
    return [scale * vect[0], scale * vect[1]]


def addVect(v1: list[float], v2: list[float]):
    return [v1[0] + v2[0], v1[1] + v2[1]]


def distanceSqr(v1: list[float], v2: list[float] = [0, 0]) -> float:
    delta = addVect(v1, scaleVect(-1, v2))
    return delta[0] * delta[0] + delta[1] * delta[1]


class Game:
    """
    Stores all information about the game and manages the communication cycle.
    Available attributes after initialization will be:
    - tank_id: your tank id
    - objects: a dict of all objects on the map like {object-id: object-dict}.
    - width: the width of the map as a floating point number.
    - height: the height of the map as a floating point number.
    - current_turn_message: a copy of the message received this turn. It will be updated everytime `read_next_turn_data`
        is called and will be available to be used in `respond_to_turn` if needed.
    """

    def __init__(self):
        self.dummy = False
        self.turnCount = 0
        self.gameTime = 0
        self.pickups: set[str] = set()
        self.bullets: set[str] = set()
        self.oldPos = [0, 0]
        self.circlingDir = 1
        self.lastLOS = False

        # begin reading

        tank_id_message: dict = comms.read_message()
        self.tank_id = tank_id_message["message"]["your-tank-id"]
        self.enemy_id = tank_id_message["message"]["enemy-tank-id"]

        self.current_turn_message = None

        # We will store all game objects here
        self.objects = {}

        next_init_message = comms.read_message()
        while next_init_message != comms.END_INIT_SIGNAL:
            # At this stage, there won't be any "events" in the message. So we only care about the object_info.
            object_info: dict = next_init_message["message"]["updated_objects"]

            # Store them in the objects dict
            self.objects.update(object_info)

            # Read the next message
            next_init_message = comms.read_message()

        # We are outside the loop, which means we must've received the END_INIT signal

        # Let's figure out the map size based on the given boundaries

        # Read all the objects and find the boundary objects
        boundaries = []
        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.BOUNDARY.value:
                boundaries.append(game_object)

        # The biggest X and the biggest Y among all Xs and Ys of boundaries must be the top right corner of the map.

        # Let's find them. This might seem complicated, but you will learn about its details in the tech workshop.
        biggest_x, biggest_y = [
            max(
                [
                    max(
                        map(
                            lambda single_position: single_position[i],
                            boundary["position"],
                        )
                    )
                    for boundary in boundaries
                ]
            )
            for i in range(2)
        ]

        self.width = biggest_x
        self.height = biggest_y

        # create wall map
        x, y = worldToCell(biggest_x, biggest_y)
        self.walls = Map(x, y)
        self.destructables = Map(x, y)

        for game_object in self.objects.values():
            if game_object["type"] == ObjectTypes.WALL.value:
                pos = game_object["position"]
                x, y = worldToCell(pos[0], pos[1])
                self.walls.set(x, y, True)
            elif game_object["type"] == ObjectTypes.DESTRUCTIBLE_WALL.value:
                pos = game_object["position"]
                x, y = worldToCell(pos[0], pos[1])
                self.destructables.set(x, y, True)
            # elif game_object["type"] == ObjectTypes.CLOSING_BOUNDARY.value:
            #     self.cb_id =

        # log(f"Walls:\n{self.walls}")
        # log(f"Breaks:\n{self.destructables}")

    def getBoundary(self, time: float) -> tuple[list[float], list[float]]:
        distTraveled = BOUNDARY_SPEED * time
        return [distTraveled, distTraveled], [
            self.width - distTraveled,
            self.height - distTraveled,
        ]

    def outsideBounds(self, coords: list[float], padding: float = 0) -> bool:
        lower, upper = self.getBoundary(self.gameTime)
        for l in addVect(addVect(coords, [-padding, -padding]), scaleVect(-1, lower)):
            if l < 0:
                return True
        for u in addVect(addVect(upper, [-padding, -padding]), scaleVect(-1, coords)):
            if u < 0:
                return True
        return False

    def checkForWalls(self, cell: list[int]) -> int:
        if self.walls.get(cell[0], cell[1]):
            return 1
        elif self.destructables.get(cell[0], cell[1]):
            return 2
        return 0

    def linecastBounds(self, start, end) -> tuple[list[float], bool, bool] | None:
        # check boundary
        delta = [end[0] - start[0], end[1] - start[1]]
        lower, upper = self.getBoundary(self.gameTime)

        hit = [-1, -1]
        for i in [0, 1]:
            if delta[i] == 0:
                hit[i] = 1000
            elif delta[i] < 0:
                hit[i] = (lower[i] + 5 - start[i]) / delta[i]
            elif delta[i] > 0:
                hit[i] = (upper[i] - 5 - start[i]) / delta[i]

        # log(f"[{self.gameTime}] hitTimes:{hit}")
        # which hits first
        if hit[0] < 1 and hit[0] < hit[1]:
            return (
                addVect(start, scaleVect(hit[0], delta)),
                True,
                False,
            )
        elif hit[1] < 1:
            return (
                addVect(start, scaleVect(hit[1], delta)),
                False,
                False,
            )
        else:
            return None

    def linecast(self, start, end) -> tuple[list[float], bool, bool] | None:
        x = start[0] / CELL_SIZE
        y = start[1] / CELL_SIZE

        velocity = [end[0] - start[0], end[1] - start[1]]

        if velocity[0] == 0 and velocity[1] == 0:
            return None

        # |direction[0]| > |direction[1]|
        if abs(velocity[0]) > abs(velocity[1]):
            grad = velocity[1] / velocity[0]

            dx = 0
            if velocity[0] > 0:
                y += grad * (ceil(x) - x)
                dx = 1
            elif velocity[0] < 0:
                y += -grad * (x - floor(x))
                dx = -1

            endIndex = end[0] // CELL_SIZE

            cell: list[int] = [floor(x), 0]
            while True:
                cell[0] += dx
                cell[1] = floor(y)

                newy = y + grad * dx

                # check end
                if cell[0] == endIndex:
                    return None

                # check walls
                toCheck: list[tuple[list[int], bool]] = [(cell, True)]
                if max(y, newy) + 0.25 > cell[1] + 1:
                    toCheck.append(([cell[0], cell[1] + 1], False))
                if min(y, newy) - 0.25 < cell[1]:
                    toCheck.append(([cell[0], cell[1] - 1], False))

                for coords, hori in toCheck:
                    type = self.checkForWalls(coords)
                    if type != 0:
                        coords = addVect(scaleVect(CELL_SIZE, coords), [10, 10])
                        log(
                            f"[{self.gameTime}] LINECAST start: {start} end: {end} success: {coords} {hori} {type}"
                        )
                        return coords, hori, type == 2

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

            endIndex = end[1] // CELL_SIZE

            cy = floor(y)
            while True:
                cy += dy
                cx = floor(x)
                newx = x + grad * dy

                # check end
                if cy == endIndex:
                    return None

                # check walls
                toCheck: list[tuple[list[int], bool]] = [([cx, cy], False)]
                if max(x, newx) + 0.25 > cx + 1:
                    toCheck.append(([cx + 1, cy], True))
                if min(x, newx) - 0.25 < cx:
                    toCheck.append(([cx - 1, cy], True))

                for coords, hori in toCheck:
                    type = self.checkForWalls(coords)
                    if type != 0:
                        coords = addVect(scaleVect(CELL_SIZE, coords), [10, 10])
                        log(
                            f"[{self.gameTime}] LINECAST start: {start} end: {end} success: {coords} {hori} {type}"
                        )
                        return coords, hori, type == 2

                x = newx

    def predictBullet(
        self, start, velocity, duration
    ) -> tuple[list[float], list[float]]:
        delta = scaleVect(duration, velocity)
        end = addVect(start, delta)

        result = self.linecastBounds(start, end)
        if result != None:
            end = result[0]

        wallResult = self.linecast(start, end)
        if wallResult != None:
            result = wallResult

        if result != None:
            pos, hori, destroy = result
            # destroy
            if destroy:
                return [-1000, -1000], velocity
            # bounce
            delta = addVect(delta, addVect(start, scaleVect(-1, pos)))
            if hori:
                velocity = [-velocity[0], velocity[1]]
                delta = [-delta[0], delta[1]]
            else:
                velocity = [velocity[0], -velocity[1]]
                delta = [delta[0], -delta[1]]

            return addVect(pos, delta), velocity
        else:
            return end, velocity

    def read_next_turn_data(self):
        """
        It's our turn! Read what the game has sent us and update the game info.
        :returns True if the game continues, False if the end game signal is received and the bot should be terminated
        """
        # Read and save the message
        self.current_turn_message = comms.read_message()

        self.startTime = time.time()

        if self.current_turn_message == comms.END_SIGNAL:
            return False

        # Delete the objects that have been deleted
        # NOTE: You might want to do some additional logic here. For example check if a powerup you were moving towards
        # is already deleted, etc.
        for deleted_object_id in self.current_turn_message["message"][
            "deleted_objects"
        ]:
            if deleted_object_id in self.pickups:
                self.pickups.remove(deleted_object_id)
            elif deleted_object_id in self.bullets:
                self.bullets.remove(deleted_object_id)
            try:
                # game_object = self.objects[deleted_object_id]
                # if game_object["type"] == ObjectTypes.DESTRUCTIBLE_WALL.value:
                #     pos = game_object["position"]
                #     x, y = worldToCell(pos[0], pos[1])
                #     self.destructables.set(x, y, False)
                #     log(f"[{self.gameTime}] [{x}, {y}] destroyed")
                # elif game_object["type"] == ObjectTypes.POWERUP.value:
                #     self.pickups.remove(deleted_object_id)
                # elif game_object["type"] == ObjectTypes.BULLET.value:
                #     self.bullets.remove(deleted_object_id)

                del self.objects[deleted_object_id]
            except KeyError:
                pass

        # Update your records of the new and updated objects in the game
        # NOTE: you might want to do some additional logic here. For example check if a new bullet has been shot or a
        # new powerup is now spawned, etc.
        self.objects.update(self.current_turn_message["message"]["updated_objects"])
        for updated_obj_id in self.current_turn_message["message"]["updated_objects"]:
            # already deleted
            if (
                updated_obj_id
                in self.current_turn_message["message"]["deleted_objects"]
            ):
                continue
            obj = self.objects[updated_obj_id]
            if obj["type"] == ObjectTypes.BULLET.value:
                self.bullets.add(updated_obj_id)
            elif (
                obj["type"] == ObjectTypes.POWERUP.value
                and obj["powerup_type"] != "SPEED"
            ):
                self.pickups.add(updated_obj_id)
        self.gameTime += DELTA_TIME

        log(f"[{self.gameTime}] pickups:{self.pickups}")
        log(f"[{self.gameTime}] bullets:{self.bullets}")

        return True

    def respond_to_turn(self):
        """
        This is where you should write your bot code to process the data and respond to the game.
        """
        selfPos = self.objects[self.tank_id]["position"]
        enemyPos = self.objects[self.enemy_id]["position"]

        deltaX = enemyPos[0] - selfPos[0]
        deltaY = enemyPos[1] - selfPos[1]

        sqrDist = deltaX * deltaX + deltaY * deltaY

        deltaPos = distanceSqr(self.oldPos, selfPos)

        action = {}

        removal = []
        bestPickup = None
        bestDist = self.width * self.width
        for pickup in self.pickups:
            pos = self.objects[pickup]["position"]
            if self.outsideBounds(pos, 60):
                removal.append(pickup)
            else:
                selfDist = distanceSqr(pos, selfPos)
                if selfDist < bestDist and selfDist < distanceSqr(pos, enemyPos):
                    log(f"[{self.gameTime}] Good powerup found!")
                    bestPickup = pos
                    bestDist = selfDist
        # remove out of bounds
        for a in removal:
            self.pickups.remove(a)

        # targetPos = bestPickup
        # targetV = []

        movement = {}

        # check los
        results = self.linecast(selfPos, enemyPos)
        log(f"[{self.gameTime}] Enemy linecast: {results}")
        if results == None:
            # can see
            action["shoot"] = vect2Angle(deltaX, deltaY)  # vect2Angle(v[0], v[1])
            if sqrDist > 150 * 150:
                # beeline
                movement = {"move": vect2Angle(deltaX, deltaY)}
            else:
                # too close
                # obstacle avoidance
                targetDir = [-deltaY * self.circlingDir, deltaX * self.circlingDir]
                end = addVect(selfPos, targetDir)
                result = self.linecastBounds(selfPos, end)
                if result != None:
                    end = result[0]
                newResult = self.linecast(selfPos, end)
                if newResult != None:
                    result = newResult

                if result != None and distanceSqr(result[0], selfPos) < 30 * 30:
                    log(f"[{self.gameTime}] cycle swap: {result}")
                    self.circlingDir *= -1
                elif deltaPos < 20 * 20:
                    log(f"[{self.gameTime}] cycle swap from lack of motion")
                    self.circlingDir *= -1

                # circling
                movement = {
                    "move": vect2Angle(
                        -deltaY * self.circlingDir, deltaX * self.circlingDir
                    )
                }
        else:
            # cannot see
            # shoot forwards
            if not self.lastLOS:
                l = sqrt(deltaX * deltaX + deltaY * deltaY)
                result = self.linecast(
                    selfPos, addVect(selfPos, [450 * deltaX / l, 450 * deltaY / l])
                )
                log(f"[{self.gameTime}] shoot prediction: {result}")
                if (
                    result == None
                    or result[2]
                    or distanceSqr(result[0], selfPos) > 130 * 130
                ):
                    action["shoot"] = vect2Angle(deltaX, deltaY)

            # path to enemy
            if sqrDist > 150 * 150:
                # track
                movement = {"path": enemyPos}
            else:
                # too close
                # obstacle avoidance
                targetDir = [-deltaY * self.circlingDir, deltaX * self.circlingDir]
                end = addVect(selfPos, targetDir)
                result = self.linecastBounds(selfPos, end)
                if result != None:
                    end = result[0]
                newResult = self.linecast(selfPos, end)
                if newResult != None:
                    result = newResult

                if result != None and distanceSqr(result[0], selfPos) < 20 * 20:
                    log(f"[{self.gameTime}] cycle swap: {result}")
                    self.circlingDir *= -1
                elif deltaPos < 20 * 20:
                    log(f"[{self.gameTime}] cycle swap from lack of motion")
                    self.circlingDir *= -1

                # circling
                movement = {
                    "move": vect2Angle(
                        -deltaY * self.circlingDir, deltaX * self.circlingDir
                    )
                }
        self.lastLOS = results == None

        # go for pickups
        if bestPickup:
            movement = {"path": bestPickup}

        # bullets
        dangerB = []
        # get all close bullets
        for bullet in self.bullets:
            bPos = self.objects[bullet]["position"]
            if distanceSqr(bPos, selfPos) < 300 * 300:
                dangerB.append((bPos, self.objects[bullet]["velocity"]))

        avoidDanger = [0.0, 0.0]
        for pos, vel in dangerB:
            newPos, newVel = self.predictBullet(pos, vel, DELTA_TIME)
            log(
                f"[{self.gameTime}] og pos:{pos} og vel:{vel} predict pos: {newPos} predict vel:{newVel}"
            )
            delta = addVect(newPos, scaleVect(-1, selfPos))
            delta[0] += 0.01
            sqrDist = delta[0] * delta[0] + delta[1] * delta[1]
            if sqrDist < 140 * 140:
                velSqr = newVel[0] * newVel[0] + newVel[1] * newVel[1] + 0.001
                dDotV = delta[0] * newVel[0] + delta[1] * newVel[1]
                dangerVect = addVect(
                    scaleVect(dDotV / velSqr, vel), scaleVect(-1, delta)
                )
                log(f"[{self.gameTime}] delta: {delta} calc dist:{dangerVect}")
                lengthSqr = distanceSqr(dangerVect, [0, 0]) + 0.001
                if lengthSqr < 60 * 60:
                    avoidDanger = addVect(
                        avoidDanger, scaleVect(40 / lengthSqr, dangerVect)
                    )

        log(f"[{self.gameTime}] bullet avoidance:{avoidDanger}")

        # avoid boundary
        bounds = self.getBoundary(self.gameTime)

        lowerDiff = addVect(selfPos, scaleVect(-1, bounds[0]))
        upperDiff = addVect(selfPos, scaleVect(-1, bounds[1]))
        # log(f"[{self.gameTime}] lowDiff:{lowerDiff} uppDiff:{upperDiff}")
        push = [0.0, 0.0]
        for i in [0, 1]:
            if lowerDiff[i] < -upperDiff[i]:
                push[i] = lowerDiff[i]
            else:
                push[i] = upperDiff[i]

            # ignore if far
            if abs(push[i]) > 100:
                push[i] = 0
            else:
                push[i] = 50 / push[i] + 0.001
        log(f"[{self.gameTime}] boundary avoidance:{push}")
        avoidDanger = addVect(avoidDanger, scaleVect(10, push))

        log(f"[{self.gameTime}] final avoidance:{avoidDanger}")
        if avoidDanger[0] != 0 or avoidDanger[1] != 0:
            movement = {"move": vect2Angle(avoidDanger[0], avoidDanger[1])}

        safePos = [self.width / 2 + 100, self.height / 2]
        # endgame
        if bounds[1][1] - bounds[0][1] < 150:
            log(f"[{self.gameTime}] End game")
            if distanceSqr(safePos, selfPos) < 30 * 30:
                movement = {"move": -1}
            else:
                movement = {"path": safePos}
        # unstuck
        elif deltaPos < 3 * 3:
            log(f"[{self.gameTime}] UNSTICKING!")
            # action["shoot"] = 0
            if distanceSqr(safePos, selfPos) < 30 * 30:
                movement = {"move": -1}
            else:
                movement = {"path": safePos}

        action.update(movement)

        self.oldPos = selfPos
        self.turnCount += 1
        log(f"[{self.gameTime}] Bounds: {bounds}")
        log(
            f"[{self.gameTime}] Action: {action}Time taken: {time.time() - self.startTime}"
        )
        comms.post_message(action)
