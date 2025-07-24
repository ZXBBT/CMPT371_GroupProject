import pygame
from utils import Button

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Join a Game")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 120, 215)

FONT = pygame.font.SysFont("Arial", 24)
TITLE_FONT = pygame.font.SysFont("Arial", 36, bold=True)

def scan_for_servers():
    # placeholder for real UDP server discovery
    return [
        ("Host 1", "192.168.0.101", 12345),
        ("Host 2", "192.168.0.102", 12345)
    ]

def draw_text(text, x, y, color=BLACK):
    surf = FONT.render(text, True, color)
    SCREEN.blit(surf, (x, y))

def join_menu(player_name, go_back_callback):
    clock = pygame.time.Clock()
    servers = scan_for_servers()
    buttons = []

    for i, (name, ip, port) in enumerate(servers):
        def make_callback(server_ip=ip, server_port=port):
            return lambda: print(f"{player_name} joining {server_ip}:{server_port}")
        buttons.append(Button(f"Join {name} ({ip})", 150, 120 + i * 60, 300, 40, make_callback()))

    back_button = Button("Back", 20, HEIGHT - 60, 100, 40, go_back_callback)

    while True:
        SCREEN.fill(WHITE)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            for button in buttons + [back_button]:
                button.handle_event(event)

        title = TITLE_FONT.render("Available Servers", True, BLUE)
        SCREEN.blit(title, (WIDTH // 2 - title.get_width() // 2, 40))

        for button in buttons:
            button.draw(SCREEN)
        back_button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)

if __name__ == "__main__":
    join_menu("Test_Player", lambda: print("Back to menu"))
