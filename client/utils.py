import pygame

# Color constants
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
LIGHT_GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)
BLUE = (0, 120, 215)

class Button:
    def __init__(self, text, x, y, width, height, callback):
        self.text = text
        self.rect = pygame.Rect(x, y, width, height)
        self.callback = callback
        self.font = pygame.font.SysFont("Arial", 24)
        self.hovered = False

    def draw(self, surface):
        color = LIGHT_GRAY if not self.hovered else (180, 180, 180)
        pygame.draw.rect(surface, color, self.rect, border_radius=8)
        pygame.draw.rect(surface, DARK_GRAY, self.rect, 2, border_radius=8)

        text_surf = self.font.render(self.text, True, BLACK)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)

    def handle_event(self, event):
        self.hovered = self.rect.collidepoint(pygame.mouse.get_pos())
        
        if event.type == pygame.MOUSEBUTTONDOWN and self.hovered:
            return self.callback()
        return None

class InputBox:
    def __init__(self, x, y, width, height, placeholder="", default_text=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.color = DARK_GRAY
        self.text = default_text
        self.placeholder = placeholder
        self.font = pygame.font.SysFont("Arial", 24)
        self.active = False
        self.placeholder_color = (150, 150, 150)

    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
            self.color = BLUE if self.active else DARK_GRAY
        
        if event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_RETURN:
                return True
            elif event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            else:
                self.text += event.unicode
        return False

    def draw(self, surface):
        pygame.draw.rect(surface, WHITE, self.rect)
        pygame.draw.rect(surface, self.color, self.rect, 2)
        
        if self.text or self.active:
            text_surface = self.font.render(self.text, True, BLACK)
        else:
            text_surface = self.font.render(self.placeholder, True, self.placeholder_color)
        
        surface.blit(text_surface, (self.rect.x + 5, self.rect.y + 5))