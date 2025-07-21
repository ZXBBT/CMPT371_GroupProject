import pygame
import sys
from utils import Button

pygame.init()
pygame.font.init()
WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Deny and Conquer")

# Colors
WHITE = (255, 255, 255)
BLUE = (0, 120, 215)

# Fonts
TITLE_FONT = pygame.font.SysFont("Arial", 48, bold=True)

def exit_game():
    pygame.quit()
    sys.exit()

def main_menu():
    # Create button instances
    buttons = [
        Button("Create a Game", WIDTH // 2 - 100, 160, 200, 50, lambda: print("Create Game pressed")),
        Button("Join a Game", WIDTH // 2 - 100, 230, 200, 50, lambda: print("Join Game pressed")),
        Button("Exit", WIDTH // 2 - 100, 300, 200, 50, exit_game)
    ]

    clock = pygame.time.Clock()

    while True:
        SCREEN.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()
            for button in buttons:
                button.handle_event(event)

        title_surf = TITLE_FONT.render("Deny and Conquer", True, BLUE)
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 80))
        SCREEN.blit(title_surf, title_rect)

        for button in buttons:
            button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)
