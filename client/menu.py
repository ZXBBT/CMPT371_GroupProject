import pygame
import sys
from utils import Button, InputBox, ReadyButton
from network import NetworkManager
from gameboard import GameBoard

pygame.init()
pygame.font.init()

WIDTH, HEIGHT = 600, 400
SCREEN = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Deny and Conquer")

WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
BLUE = (0, 120, 215)

TITLE_FONT = pygame.font.SysFont("Arial", 48, bold=True)
MEDIUM_FONT = pygame.font.SysFont("Arial", 24)
SMALL_FONT = pygame.font.SysFont("Arial", 16)

def exit_game():
    pygame.quit()
    sys.exit()

class LobbyScreen:
    def __init__(self, network_manager):
        self.network = network_manager
        self.input_box = InputBox(50, HEIGHT - 50, WIDTH - 100, 40, "Type your message...")
        self.exit_button = Button("Exit Lobby", WIDTH - 120, HEIGHT - 50, 100, 40, self.quit_lobby)

        self.player_ready = {self.network.username: False}
        self.ready_button = ReadyButton("Ready", 50, HEIGHT - 100, 120, 40, self.on_ready_toggle, self.network.username)

        if self.network.username not in self.network.players:
            self.network.players.append(self.network.username)

        self.network.set_message_handler(self.handle_network_message)
        self.network.set_player_update_handler(self.handle_player_update)

    def handle_network_message(self, message):
        if message.startswith("GAME:READY:"):
            parts = message.split(":")
            if len(parts) == 4:
                is_ready = parts[2] == "1"
                player = parts[3]
                self.player_ready[player] = is_ready

                if is_ready:
                    self.network.messages.append(f"{player} is ready.")
                else:
                    self.network.messages.append(f"{player} is not ready.")

                with self.network.lock:
                    for p in self.network.players:
                        if p not in self.player_ready:
                            self.player_ready[p] = False

                self.check_all_ready()

        elif message.strip() == "GAME:START":
            print("GAME:START received")
            pygame.event.post(pygame.event.Event(pygame.USEREVENT, {"start_game": True}))

    def handle_player_update(self, players):
        if self.network.username not in players:
            players.append(self.network.username)
        self.network.players = players
        for p in players:
            if p not in self.player_ready:
                self.player_ready[p] = False

    def check_all_ready(self):
        with self.network.lock:
            valid_players = [p for p in self.network.players if self.player_ready.get(p) is not None]
            all_ready = len(valid_players) > 0 and all(self.player_ready.get(p, False) for p in valid_players)
        if all_ready:
            print("All players are ready")
            self.network.send_game_command("START")
            self.handle_network_message("GAME:START")

    # def run(self):
    #     clock = pygame.time.Clock()

    #     while self.network.running:
    #         for event in pygame.event.get():
    #             if event.type == pygame.QUIT:
    #                 self.quit_lobby()
    #                 return

    #             if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
    #                 message = self.input_box.text.strip()
    #                 if message:
    #                     self.network.send_message(message)
    #                     self.input_box.text = ""

    #             if event.type == pygame.USEREVENT and event.dict.get("start_game"):
    #                 print("Launching GameBoard...")
    #                 GameBoard(self.network).run()
    #                 pygame.quit()
    #                 sys.exit()

    #             self.input_box.handle_event(event)
    #             self.ready_button.handle_event(event)
    #             action = self.exit_button.handle_event(event)
    #             if action is not None:
    #                 self.quit_lobby()
    #                 return

    #         self.draw()
    #         pygame.display.flip()
    #         clock.tick(60)

    def run(self):
        clock = pygame.time.Clock()

        while True:
            if not self.network.running:
                print("[DEBUG] Disconnected from server, returning to main menu...")
                from menu import main_menu
                pygame.display.set_mode((600, 400))
                pygame.mouse.set_visible(True)
                main_menu()
                return

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.quit_lobby()
                    return

                if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                    message = self.input_box.text.strip()
                    if message:
                        self.network.send_message(message)
                        self.input_box.text = ""

                if event.type == pygame.USEREVENT and event.dict.get("start_game"):
                    print("Launching GameBoard...")
                    GameBoard(self.network).run()
                    pygame.display.set_mode((600, 400))
                    pygame.mouse.set_visible(True)
                    main_menu()
                    return

                self.input_box.handle_event(event)
                self.ready_button.handle_event(event)
                action = self.exit_button.handle_event(event)
                if action is not None:
                    self.quit_lobby()
                    return

            self.draw()
            pygame.display.flip()
            clock.tick(60)



    def on_ready_toggle(self, player_id, is_ready):
        self.player_ready[player_id] = is_ready
        self.network.send_game_command(f"READY:{int(is_ready)}:{player_id}")

        if self.network.is_host:
            self.check_all_ready()

    def draw(self):
        SCREEN.fill(WHITE)

        title_surf = MEDIUM_FONT.render("Lobby", True, BLUE)
        SCREEN.blit(title_surf, (20, 20))

        server_info = self.network.get_server_info()
        server_surf = SMALL_FONT.render(server_info, True, BLACK)
        SCREEN.blit(server_surf, (20, 50))

        players_surf = SMALL_FONT.render("Players:", True, BLACK)
        SCREEN.blit(players_surf, (WIDTH - 150, 20))

        with self.network.lock:
            for i, player in enumerate(self.network.players):
                player_surf = SMALL_FONT.render(player, True, BLACK)
                SCREEN.blit(player_surf, (WIDTH - 150, 50 + i * 25))

            for i, message in enumerate(self.network.messages[-10:]):
                msg_surf = SMALL_FONT.render(message, True, BLACK)
                SCREEN.blit(msg_surf, (20, 80 + i * 20))

        self.input_box.draw(SCREEN)
        self.exit_button.draw(SCREEN)
        self.ready_button.draw(SCREEN)

    def quit_lobby(self):
        self.network.quit()


