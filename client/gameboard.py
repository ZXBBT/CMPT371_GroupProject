# Implements the main game board and drawing logic for a multiplayer grid-based game
# Handles network communication, user input, and game state updates

import os
import pygame
import numpy as np
from network import NetworkManager
from utils import Button
import time

pygame.init()
pygame.font.init()
ASSETS_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'images'))
GRID_SIZE = 8
SQUARE_SIZE = 80
SIDE_WIDTH = 180
WIDTH = SIDE_WIDTH + GRID_SIZE * SQUARE_SIZE
HEIGHT = GRID_SIZE * SQUARE_SIZE
ANIMATION_SPEED = 2
FONT = pygame.font.SysFont("Arial", 18)
BIG_FONT = pygame.font.SysFont("Arial", 64)
PLAYER_COLORS = ["red", "blue", "green", "pink"]

# Represents a single grid square that can be drawn on by a player
class Square:
    def __init__(self, row, col):
        self.row = row
        self.col = col
        self.rect = pygame.Rect(SIDE_WIDTH + col * SQUARE_SIZE, row * SQUARE_SIZE, SQUARE_SIZE, SQUARE_SIZE)
        self.claimed_by = None
        self.drawing = False
        self.drawing_color = None
        self.locked_by = None
        self.pixel_grid = np.zeros((SQUARE_SIZE, SQUARE_SIZE))
    
    # Render the square's current state
    def draw(self, screen):
        if not self.claimed_by:
            pygame.draw.rect(screen, (255, 255, 255), self.rect)
            if self.drawing and self.drawing_color:
                color = pygame.Color(self.drawing_color)
                for y in range(SQUARE_SIZE):
                    for x in range(SQUARE_SIZE):
                        if self.pixel_grid[y][x]:
                            screen.fill(color, (self.rect.x + x, self.rect.y + y, 1, 1))
        else:
            pygame.draw.rect(screen, pygame.Color(self.claimed_by), self.rect)
        
        pygame.draw.rect(screen, (0, 0, 0), self.rect, 2)

    # Check if a position is inside the square
    def contains(self, pos):
        return self.rect.collidepoint(pos)
    
    # Begin drawing on this square with the player's color if it's available
    def start_drawing(self, color):
        if self.claimed_by is None and self.locked_by is None:
            self.drawing = True
            self.drawing_color = color
            self.locked_by = color
            self.pixel_grid.fill(0)
    
    # Mark pixels in the square as filled based on mouse movement
    def update_drawing(self, mouse_pos):
        if self.drawing and self.contains(mouse_pos):
            local_x = mouse_pos[0] - self.rect.x
            local_y = mouse_pos[1] - self.rect.y
            
            for dy in range(-4, 6):
                for dx in range(-4, 6):
                    px = local_x + dx
                    py = local_y + dy
                    if 0 <= px < SQUARE_SIZE and 0 <= py < SQUARE_SIZE:
                        self.pixel_grid[py][px] = 1
    
    # Stop drawing and claim the square if more than 50% is filled
    def stop_drawing(self):
        if self.drawing:
            filled_pixels = np.sum(self.pixel_grid)
            total_pixels = SQUARE_SIZE * SQUARE_SIZE
            percentage = (filled_pixels / total_pixels) * 100
            if percentage >= 50:
                self.claimed_by = self.drawing_color
            
            self.reset_drawing()
    
    # Clear the drawing state of the square
    def reset_drawing(self):
        self.drawing = False
        self.drawing_color = None
        self.locked_by = None
        self.pixel_grid.fill(0)

