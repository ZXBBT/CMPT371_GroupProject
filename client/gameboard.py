import pygame
from network import NetworkManager

pygame.init()
pygame.font.init()

GRID_SIZE = 8
SQUARE_SIZE = 80
SIDE_WIDTH = 180
WIDTH = SIDE_WIDTH + GRID_SIZE * SQUARE_SIZE
HEIGHT = GRID_SIZE * SQUARE_SIZE

FONT = pygame.font.SysFont("Arial", 18)
PLAYER_COLORS = ["red", "blue", "green", "pink"]

class Square:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.rect = pygame.Rect(SIDE_WIDTH + col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        self.claimed_by = None

    def draw(self, screen):
        color = (255, 255, 255) if not self.claimed_by else pygame.Color(self.claimed_by)
        pygame.draw.rect(screen, color, self.rect)
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)

    def contains(self, pos):
        return self.rect.collidepoint(pos)

class GameBoard:
    def __init__(self, network_manager):
        self.network = network_manager
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.squares = [[Square(r, c) for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
        self.clock = pygame.time.Clock()
        self.running = True

        self.player_colors = {}
        self.pen_images = {}
        self.cursor_img = None
        self.my_color = None

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
        for name in self.network.players:
            color = self.player_colors.get(name, "black")
            pygame.draw.rect(self.screen, pygame.Color(color), (20, y, 20, 20))
            self.screen.blit(FONT.render(name, True, (0, 0, 0)), (50, y))
            y += 30

    def draw_board(self):
        for row in self.squares:
            for square in row:
                square.draw(self.screen)

    def run(self):
        while self.running and self.network.running:
            self.assign_colors()  # continuously sync
            self.update_cursor()
            self.handle_events()
            self.screen.fill((255, 255, 255))
            self.draw_players()
            self.draw_board()
            self.draw_cursor()
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
        for row in self.squares:
            for square in row:
                if square.contains(pos) and square.claimed_by is None:
                    square.claimed_by = self.my_color
                    self.network.send_game_command(f"CLAIM:{square.row},{square.col}:{self.my_color}")

if __name__ == "__main__":
    net = NetworkManager("brandonyang", 25565, is_host=True)
    board = GameBoard(net)
    board.run()