def create_game_screen():
    username_box = InputBox(WIDTH // 2 - 100, 150, 200, 40, "Username")
    port_box = InputBox(WIDTH // 2 - 100, 220, 200, 40, "Port", "25565")
    buttons = [
        Button("Create Server", WIDTH // 2 - 100, 300, 200, 50,
               lambda: LobbyScreen(NetworkManager(username_box.text, int(port_box.text), is_host=True)).run()),
        Button("Back", 20, HEIGHT - 70, 100, 40, lambda: "back")
    ]

    clock = pygame.time.Clock()

    while True:
        SCREEN.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()

            username_box.handle_event(event)
            port_box.handle_event(event)

            for button in buttons:
                action = button.handle_event(event)
                if action == "back":
                    return

        title_surf = TITLE_FONT.render("Create Game", True, BLUE)
        SCREEN.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 50))

        username_box.draw(SCREEN)
        port_box.draw(SCREEN)

        for button in buttons:
            button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)

def join_game_screen():
    error_message = ""
    username_box = InputBox(WIDTH // 2 - 100, 120, 200, 40, "Username")
    server_ip_box = InputBox(WIDTH // 2 - 100, 190, 200, 40, "Server IP")
    port_box = InputBox(WIDTH // 2 - 100, 260, 200, 40, "Port", "25565")

    def try_join_server(username, server_ip, port_text):
        nonlocal error_message
        error_message = ""
        try:
            port = int(port_text)
            network = NetworkManager(username, port, server_ip=server_ip)
            if not network.running:
                raise Exception("Connection failed")
            LobbyScreen(network).run()
        except Exception as e:
            error_message = "Failed to connect to server"

    buttons = [
        Button(
            "Join Server",
            WIDTH // 2 - 100,
            330,
            200,
            50,
            lambda: try_join_server(username_box.text, server_ip_box.text, port_box.text)
        )
    ]

    clock = pygame.time.Clock()

    while True:
        SCREEN.fill(WHITE)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                exit_game()

            username_box.handle_event(event)
            server_ip_box.handle_event(event)
            port_box.handle_event(event)

            for button in buttons:
                action = button.handle_event(event)
                if action == "back":
                    return

        title_surf = TITLE_FONT.render("Join Game", True, BLUE)
        SCREEN.blit(title_surf, (WIDTH // 2 - title_surf.get_width() // 2, 50))

        username_box.draw(SCREEN)
        server_ip_box.draw(SCREEN)
        port_box.draw(SCREEN)

        for button in buttons:
            button.draw(SCREEN)

        if error_message:
            error_surf = SMALL_FONT.render(error_message, True, (255, 0, 0))
            SCREEN.blit(error_surf, (WIDTH // 2 - error_surf.get_width() // 2, 10))

        pygame.display.flip()
        clock.tick(60)

def main_menu():
    buttons = [
        Button("Create a Game", WIDTH // 2 - 100, 160, 200, 50, create_game_screen),
        Button("Join a Game", WIDTH // 2 - 100, 230, 200, 50, join_game_screen),
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
        title_rect = title_surf.get_rect(center=(WIDTH // 2, 60))
        SCREEN.blit(title_surf, title_rect)

        for button in buttons:
            button.draw(SCREEN)

        pygame.display.flip()
        clock.tick(60)