# Main game interface and logic for handling drawing, network updates, and gameplay
class GameBoard:
    def __init__(self, network_manager):   
        self.network = network_manager
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.squares = [[Square(r, c) for c in range(GRID_SIZE)] for r in range(GRID_SIZE)]
        self.clock = pygame.time.Clock()
        self.running = True
        self.mouse_down = False
        self.current_square = None
        self.other_cursors = {}
        self.last_draw_time = 0
        self.last_cursor_update = 0
        self.last_cursor_pos = (0, 0)
        self.player_colors = {}
        self.pen_images = {}
        self.cursor_img = None
        self.my_color = None
        self.winner = None
        self.assign_colors()
        self.load_pen_images()
        self.update_cursor()

        self.network.set_message_handler(self.handle_game_message)
        self.exit_button = Button("EXIT", 20, HEIGHT - 60, 150, 50, self.return_to_main_menu)
        self.mainmenu_button = Button("Main Menu", WIDTH // 2 - 75, HEIGHT // 2 + 40, 150, 50, self.return_to_main_menu)
        self.network.set_player_update_handler(self.handle_player_update)
    
    # Update internal player list and remove cursors of players who left
    def handle_player_update(self, players):
        active_colors = set(self.player_colors.get(p) for p in players if p in self.player_colors)
        stale_cursors = [color for color in self.other_cursors if color not in active_colors]
        for color in stale_cursors:
            del self.other_cursors[color]

    # Assign a unique color to each player
    def assign_colors(self):
        with self.network.lock:
            for i, name in enumerate(self.network.players):
                self.player_colors[name] = PLAYER_COLORS[i % len(PLAYER_COLORS)]
            self.my_color = self.player_colors[self.network.username]
        self.update_cursor()

    # Load pen cursor images for each color from assets
    def load_pen_images(self):
        for color in PLAYER_COLORS:
            try:
                img = pygame.image.load(os.path.join(ASSETS_DIR, f"{color}_pen.png")).convert_alpha()
                img = pygame.transform.scale(img, (40, 40))
                
                scale_factor = 40 / 1024
                offset_x = int(170 * scale_factor)
                offset_y = int(840 * scale_factor)
                
                self.pen_images[color] = {
                    'image': img,
                    'offset': (offset_x, offset_y)
                }
            except Exception as e:
                print(f"Missing or failed to load image: images/{color}_pen.png")
                self.pen_images[color] = {
                    'image': None,
                    'offset': (0, 0)
                }
    # Send cursor position to the server and update local cursor
    def update_cursor(self):
        current_time = pygame.time.get_ticks()
        x, y = pygame.mouse.get_pos()
        self.network.send_game_command(f"CURSOR:{self.my_color}:{x},{y}")
        self.last_cursor_update = current_time
        self.last_cursor_pos = (x, y)
        
        if self.my_color and self.pen_images.get(self.my_color, {}).get('image'):
            self.cursor_img = self.pen_images[self.my_color]
            pygame.mouse.set_visible(False)
        else:
            self.cursor_img = None
            pygame.mouse.set_visible(True)

    # Display player names, colors, and their ownership percentage on the screen
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

    # Draw the entire game grid and exit button
    def draw_board(self):
        for row in self.squares:
            for square in row:
                square.draw(self.screen)
        self.exit_button.draw(self.screen)

    # Main game loop, for processing events, updating screen, and checking win condition
    def run(self):
        import gc
        last_gc = 0
        gc_interval = 60
        
        while self.running and self.network.running:
            current_frame = pygame.time.get_ticks()
            
            if current_frame - last_gc > gc_interval * 1000/60:
                gc.collect()
                last_gc = current_frame
            
            self.update_cursor()
            self.handle_events()
            self.screen.fill((255, 255, 255))
            self.draw_players()
            self.draw_board()
            self.draw_cursor()
            
            if not self.winner and self.is_board_full():
                percentages = self.calculate_ownership()
                max_squares = max(percentages.values())
                winners = [name for name, count in percentages.items() if count == max_squares]
                self.winner = winners[0]
            if self.winner:
                self.draw_victory_screen(self.winner)

            pygame.display.flip()
            self.clock.tick(60)

    # Render the player's own cursor and those of other players
    def draw_cursor(self):
        if self.cursor_img and self.cursor_img['image']:
            x, y = pygame.mouse.get_pos()
            offset_x, offset_y = self.cursor_img['offset']
            self.screen.blit(
                self.cursor_img['image'], 
                (x - offset_x, y - offset_y)
            )

        for color, (x, y) in self.other_cursors.items():
            img_data = self.pen_images.get(color)
            if img_data and img_data['image']:
                offset_x, offset_y = img_data['offset']
                self.screen.blit(
                    img_data['image'],
                    (x - offset_x, y - offset_y)
                )
    # Process mouse and window events like drawing or quitting
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
                self.network.quit()
            
            if self.winner:
                self.mainmenu_button.handle_event(event)
                continue
            elif event.type == pygame.MOUSEBUTTONDOWN:
                self.mouse_down = True
                self.handle_mouse_down(pygame.mouse.get_pos())
            elif event.type == pygame.MOUSEBUTTONUP:
                self.mouse_down = False
                self.handle_mouse_up()
            elif event.type == pygame.MOUSEMOTION and self.mouse_down:
                self.handle_mouse_motion(pygame.mouse.get_pos())
            
            self.exit_button.handle_event(event)

    # Start drawing when mouse button is pressed over an available square
    def handle_mouse_down(self, pos):
        if self.winner:
            return
        
        for row in self.squares:
            for square in row:
                if square.contains(pos):
                    if (square.locked_by is None or square.locked_by == self.my_color) and \
                    (square.claimed_by is None or square.claimed_by == self.my_color):
                        square.start_drawing(self.my_color)
                        self.current_square = square
                        self.network.send_game_command(f"LOCK:{square.row},{square.col}:{self.my_color}")
                        return
    
    # Update the drawing area while dragging the mouse
    def handle_mouse_motion(self, pos):
        if self.winner or not self.current_square:
            return
            
        current_time = pygame.time.get_ticks()
        if current_time - self.last_draw_time < 1:
            self.current_square.update_drawing(pos)
            return
            
        if not self.current_square.contains(pos):
            self.network.send_game_command(f"RESET:{self.current_square.row},{self.current_square.col}")
            self.current_square.reset_drawing()
            self.current_square = None
            return
        
        self.current_square.update_drawing(pos)
        local_x = pos[0] - self.current_square.rect.x
        local_y = pos[1] - self.current_square.rect.y
        self.network.send_game_command(
            f"DRAW:{self.current_square.row},{self.current_square.col}:{local_x},{local_y}:{self.my_color}"
        )
        self.last_draw_time = current_time

    # Stop drawing and decide whether to claim the square
    def handle_mouse_up(self):
        if self.winner or not self.current_square:
            return
            
        if self.current_square.drawing:
            filled_pixels = np.sum(self.current_square.pixel_grid)
            total_pixels = SQUARE_SIZE * SQUARE_SIZE
            percentage = (filled_pixels / total_pixels) * 100

            if percentage >= 50:
                self.network.send_game_command(
                    f"CLAIM:{self.current_square.row},{self.current_square.col}:{self.my_color}"
                )
            else:
                self.network.send_game_command(
                    f"RESET:{self.current_square.row},{self.current_square.col}"
                )
                self.network.send_game_command(f"UNLOCK:{self.current_square.row},{self.current_square.col}")

        self.current_square.stop_drawing()
        self.current_square = None

    # Process and apply incoming network game commands
    def handle_game_message(self, message):
        MAX_MESSAGES_PER_FRAME = 20
        processed_count = 0
        messages = message.split("GAME:")[1:]
        messages = ["GAME:" + msg for msg in messages]
        last_messages = {}
        
        for msg in messages:
            if processed_count >= MAX_MESSAGES_PER_FRAME:
                break
                
            try:
                if msg.startswith("GAME:CLAIM:"):
                    last_messages["CLAIM"] = msg
                elif msg.startswith("GAME:DRAW:"):
                    last_messages["DRAW"] = msg
                elif msg.startswith("GAME:RESET:"):
                    last_messages["RESET"] = msg
                elif msg.startswith("GAME:CURSOR:"):
                    last_messages["CURSOR"] = msg
                elif msg.startswith("GAME:LOCK:"):
                    last_messages["LOCK"] = msg
                elif msg.startswith("GAME:UNLOCK:"):
                    last_messages["UNLOCK"] = msg
                    
                processed_count += 1
            except:
                continue
        
        for msg_type, msg in last_messages.items():
            try:
                if msg_type == "CLAIM":
                    _, data = msg.split("GAME:CLAIM:")
                    coord_str, color = data.split(":")
                    row, col = map(int, coord_str.split(","))
                    square = self.squares[row][col]
                    if square.claimed_by is None:
                        square.claimed_by = color
                        square.drawing = False
                        square.pixel_grid.fill(False)                  
                elif msg_type == "DRAW":
                    _, data = msg.split("GAME:DRAW:")
                    coord_str, pixel_str, color = data.split(":")
                    row, col = map(int, coord_str.split(","))
                    px, py = map(int, pixel_str.split(","))
                    square = self.squares[row][col]
                    if square.claimed_by is None:
                        if square.locked_by is None or square.locked_by == color:
                            square.locked_by = color
                            square.drawing = True
                            square.drawing_color = color
                            
                            for dy in range(-4, 6):
                                for dx in range(-4, 6):
                                    brush_px = px + dx
                                    brush_py = py + dy
                                    if 0 <= brush_px < SQUARE_SIZE and 0 <= brush_py < SQUARE_SIZE:
                                        square.pixel_grid[brush_py][brush_px] = True
                elif msg_type == "RESET":
                    _, coord_str = msg.split("GAME:RESET:")
                    row, col = map(int, coord_str.split(","))
                    square = self.squares[row][col]
                    square.reset_drawing()
                elif msg_type == "CURSOR":
                    _, data = msg.split("GAME:CURSOR:")
                    color, pos_str = data.split(":")
                    if color != self.my_color:
                        x, y = map(int, pos_str.split(","))
                        
                        if color in self.other_cursors:
                            last_x, last_y = self.other_cursors[color]
                            x = last_x + (x - last_x) * 0.3  
                            y = last_y + (y - last_y) * 0.3
                            
                        self.other_cursors[color] = (x, y)
                        
                        if len(self.other_cursors) > 4:
                            oldest = next(iter(self.other_cursors))
                            del self.other_cursors[oldest]

                        current_colors = set(self.player_colors[p] for p in self.network.players if p in self.player_colors)
                        stale_cursors = [c for c in self.other_cursors if c not in current_colors]
                        for c in stale_cursors:
                            del self.other_cursors[c]            
                elif msg_type == "LOCK":
                    _, data = msg.split("GAME:LOCK:")
                    coord_str, color = data.split(":")
                    row, col = map(int, coord_str.split(","))
                    square = self.squares[row][col]
                    if square.claimed_by is None:
                        square.locked_by = color
                elif msg_type == "UNLOCK":
                    _, coord_str = msg.split("GAME:UNLOCK:")
                    row, col = map(int, coord_str.split(","))
                    square = self.squares[row][col]
                    if square.locked_by:
                        square.locked_by = None

            except Exception as e:
                print(f"Invalid {msg_type} message: {msg} ({e})")

    # Check whether all squares on the board have been claimed
    def is_board_full(self):
        for row in self.squares:
            for square in row:
                if not square.claimed_by:
                    return False
        return True

    # Compute how many squares each player owns, as a percentage
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
    
    # Display the winning player's name and return to main menu option
    def draw_victory_screen(self, winner_name):
        overlay = pygame.Surface((WIDTH, HEIGHT))
        overlay.set_alpha(180)
        overlay.fill((255, 255, 255))
        self.screen.blit(overlay, (0, 0))
        text = BIG_FONT.render(f"{winner_name} wins!", True, (0, 0, 0))
        text_rect = text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
        self.screen.blit(text, text_rect)
        self.mainmenu_button.draw(self.screen)

    # End the game and return to the main menu screen
    def return_to_main_menu(self):
        from menu import main_menu
        self.running = False
        self.network.quit()
        pygame.display.set_mode((600, 400))
        pygame.mouse.set_visible(True)
        main_menu()

if __name__ == "__main__":
    net = NetworkManager("brandonyang", 25565, is_host=True)
    board = GameBoard(net)
    board.run()
