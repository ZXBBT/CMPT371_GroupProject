import ctypes
import threading
import socket
from ctypes import c_void_p, c_char_p, c_int, c_bool, create_string_buffer

_lib = ctypes.CDLL("./cpp_network/libnetapi.so")

_lib.create_network_manager.restype = c_void_p
_lib.create_network_manager.argtypes = [c_int]

_lib.start_network_manager.restype = c_bool
_lib.start_network_manager.argtypes = [c_void_p, c_char_p, c_int]

_lib.poll_network_message.restype = c_bool
_lib.poll_network_message.argtypes = [c_void_p, c_char_p, c_int]

_lib.broadcast_network_message.restype = None
_lib.broadcast_network_message.argtypes = [c_void_p, c_char_p]

_lib.destroy_network_manager.restype = None
_lib.destroy_network_manager.argtypes = [c_void_p]

class NetworkManager:
    def __init__(self, username: str, port: int, is_host: bool = False, server_ip: str = None):
        self.username = username
        self.port = port
        self.is_host = is_host
        self.server_ip = server_ip
        self.host_ip = self.get_local_ip() if is_host else None
        self.players = [username]
        self.messages = []
        self.running = True
        self.board_state = [[None]*8 for _ in range(8)]
        self.lock = threading.Lock()
        self.message_handler = None
        self.player_update_handler = None

        role = 0 if is_host else 1
        ip = "" if is_host else server_ip

        self._handle = _lib.create_network_manager(role)
        if not self._handle:
            raise RuntimeError("Failed to create network manager")
        success = _lib.start_network_manager(self._handle, ip.encode(), port)
        if not success:
            raise RuntimeError(f"NM_Start failed (role={role}, ip={ip}, port={port})")
        if not is_host:
            self._send_raw(f"JOIN:{self.username}")
    
    def set_message_handler(self, h):
        self.message_handler = h

    def set_player_update_handler(self, h):
        self.player_update_handler = h

    def get_server_info(self):
        if self.is_host:
            return f"Host IP: {self.host_ip}:{self.port}"
        else:
            return f"Connected to: {self.server_ip}:{self.port}"

    def add_message(self, msg: str):
        with self.lock:
            self.messages.append(msg)
        if self.message_handler:
            # prefix like original code
            self.message_handler(f"MSG:{msg}")

    def send_message(self, text: str):
        if not self.running: return
        full = f"{self.username}: {text}"
        payload = f"MSG:{full}"
        if self.is_host:
            # host calls handler then broadcasts
            self.add_message(full)
            _lib.broadcast_network_message(self._handle, payload.encode())
        else:
            self.add_message(full)
            _lib.broadcast_network_message(self._handle, payload.encode())

    def send_game_command(self, cmd: str):
        if not self.running: return
        payload = f"GAME:{cmd}"
        if self.is_host:
            # apply locally
            self._handle_game(payload)
            _lib.broadcast_network_message(self._handle, payload.encode())
        else:
            _lib.broadcast_network_message(self._handle, payload.encode())

    def _handle_game(self, raw: str):
        # handle CLAIMs
        if raw.startswith("GAME:CLAIM:"):
            data = raw[len("GAME:CLAIM:"):]
            coord, color = data.split(":")
            r,c = map(int, coord.split(","))
            self.board_state[r][c] = color
        if self.message_handler:
            self.message_handler(raw)
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
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
                self.player_update_handler(plist)

        elif raw_message.startswith("MSG:"):
            self.add_message(raw_message.split(":",1)[1])

        elif raw_message.startswith("GAME:"):
            self._handle_game(raw_message)

        elif raw_message == "SERVER_SHUTDOWN":
            self.add_message("Server has been shut down")
            self.running = False

        return raw_message

    # def broadcast(self, message: str) -> None:
    #     _lib.broadcast_network_message(self._handle, message.encode())

    # send = broadcast

    # def close(self) -> None:
    #     _lib.destroy_network_manager(self._handle)
    #     self._handle = None

    # quit = close
    
    def quit(self):
        self.running = False
        _lib.destroy_network_manager(self._handle)