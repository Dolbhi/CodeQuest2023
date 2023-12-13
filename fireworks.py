"""
Test:
12 7 3
3 3
8 4
10 2

"""

parameters = input().split(" ")
w = int(parameters[0])
h = int(parameters[1])
f = int(parameters[2])

"""
5.....#
4....##
3...###
2..####
1.#####
0######
"""


def getFullFillHeight(x, y):
    return y + min(x, w - x - 1) - w + 1


highestIndex = 0
highestWork = 0

fullFill = -1

fireworks = []
for i in range(f):
    data = input().split(" ")
    workCoords = (int(data[0]), int(data[1]))
    if workCoords[1] > highestWork:
        highestIndex = i
        highestWork = workCoords[1]

    newFill = getFullFillHeight(workCoords[0], workCoords[1])
    if newFill > fullFill:
        fullFill = newFill

    fireworks.append(workCoords)

x = 10
y = 10

print(str(parameters))
for i in range(f):
    print(fireworks[i])

print(f"highestWork: {highestWork} fullFill: {fullFill}")
