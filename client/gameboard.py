import pygame
from network import NetworkManager

pygame.init()
pygame.font.init()

GRID_SIZE = 8
SQUARE_SIZE = 80
SIDE_WIDTH = 180
WIDTH = SIDE_WIDTH + GRID_SIZE * SQUARE_SIZE
HEIGHT = GRID_SIZE * SQUARE_SIZE

ANIMATION_SPEED = 2
WIN_REQUIRE = 30

FONT = pygame.font.SysFont("Arial", 18)
BIG_FONT = pygame.font.SysFont("Arial", 64)
PLAYER_COLORS = ["red", "blue", "green", "pink"]

class Square:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.rect = pygame.Rect(SIDE_WIDTH + col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        self.claimed_by = None

        # Animation and lock
        self.animating = False
        self.locked_by = None
        self.animation_progress = 0


    def draw(self, screen):
        if self.claimed_by:
            if self.animating:
                # Animation part
                progress_height = int(SQUARE_SIZE * (self.animation_progress / 100))
                partial_rect = pygame.Rect(
                    self.rect.x,
                    self.rect.y + (SQUARE_SIZE - progress_height),
                    SQUARE_SIZE,
                    progress_height
                )
                color = pygame.Color(self.claimed_by)
                pygame.draw.rect(screen, color, partial_rect)
            else:
                pygame.draw.rect(screen, pygame.Color(self.claimed_by), self.rect)

        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)

    def contains(self, pos):
        return self.rect.collidepoint(pos)

class GameBoard:
    def __init__(self, network_manager):   
        self.network = network_manager
        self.network.set_message_handler(self.handle_game_message)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.squares = [[Square(r, c) for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
        self.clock = pygame.time.Clock()
        self.running = True

        self.player_colors = {}
        self.pen_images = {}
        self.cursor_img = None
        self.my_color = None

        self.winner = None

        self.assign_colors()
        self.load_pen_images()
        self.update_cursor()

    def assign_colors(self):
        with self.network.lock:
            for i, name in enumerate(self.network.players):
                self.player_colors[name] = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            self.my_color = self.player_colors[self.network.username]

    def load_pen_images(self):
        for color in PLAYER_COLORS:
            try:
                img = pygame.image.load(f"../images/{color}_pen.png").convert_alpha()
                self.pen_images[color] = pygame.transform.scale(img, (40, 40))
            except Exception as e:
                print(f"Missing or failed to load image: pens/{color}_pen.png")

        self.cursor_img = self.pen_images.get(self.my_color)

    def update_cursor(self):
        if self.cursor_img:
            pygame.mouse.set_visible(False)
        else:
            pygame.mouse.set_visible(True)

    def draw_players(self):
        y = 20
        self.screen.blit(FONT.render("Players:", True, (0, 0, 0)), (20, y))
        y += 30
        percentages = self.calculate_ownership()
        for name in self.network.players:
            color = self.player_colors.get(name, "black")
            percent = percentages.get(name, 0)
            label = f"{name} ({percent}%)"

            pygame.draw.rect(self.screen, pygame.Color(color), (20, y, 20, 20))
            self.screen.blit(FONT.render(label, True, (0, 0, 0)), (50, y))
            y += 30

    def draw_board(self):
        for row in self.squares:
            for square in row:
                square.draw(self.screen)

    def run(self):
        while self.running and self.network.running:
            #self.assign_colors()  # continuously sync
            self.update_cursor()
            self.handle_events()
            self.update_animations()
            self.screen.fill((255, 255, 255))
            self.draw_players()
            self.draw_board()
            self.draw_cursor()

            if not self.winner:
                percentages = self.calculate_ownership()
                for name, percent in percentages.items():
                    if percent >= WIN_REQUIRE:
                        self.winner = name
                        break

            if self.winner:
                self.draw_victory_screen(self.winner)

            pygame.display.flip()
            self.clock.tick(60)

    def draw_cursor(self):
        if self.cursor_img:
            x, y = pygame.mouse.get_pos()
            self.screen.blit(self.cursor_img, (x - 20, y - 20))

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.network.quit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.handle_click(pygame.mouse.get_pos())

    def handle_click(self, pos):
        if self.winner:
            return
        if any(sq.animating and sq.locked_by == self.my_color for row in self.squares for sq in row):
            return

        for row in self.squares:
            for square in row:
                if square.contains(pos):
                    if square.animating or square.locked_by is not None or square.claimed_by == self.my_color:
                        return

                    square.locked_by = self.my_color
                    square.animating = True
                    square.animation_progress = 0
                    square.claimed_by = self.my_color
                    self.network.send_game_command(f"CLAIM:{square.row},{square.col}:{self.my_color}")
                    return

    def handle_game_message(self, message):
        if message.startswith("GAME:CLAIM:"):
            try:
                _, data = message.split("GAME:CLAIM:")
                coord_str, color = data.split(":")
                row, col = map(int, coord_str.split(","))
                if 0 <= row < GRID_SIZE and 0 <= col < GRID_SIZE:
                    square = self.squares[row][col]
                    if square.animating or square.locked_by is not None:
                        return
                    square.claimed_by = color
                    square.animating = True
                    square.animation_progress = 0
                    square.locked_by = None
            except Exception as e:
                print(f"Invalid message: {message} ({e})")

    def update_animations(self):
        for row in self.squares:
            for square in row:
                if square.animating:
                    square.animation_progress += ANIMATION_SPEED
                    if square.animation_progress >= 100:
                        square.animating = False
                        square.animation_progress = 100
                        square.locked_by = None

    def calculate_ownership(self):
        color_to_player = {v: k for k, v in self.player_colors.items()}
        counts = {name: 0 for name in self.player_colors}
        total = GRID_SIZE * GRID_SIZE

        for row in self.squares:
            for square in row:
                player_name = color_to_player.get(square.claimed_by)
                if player_name:
                    counts[player_name] += 1

        percentages = {}
        for name, count in counts.items():
            percentages[name] = int((count / total) * 100)

        return percentages
    
    def draw_victory_screen(self, winner_name):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((255, 255, 255))
        self.screen.blit(overlay, (0, 0))

        text = BIG_FONT.render(f"{winner_name} wins!", True, (0, 0, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(text, text_rect)



if __name__ == "__main__":
    net = NetworkManager("brandonyang", 25565, is_host=True)
    board = GameBoard(net)
    board.run()
