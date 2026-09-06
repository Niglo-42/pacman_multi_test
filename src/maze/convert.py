from ..game_logic.direction import Dir
from .maze import Maze


class Convert:
    # - 16 = external walls
    match_int = (
        ((1, 1, 1), (1, 1, 1), (1, 1, 1)),
        ((24, 24, 24), (1, 1, 1), (1, 1, 1)),  # N
        ((1, 1, 25), (1, 1, 25), (1, 1, 25)),  # E
        ((24, 24, 21), (1, 1, 25), (1, 1, 25)),  # NE
        ((1, 1, 1), (1, 1, 1), (26, 26, 26)),  # S
        ((24, 24, 24), (1, 1, 1), (26, 26, 26)),  # SN
        ((1, 1, 25), (1, 1, 25), (26, 26, 22)),  # SE
        ((24, 24, 21), (1, 1, 25), (26, 26, 22)),  # SEN
        ((27, 1, 1), (27, 1, 1), (27, 1, 1)),  # W
        ((20, 24, 24), (27, 1, 1), (27, 1, 1)),  # WN
        ((27, 1, 25), (27, 1, 25), (27, 1, 25)),  # WE
        ((20, 24, 21), (27, 1, 25), (27, 1, 25)),  # WEN
        ((27, 1, 1), (27, 1, 1), (23, 26, 26)),  # WS
        ((20, 24, 24), (27, 1, 1), (23, 26, 26)),  # WSN
        ((27, 1, 25), (27, 1, 25), (23, 26, 22)),  # WSE
        ((20, 24, 21), (27, 0, 25), (23, 26, 22)),  # WSEN
    )

    corner_match = [
        # 0 not applicated
        (0, 0, 0, 0),
        (0, 0, 18, 19),  # n
        (16, 0, 0, 19),  # e
        (0, 0, 0, 19),
        (16, 17, 0, 0),  # s
        (0, 0, 0, 0),
        (16, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 17, 18, 0),  # w
        (0, 0, 18, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 17, 0, 0),  # ws
        (0, 0, 0, 0),
        (0, 0, 0, 0),
        (0, 0, 0, 0)
    ]

    @staticmethod
    def get_trad(cardinal, val) -> list[list[int]]:
        def is_only_one_wall(cardinal) -> bool:
            return cardinal != 0 and not cardinal & (cardinal - 1)
        res = [list(row) for row in Convert.match_int[val]]
        if cardinal == 0:
            return res
        if cardinal & 1:
            res[0] = [x - 16 if x > 16 else x
                      for x in res[0]]
        if cardinal & 2:
            for row in res:
                if row[2] > 16:
                    row[2] -= 16
        if cardinal & 4:
            res[2] = [x - 16 if x > 16 else x
                      for x in res[2]]
        if cardinal & 8:
            for row in res:
                if row[0] > 16:
                    row[0] -= 16
        if is_only_one_wall(cardinal):
            if cardinal & 1:
                if val & Dir.E.bit:
                    res[0][2] = 29
                if val & Dir.W.bit:
                    res[0][0] = 28
            if cardinal & 2:
                if val & Dir.S.bit:
                    res[2][2] = 14
                if val & Dir.N.bit:
                    res[0][2] = 13
            if cardinal & 4:
                if val & Dir.E.bit:
                    res[2][2] = 30
                if val & Dir.W.bit:
                    res[2][0] = 31
            if cardinal & 8:
                if val & Dir.S.bit:
                    res[2][0] = 15
                if val & Dir.N.bit:
                    res[0][0] = 12
        return res

    def modify_corner(grid, corner, row, col) -> list[list[list | list[int]]]:
        for y in range(row):
            for x in range(col):
                current = corner[y * col + x]
                offset = y * col + x
                if current[0]:
                    grid[y][x][2][2] = corner[offset][0]
                if current[1]:
                    grid[y][x + 1][2][0] = corner[offset][1]
                if current[2]:
                    grid[y + 1][x + 1][0][0] = corner[offset][2]
                if current[3]:
                    grid[y + 1][x][0][2] = corner[offset][3]
        return grid

    @staticmethod
    def cell2tiles(maze: Maze) -> list[list[int]]:
        def isnot_last_row_or_col(x, y, w, h) -> bool:
            return x < w - 1 and y < h - 1

        def get_external_walls(x, y, w, h) -> int:
            res = 0
            if (y == 0):
                res |= 1
            if x == w - 1:
                res |= 2
            if y == h - 1:
                res |= 4
            if x == 0:
                res |= 8
            return res
        tiles = []
        corners = []
        for y in range(maze.height):
            tiles.append([])
            for x in range(maze.width):
                cardinal = get_external_walls(x, y, maze.width, maze.height)
                tiles[y].append(Convert.get_trad(cardinal, maze.grid[y][x]))
                if isnot_last_row_or_col(x, y, maze.width, maze.height):
                    corners.append(
                        Convert.corner_match[Convert.get_corner(maze, y, x)])
        tiles = Convert.modify_corner(
            tiles, corners, maze.height - 1, maze.width - 1)
        tiles = Convert.flat(tiles, maze.width, maze.height)
        return tiles

    def flat(tiles: list[list[list[list[int]]]], w, h) -> list[list[int]]:
        row = []
        for y in range(h):
            for one_third in range(3):
                col = []
                for x in range(w):
                    col.extend(tiles[y][x][one_third])
                row.append(col)
        return row

    @staticmethod
    def get_corner(maze, y, x) -> int:
        res = 0
        current = maze.grid[y][x]
        right = maze.grid[y][x + 1]
        bottom = maze.grid[y + 1][x]
        if current & Dir.E.bit:
            res |= Dir.N.bit
        if current & Dir.S.bit:
            res |= Dir.W.bit
        if right & Dir.S.bit:
            res |= Dir.E.bit
        if bottom & Dir.E.bit:
            res |= Dir.S.bit
        return res
