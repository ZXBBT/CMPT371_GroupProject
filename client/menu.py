import pygame
import sys
import random
from utils import Button
import join_menu
import waiting_room

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Deny and Conquer")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 120, 215)
DARK_GRAY = (50, 50, 50)
TITLE_FONT = pygame.font.SysFont("Arial", 48, bold=True)
TEXT_FONT = pygame.font.SysFont("Arial", 24)

player_name = f"Player_{random.randint(1000, 9999)}"
input_rect = pygame.Rect(WIDTH // 2 - 100, 120, 200, 32)
input_active = False

def exit_game():
    pygame.quit()
    sys.exit()

def main_menu():
    global player_name, input_active

    buttons = [
        Button("Create a Game", WIDTH // 2 - 100, 180, 200, 50, lambda: waiting_room.waiting_room(player_name, main_menu)),
        Button("Join a Game", WIDTH // 2 - 100, 250, 200, 50, lambda: join_menu.join_menu(player_name, main_menu)),
        Button("Exit", WIDTH // 2 - 100, 320, 200, 50, exit_game)
    ]

    clock = pygame.time.Clock()

    while True:
        SCREEN.fill(WHITE)
        show_cursor = pygame.time.get_ticks() % 1000 < 500

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                input_active = input_rect.collidepoint(event.pos)
                for button in buttons:
                    button.handle_event(event)
            elif event.type == pygame.KEYDOWN and input_active:
                if event.key == pygame.K_BACKSPACE:
                    player_name = player_name[:-1]
                elif event.key == pygame.K_RETURN:
                    input_active = False
                elif len(player_name) < 16 and event.unicode.isprintable():
                    player_name += event.unicode

        title_surf = TITLE_FONT.render("Deny and Conquer", True, BLUE)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 60))
        SCREEN.blit(title_surf, title_rect)

        name_label = TEXT_FONT.render("Name:", True, BLACK)
        SCREEN.blit(name_label, (input_rect.x - 70, input_rect.y + 5))
        box_color = BLUE if input_active else BLACK
        pygame.draw.rect(SCREEN, box_color, input_rect, 2)
        name_surf = TEXT_FONT.render(player_name, True, BLACK)
        SCREEN.blit(name_surf, (input_rect.x + 5, input_rect.y + 4))
        if input_active and show_cursor:
            cursor_x = input_rect.x + 5 + name_surf.get_width()
            cursor_y = input_rect.y + 4
            cursor_h = name_surf.get_height()
            pygame.draw.line(SCREEN, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_h), 2)

        for button in buttons:
            button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    main_menu()
