import pygame
import numpy as np
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

        # Drawing state
        self.drawing = False
        self.drawing_color = None
        self.locked_by = None
        self.pixel_grid = np.zeros((SQUARE_SIZE, SQUARE_SIZE))  # Track colored pixels
        
    def draw(self, screen):
        # Draw base square
        pygame.draw.rect(screen, (255, 255, 255), self.rect)
        
        # Draw colored pixels if drawing
        if self.drawing_color:
            color = pygame.Color(self.drawing_color)
            for y in range(SQUARE_SIZE):
                for x in range(SQUARE_SIZE):
                    if self.pixel_grid[y][x] > 0:
                        screen.set_at((self.rect.x + x, self.rect.y + y), color)
        
        # Draw claimed color if fully claimed
        if self.claimed_by:
            pygame.draw.rect(screen, pygame.Color(self.claimed_by), self.rect)
        
        # Draw border
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)

    def contains(self, pos):
        return self.rect.collidepoint(pos)
    
    def start_drawing(self, color):
        if self.claimed_by is None and self.locked_by is None:
            self.drawing = True
            self.drawing_color = color
            self.locked_by = color
            self.pixel_grid.fill(0)  # Reset pixel grid
    
    def update_drawing(self, mouse_pos):
        if self.drawing and self.contains(mouse_pos):
            # Convert mouse position to local square coordinates
            local_x = mouse_pos[0] - self.rect.x
            local_y = mouse_pos[1] - self.rect.y
            
            # Color a 5x5 area around the mouse for smoother drawing
            for dy in range(-2, 3):
                for dx in range(-2, 3):
                    px = local_x + dx
                    py = local_y + dy
                    if 0 <= px < SQUARE_SIZE and 0 <= py < SQUARE_SIZE:
                        self.pixel_grid[py][px] = 1
    
    def stop_drawing(self):
        if self.drawing:
            # Calculate percentage filled
            filled_pixels = np.sum(self.pixel_grid)
            total_pixels = SQUARE_SIZE * SQUARE_SIZE
            percentage = (filled_pixels / total_pixels) * 100
            
            if percentage >= 50:  # 50% threshold
                self.claimed_by = self.drawing_color
            
            self.reset_drawing()
    
    def reset_drawing(self):
        self.drawing = False
        self.drawing_color = None
        self.locked_by = None
        self.pixel_grid.fill(0)

