import time
import random
from machine import Pin, SPI, ADC
from ili9225 import ILI9225

# --- [1. 핀 설정] ---
spi = SPI(2, baudrate=20000000, sck=Pin(18), mosi=Pin(23))
lcd = ILI9225(spi, Pin(5, Pin.OUT), Pin(2, Pin.OUT), Pin(4, Pin.OUT))

vx = ADC(Pin(34))
vy = ADC(Pin(35))
sw = Pin(32, Pin.IN, Pin.PULL_UP)
vx.atten(ADC.ATTN_11DB)
vy.atten(ADC.ATTN_11DB)

# --- [2. 게임 설정] ---
COLS = 10
ROWS = 18
CELL_SIZE = 10
OFFSET_X = 38
OFFSET_Y = 20

SHAPES = [
    [[1, 1, 1, 1]],
    [[1, 1], [1, 1]],
    [[0, 1, 0], [1, 1, 1]],
    [[1, 1, 0], [0, 1, 1]],
    [[0, 1, 1], [1, 1, 0]],
    [[1, 0, 0], [1, 1, 1]],
    [[0, 0, 1], [1, 1, 1]]
]

COLORS = [0xF800, 0x07E0, 0x001F, 0xFFE0, 0xF81F, 0x07FF, 0x7BEF]

class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        self.board = [[0] * COLS for _ in range(ROWS)]
        self.score = 0
        self.game_over = False
        self.new_piece()

    def new_piece(self):
        self.piece = random.choice(SHAPES)
        self.color = random.choice(COLORS)
        self.px = COLS // 2 - len(self.piece[0]) // 2
        self.py = 0
        if self.check_collision(self.px, self.py, self.piece):
            self.game_over = True

    def check_collision(self, x, y, piece):
        for r, row in enumerate(piece):
            for c, val in enumerate(row):
                if val:
                    if x + c < 0 or x + c >= COLS or y + r >= ROWS:
                        return True
                    if self.board[y + r][x + c]:
                        return True
        return False

    def rotate(self, piece):
        return [list(row) for row in zip(*piece[::-1])]

    def lock_piece(self):
        for r, row in enumerate(self.piece):
            for c, val in enumerate(row):
                if val:
                    self.board[self.py + r][self.px + c] = self.color
        self.clear_lines()
        self.new_piece()

    def clear_lines(self):
        new_board = [row for row in self.board if any(v == 0 for v in row)]
        lines = ROWS - len(new_board)
        for _ in range(lines):
            new_board.insert(0, [0] * COLS)
        self.board = new_board
        self.score += lines * 100

    def draw(self):
        lcd.fill(0x0000)
        lcd.rect(OFFSET_X-2, OFFSET_Y-2, COLS*CELL_SIZE+4, ROWS*CELL_SIZE+4, 0xFFFF)

        for r in range(ROWS):
            for c in range(COLS):
                if self.board[r][c]:
                    lcd.fill_rect(
                        OFFSET_X + c*CELL_SIZE,
                        OFFSET_Y + r*CELL_SIZE,
                        CELL_SIZE-1,
                        CELL_SIZE-1,
                        self.board[r][c]
                    )

        for r, row in enumerate(self.piece):
            for c, val in enumerate(row):
                if val:
                    lcd.fill_rect(
                        OFFSET_X + (self.px + c)*CELL_SIZE,
                        OFFSET_Y + (self.py + r)*CELL_SIZE,
                        CELL_SIZE-1,
                        CELL_SIZE-1,
                        self.color
                    )

        lcd.text(f"Score:{self.score}", 10, 5, 0xFFFF)
        lcd.show()

def wait_reset():
    press_time = None
    while True:
        if sw.value() == 0:
            if press_time is None:
                press_time = time.ticks_ms()
            elif time.ticks_diff(time.ticks_ms(), press_time) > 800:
                return
        else:
            press_time = None
        time.sleep_ms(50)

def main():
    game = Tetris()
    last_fall = time.ticks_ms()

    while True:
        while not game.game_over:
            now = time.ticks_ms()

            # 🔽 점수에 따른 속도 증가
            level = game.score // 1000
            fall_interval = max(500 - level * 50, 100)

            x = vx.read()
            y = vy.read()

            if x < 500 and not game.check_collision(game.px - 1, game.py, game.piece):
                game.px -= 1
                time.sleep_ms(100)
            elif x > 3500 and not game.check_collision(game.px + 1, game.py, game.piece):
                game.px += 1
                time.sleep_ms(100)

            if y < 500:
                rotated = game.rotate(game.piece)
                if not game.check_collision(game.px, game.py, rotated):
                    game.piece = rotated
                time.sleep_ms(150)
            elif y > 3500 and not game.check_collision(game.px, game.py + 1, game.piece):
                game.py += 1

            if time.ticks_diff(now, last_fall) > fall_interval:
                if not game.check_collision(game.px, game.py + 1, game.piece):
                    game.py += 1
                else:
                    game.lock_piece()
                last_fall = now

            game.draw()

        # 🎮 GAME OVER 화면
        lcd.fill(0x0000)
        lcd.text("GAME OVER", 45, 90, 0xF800)
        lcd.text("HOLD BUTTON", 40, 110, 0xFFFF)
        lcd.text("TO RESTART", 42, 130, 0xFFFF)
        lcd.show()

        wait_reset()
        game.reset()
        last_fall = time.ticks_ms()

main()
