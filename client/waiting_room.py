import pygame
from utils import Button

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 640, 540
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Waiting Room")
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (220, 220, 220)
BLUE = (0, 120, 215)
FONT = pygame.font.SysFont("Arial", 24)
SMALL_FONT = pygame.font.SysFont("Arial", 20)

chat_messages = []
chat_input = ""

def waiting_room(player_name, go_back_callback):
    global chat_input
    players = [player_name]
    clock = pygame.time.Clock()

    chat_box_rect = pygame.Rect(180, 20, 380, 280)
    input_rect = pygame.Rect(20, HEIGHT - 200, 420, 30)
    ready_button = Button("Ready", WIDTH - 160, HEIGHT - 200, 90, 30, lambda: print(f"{player_name} is ready."))
    back_button = Button("Back", WIDTH - 160, 10, 90, 30, go_back_callback)

    active_input = False

    while True:
        SCREEN.fill(WHITE)
        show_cursor = pygame.time.get_ticks() % 1000 < 500

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                exit()
            elif event.type == pygame.MOUSEBUTTONDOWN:
                active_input = input_rect.collidepoint(event.pos)
                ready_button.handle_event(event)
                back_button.handle_event(event)
            elif event.type == pygame.KEYDOWN and active_input:
                if event.key == pygame.K_RETURN:
                    if chat_input.strip():
                        chat_messages.append(f"{player_name}: {chat_input}")
                        chat_input = ""
                elif event.key == pygame.K_BACKSPACE:
                    chat_input = chat_input[:-1]
                else:
                    chat_input += event.unicode

        draw_text("Players in Room:", 20, 20)
        for i, name in enumerate(players):
            draw_text(f"- {name}", 40, 60 + i * 30)

        pygame.draw.rect(SCREEN, GRAY, chat_box_rect)
        pygame.draw.rect(SCREEN, BLACK, chat_box_rect, 1)
        for i, msg in enumerate(chat_messages[-10:]):
            draw_text(msg, chat_box_rect.x + 10, chat_box_rect.y + 10 + i * 22, BLACK, SMALL_FONT)

        pygame.draw.rect(SCREEN, BLACK, input_rect, 2)
        input_surf = SMALL_FONT.render(chat_input, True, BLACK)
        SCREEN.blit(input_surf, (input_rect.x + 6, input_rect.y + 5))
        if active_input and show_cursor:
            cursor_x = input_rect.x + 6 + input_surf.get_width()
            cursor_y = input_rect.y + 5
            cursor_h = input_surf.get_height()
            pygame.draw.line(SCREEN, BLACK, (cursor_x, cursor_y), (cursor_x, cursor_y + cursor_h), 2)

        ready_button.draw(SCREEN)
        back_button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)

def draw_text(text, x, y, color=BLACK, font=FONT):
    surf = font.render(text, True, color)
    SCREEN.blit(surf, (x, y))

if __name__ == "__main__":
    waiting_room("Test_Player", lambda: print("Back to menu"))