class GameBoard:
    def __init__(self, network_manager):   
        self.network = network_manager
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.squares = [[Square(r, c) for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
        self.clock = pygame.time.Clock()
        self.running = True
        self.mouse_down = False
        self.current_square = None  # Track which square is being drawn on
        self.other_cursors = {}

        self.player_colors = {}
        self.pen_images = {}
        self.cursor_img = None
        self.my_color = None

        self.winner = None

        self.assign_colors()
        self.load_pen_images()
        self.update_cursor()

        self.network.set_message_handler(self.handle_game_message)

    def assign_colors(self):
        with self.network.lock:
            for i, name in enumerate(self.network.players):
                self.player_colors[name] = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            self.my_color = self.player_colors[self.network.username]
        self.update_cursor()

    def load_pen_images(self):
        for color in PLAYER_COLORS:
            try:
                img = pygame.image.load(f"../images/{color}_pen.png").convert_alpha()
                img = pygame.transform.scale(img, (40, 40))
                
                scale_factor = 40 / 1024
                offset_x = int(170 * scale_factor)
                offset_y = int(840 * scale_factor)
                
                self.pen_images[color] = {
                    'image': img,
                    'offset': (offset_x, offset_y)
                }
            except Exception as e:
                print(f"Missing or failed to load image: pens/{color}_pen.png")
                self.pen_images[color] = {
                    'image': None,
                    'offset': (0, 0)
                }

    def update_cursor(self):
        x, y = pygame.mouse.get_pos()
        self.network.send_game_command(f"CURSOR:{self.my_color}:{x},{y}")

        if self.my_color and self.pen_images.get(self.my_color, {}).get('image'):
            self.cursor_img = self.pen_images[self.my_color]
            pygame.mouse.set_visible(False)
        else:
            self.cursor_img = None
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
        # Draw your own cursor
        if self.cursor_img and self.cursor_img['image']:
            x, y = pygame.mouse.get_pos()
            offset_x, offset_y = self.cursor_img['offset']
            self.screen.blit(
                self.cursor_img['image'], 
                (x - offset_x, y - offset_y)
            )

        # Draw other players' cursors
        for color, (x, y) in self.other_cursors.items():
            img_data = self.pen_images.get(color)
            if img_data and img_data['image']:
                offset_x, offset_y = img_data['offset']
                self.screen.blit(
                    img_data['image'],
                    (x - offset_x, y - offset_y)
                )

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.network.quit()

            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down = True
                self.handle_mouse_down(pygame.mouse.get_pos())

            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_down = False
                self.handle_mouse_up()

            elif event.type == pygame.MOUSEMOTION and self.mouse_down:
                self.handle_mouse_motion(pygame.mouse.get_pos())

    def handle_mouse_down(self, pos):
        if self.winner:
            return
        
        for row in self.squares:
            for square in row:
                if square.contains(pos):
                    square.start_drawing(self.my_color)
                    self.current_square = square
                    return

    def handle_mouse_motion(self, pos):
        if self.winner or not self.current_square:
            return

        # Check if we left the current square
        if not self.current_square.contains(pos):
            self.network.send_game_command(
                f"RESET:{self.current_square.row},{self.current_square.col}"
            )
            self.current_square.reset_drawing()
            self.current_square = None
            return
        
        self.current_square.update_drawing(pos)
        local_x = pos[0] - self.current_square.rect.x
        local_y = pos[1] - self.current_square.rect.y
        self.network.send_game_command(
            f"DRAW:{self.current_square.row},{self.current_square.col}:{local_x},{local_y}:{self.my_color}"
        )
        #print(f"[SEND] DRAW:{self.current_square.row},{self.current_square.col}:{local_x},{local_y}:{self.my_color}", flush=True)

    def handle_mouse_up(self):
        if self.winner or not self.current_square:
            return
        
        if self.current_square.drawing:
            filled_pixels = np.sum(self.current_square.pixel_grid)
            total_pixels = SQUARE_SIZE * SQUARE_SIZE
            percentage = (filled_pixels / total_pixels) * 100

            if percentage < 50:
                self.network.send_game_command(
                    f"RESET:{self.current_square.row},{self.current_square.col}"
                )
            elif percentage >= 50:
                self.network.send_game_command(
                    f"CLAIM:{self.current_square.row},{self.current_square.col}:{self.my_color}"
                )
        
        self.current_square.stop_drawing()
        self.current_square = None

    def handle_click(self, pos):
        if self.winner:
            return
        if any(sq.animating and sq.locked_by == self.my_color for row in self.squares for sq in row):
            return

        for row in self.squares:
            for square in row:
                if square.contains(pos):
                    if square.animating or square.locked_by is not None or square.claimed_by is not None:
                        return

                    self.network.send_game_command(f"CLAIM:{square.row},{square.col}:{self.my_color}")
                    return

    def handle_game_message(self, message):
        if message.startswith("GAME:CLAIM:"):
            try:
                _, data = message.split("GAME:CLAIM:")
                coord_str, color = data.split(":")
                row, col = map(int, coord_str.split(","))
                square = self.squares[row][col]
                if square.claimed_by is not None:
                    return
                square.claimed_by = color
                square.animating = True
                square.animation_progress = 0
                square.locked_by = None
            except Exception as e:
                print(f"Invalid message: {message} ({e})")

        elif message.startswith("GAME:DRAW:"):
            #print(f"[RECV] {message}", flush=True)
            try:
                _, data = message.split("GAME:DRAW:")
                coord_str, pixel_str, color = data.split(":")
                row, col = map(int, coord_str.split(","))
                px, py = map(int, pixel_str.split(","))
                square = self.squares[row][col]

                if square.locked_by is None:
                    square.locked_by = color
                    square.drawing = True
                    square.drawing_color = color

                # Apply 5x5 brush centered at (px, py)
                for dy in range(-2, 3):
                    for dx in range(-2, 3):
                        brush_px = px + dx
                        brush_py = py + dy
                        if 0 <= brush_px < SQUARE_SIZE and 0 <= brush_py < SQUARE_SIZE:
                            square.pixel_grid[brush_py][brush_px] = 1

            except Exception as e:
                print(f"Invalid DRAW message: {message} ({e})")

        elif message.startswith("GAME:RESET:"):
            try:
                _, coord_str = message.split("GAME:RESET:")
                row, col = map(int, coord_str.split(","))
                square = self.squares[row][col]
                square.reset_drawing()
            except Exception as e:
                print(f"Invalid RESET message: {message} ({e})")

        elif message.startswith("GAME:CURSOR:"):
            try:
                _, data = message.split("GAME:CURSOR:")
                color, pos_str = data.split(":")
                if color != self.my_color:  # Don't track your own
                    x, y = map(int, pos_str.split(","))
                    self.other_cursors[color] = (x, y)
            except Exception as e:
                print(f"Invalid CURSOR message: {message} ({e})")


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
