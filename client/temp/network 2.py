import socket
import threading

class NetworkManager:
    def __init__(self, username, port, is_host=False, server_ip=None):
        self.username = username
        self.port = port
        self.is_host = is_host
        self.server_ip = server_ip
        self.host_ip = None
        self.players = [username]
        self.messages = []
        self.running = True
        self.client_socket = None
        self.server_socket = None
        self.clients = []
        self.lock = threading.Lock()
        self.message_handler = None
        self.player_update_handler = None
        
        if is_host:
            self.host_ip = self.get_local_ip()
            self.start_server()
            self.board_state = [[None for _ in range(8)] for _ in range(8)]
        else:
            self.connect_to_server()
    
    def set_message_handler(self, handler):
        self.message_handler = handler
    
    def set_player_update_handler(self, handler):
        self.player_update_handler = handler
    
    def start_server(self):
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            self.server_socket.bind(('0.0.0.0', self.port))
            self.server_socket.listen(5)
            threading.Thread(target=self.accept_connections, daemon=True).start()
            self.add_message(f"Server started on port {self.port}")
        except Exception as e:
            self.add_message(f"Failed to start server: {str(e)}")
            self.running = False

    def get_local_ip(self):
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def accept_connections(self):
        while self.running:
            try:
                client_socket, addr = self.server_socket.accept()
                with self.lock:
                    self.clients.append(client_socket)
                threading.Thread(target=self.handle_client, args=(client_socket,), daemon=True).start()
            except Exception as e:
                if self.running:
                    print(f"Error accepting connection: {e}")
                break

    def connect_to_server(self):
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((self.server_ip, self.port))
            self.client_socket.send(f"JOIN:{self.username}".encode())
            threading.Thread(target=self.receive_messages, daemon=True).start()
            self.add_message(f"Connected to server at {self.server_ip}:{self.port}")
        except Exception as e:
            self.add_message(f"Failed to connect: {str(e)}")
            self.running = False

    def handle_client(self, client_socket):
        username = ""
        try:
            while self.running:
                data = client_socket.recv(1024).decode()
                if not data:
                    break
                    
                if data.startswith("JOIN:"):
                    username = data.split(":")[1]
                    with self.lock:
                        if username not in self.players:
                            self.players.append(username)
                    self.broadcast(f"PLAYERS:{','.join(self.players)}")
                    self.add_message(f"{username} joined the lobby")
                elif data.startswith("MSG:"):
                    message = data.split(":", 1)[1]
                    self.broadcast(f"MSG:{message}", exclude_socket=client_socket)
                elif data.startswith("GAME:"):
                    if data.startswith("GAME:CLAIM:") and self.is_host:
                        try:
                            _, claim_data = data.split("GAME:CLAIM:")
                            coord_str, color = claim_data.split(":")
                            row, col = map(int, coord_str.split(","))

                            if self.board_state[row][col] is None:
                                self.board_state[row][col] = color
                                if self.message_handler:
                                    self.message_handler(f"GAME:CLAIM:{row},{col}:{color}")
                                self.broadcast(f"GAME:CLAIM:{row},{col}:{color}")
                                print(f"CLAIM accepted from {color} at ({row},{col})")
                            else:
                                print(f"Rejected CLAIM for ({row},{col}) — already claimed.")
                        except Exception as e:
                            print(f"Malformed CLAIM: {data} ({e})")
                    else:
                        if self.message_handler:
                            self.message_handler(data)
                        self.broadcast(data)
                elif data.startswith("LEAVE:"):
                    username = data.split(":")[1]
                    with self.lock:
                        if username in self.players:
                            self.players.remove(username)
                    self.broadcast(f"PLAYERS:{','.join(self.players)}")
                    self.add_message(f"{username} left the lobby")
                    break
        except OSError as sock_err:
            # socket-level errors (e.g. Bad file descriptor)
            print(f"[Socket Error] {sock_err!r}")
            try:
                client_socket.close()
            except Exception as e:
                print(f"[Cleanup Error] Closing socket: {e}")
            with self.lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)
            return
        except Exception as e:
            print(f"Error handling client: {e}")
        finally:
            if username:
                with self.lock:
                    if username in self.players:
                        self.players.remove(username)
                        self.broadcast(f"PLAYERS:{','.join(self.players)}")
                        self.add_message(f"{username} left the lobby")
            try:
                client_socket.close()
            except:
                pass
            with self.lock:
                if client_socket in self.clients:
                    self.clients.remove(client_socket)

    def receive_messages(self):
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode()
                if not data:
                    break
                
                if data.startswith("MSG:"):
                    self.add_message(data.split(":", 1)[1])
                elif data.startswith("PLAYERS:"):
                    with self.lock:
                        self.players = data.split(":")[1].split(",")
                    if self.player_update_handler:
                        self.player_update_handler(self.players)
                elif data.startswith("GAME:"):
                    if self.message_handler:
                        self.message_handler(data)
                elif data == "SERVER_SHUTDOWN":
                    self.add_message("Server has been shut down")
                    break
            except Exception as e:
                if self.running:
                    print(f"Error receiving messages: {e}")
                break
        
        if self.client_socket:
            try:
                if self.running:
                    self.client_socket.send(f"LEAVE:{self.username}".encode())
                self.client_socket.close()
            except:
                pass
        self.running = False

    def broadcast(self, message, exclude_socket=None):
        if message.startswith("PLAYERS:"):
            with self.lock:
                self.players = message.split(":")[1].split(",")
            if self.player_update_handler:
                self.player_update_handler(self.players)
        
        if message.startswith("MSG:"):
            self.add_message(message.split(":", 1)[1])
        
        if self.is_host:
            with self.lock:
                for client in self.clients:
                    if client != exclude_socket:
                        try:
                            client.send(message.encode())
                        except:
                            continue

    def send_message(self, message):
        if not self.running:
            return
            
        full_message = f"{self.username}: {message}"
        if self.is_host:
            self.broadcast(f"MSG:{full_message}")
        else:
            self.add_message(full_message)
            try:
                self.client_socket.send(f"MSG:{full_message}".encode())
            except Exception as e:
                self.add_message(f"Failed to send message: {e}")
                self.running = False

    def send_game_command(self, command):
        if not self.running:
            return
            
        try:
            if self.is_host:
                if self.message_handler:
                    self.message_handler(f"GAME:{command}")
                self.broadcast(f"GAME:{command}")
            else:
                self.client_socket.send(f"GAME:{command}".encode())
        except Exception as e:
            print(f"Failed to send game command: {e}")

    def add_message(self, message):
        if message:
            with self.lock:
                self.messages.append(message)
            if self.message_handler and message.startswith("MSG:"):
                self.message_handler(message)

    def get_server_info(self):
        if self.is_host:
            return f"Host IP: {self.host_ip}:{self.port}"
        else:
            return f"Connected to: {self.server_ip}:{self.port}"

    def quit(self):
        self.running = False
        if not self.is_host and self.client_socket:
            try:
                self.client_socket.send(f"LEAVE:{self.username}".encode())
                self.client_socket.close()
            except:
                pass
        if self.is_host and self.server_socket:
            with self.lock:
                for client in self.clients:
                    try:
                        client.send("SERVER_SHUTDOWN".encode())
                        client.close()
                    except:
                        pass
                self.clients.clear()
            try:
                self.server_socket.close()
            except:
                pass