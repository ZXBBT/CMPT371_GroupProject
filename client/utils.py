import pygame

# Color constants
BLACK = (0, 0, 0)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)

class Button:
    def __init__(self, text, x, y, width, height, callback):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.callback = callback
        self.font = pygame.font.SysFont("Arial", 24)

    def draw(self, surface):
        pygame.draw.rect(surface, LIGHT_GRAY, self.rect, border_radius=8)
        pygame.draw.rect(surface, DARK_GRAY, self.rect, 2, border_radius=8)

        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and self.rect.collidepoint(event.pos):
            self.callback()
