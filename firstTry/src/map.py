CELL_SIZE = 20


def worldToCell(x, y) -> tuple[int, int]:
    x //= CELL_SIZE
    y //= CELL_SIZE
    return int(x), int(y)


def cellToWorld(x, y) -> tuple[float, float]:
    return x * CELL_SIZE + CELL_SIZE / 2, y * CELL_SIZE + CELL_SIZE / 2


# print((10.2 - 1) // 32 + 1)


class Map:
    def __init__(self, cellWidth: int, cellHeight: int):
        self.cells: list[list[int]] = []
        self.width = cellWidth
        self.height = cellHeight
        for i in range(cellWidth):
            count = (cellHeight - 1) // 32 + 1
            column: list[int] = []
            for j in range(count):
                column.append(0)
            self.cells.append(column)

    def __str__(self):
        output = ""

        for columb in self.cells:
            line = "\n"
            for bitmap in columb:
                bitString = str(bin(bitmap))[2:].rjust(32, "0")
                line = bitString + line
            output += line[-self.height :]

        return output

    def set(self, x: int, y: int, toSet: bool):
        if x < 0 or x >= self.width or y < 0 or y >= self.width:
            return False

        count = y // 32
        bitIndex = y - count * 32
        bitmap = self.cells[x][count]

        mask = 1 << bitIndex
        if toSet:
            self.cells[x][count] |= mask
        else:
            self.cells[x][count] &= ~mask

    def get(self, x: int, y: int) -> bool:
        if x < 0 or x >= self.width or y < 0 or y >= self.width:
            return False

        count = y // 32
        bitIndex = y - count * 32
        bitmap = self.cells[x][count]

        mask = 1 << bitIndex
        return mask & bitmap != 0


# map = Map(50, 50)
# map.set(1, 1, True)
# map.set(2, 2, True)
# map.set(3, 3, True)
# map.set(1, 3, True)
# map.set(3, 1, True)
# map.set(4, 1, True)

# map.set(10, 1, True)
# map.set(11, 1, True)
# map.set(12, 1, True)
# map.set(13, 1, True)
# map.set(12, 1, False)
# print(map)
