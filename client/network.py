import ctypes
import threading
import socket
import time
from ctypes import c_void_p, c_char_p, c_int, c_bool, create_string_buffer

# Load C++ networking library
_lib = ctypes.CDLL("./cpp_network/libnetapi.so")

# Define C API signatures
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

        # Create and start underlying C++ network manager
        role = 0 if is_host else 1
        self._handle = _lib.create_network_manager(role)
        if not self._handle:
            raise RuntimeError("Failed to create network manager")

        ip_arg = self.host_ip.encode() if is_host else (self.server_ip or "").encode()
        success = _lib.start_network_manager(self._handle, ip_arg, self.port)
        if not success:
            raise RuntimeError(f"NM_Start failed (role={role}, ip={ip_arg.decode()}, port={self.port})")

        # If client role, announce join
        if not is_host:
            print(f"Joining game as {self.username}")
            self._send_raw(f"JOIN:{self.username}")

        # Start polling thread to process incoming messages
        self._poll_thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._poll_thread.start()

    def set_message_handler(self, handler):
        self.message_handler = handler

    def set_player_update_handler(self, handler):
        self.player_update_handler = handler

    def get_server_info(self) -> str:
        if self.is_host:
            return f"Host IP: {self.host_ip}:{self.port}"
        else:
            return f"Connected to: {self.server_ip}:{self.port}"

    def send_message(self, text: str):
        if not self.running:
            return
        full = f"{self.username}: {text}"
        self._route_out(f"MSG:{full}")

    def send_game_command(self, cmd: str):
        if not self.running:
            return
        self._route_out(f"GAME:{cmd}")

    def _poll_loop(self):
        """
        Continuously poll the C++ backend for messages and dispatch.
        """
        bufsize = 1024
        buf = create_string_buffer(bufsize)
        while self.running:
            try:
                if _lib.poll_network_message(self._handle, buf, bufsize):
                    raw = buf.value.decode()
                    print(f"Received raw: {raw}")
                    self._process_raw(raw)
            except Exception as e:
                print(f"Network poll error: {e}")
            time.sleep(0.01)

    def _process_raw(self, raw: str):
        # Handle PLAYERS update
        if raw.startswith("PLAYERS:"):
            plist = raw.split(":", 1)[1].split(",") if ":" in raw else []
            with self.lock:
                self.players = plist
            if self.player_update_handler:
                self.player_update_handler(plist)
            return

        # Handle join/leave events
        if raw.startswith("JOIN:") or raw.startswith("LEAVE:"):
            action, name = raw.split(":", 1)
            print(f"Player {action}: {name}")
            with self.lock:
                print(self.players)
                if action == "JOIN" and name not in self.players:
                    self.players.append(name)
                    self._send_raw(f"PLAYERS:{','.join(self.players)}")
                    self._invoke_message(f"{name} joined the lobby")
                elif action == "LEAVE" and name in self.players:
                    self.players.remove(name)
                    self._send_raw(f"PLAYERS:{','.join(self.players)}")
                    self._invoke_message(f"{name} left the lobby")
            return

        # Handle chat messages
        if raw.startswith("MSG:"):
            self._invoke_message(raw)
            return

        # Handle game commands
        if raw.startswith("GAME:"):
            cmd_body = raw.split(":", 1)[1]
            # Host handles CLAIM internally
            if self.is_host and cmd_body.startswith("CLAIM:"):
                self._handle_game(raw)
            self._invoke_message(raw)
            return

        # Handle server shutdown
        if raw == "SERVER_SHUTDOWN":
            self.running = False
            self._invoke_message(raw)
            return

    def _route_out(self, raw: str):
        # Local echo for chat
        if raw.startswith("MSG:"):
            msg = raw.split(":", 1)[1]
            with self.lock:
                self.messages.append(msg)
        # Host pre-handle claims
        if raw.startswith("GAME:CLAIM:"):
            self._handle_game(raw)
        # Send to network
        _lib.broadcast_network_message(self._handle, raw.encode())

    def _send_raw(self, raw: str):
        _lib.broadcast_network_message(self._handle, raw.encode())

    def _invoke_message(self, raw: str):
        # Append to local message buffer
        if raw.startswith("MSG:"):
            msg = raw.split(":", 1)[1]
            with self.lock:
                self.messages.append(msg)
        # Call handler
        if self.message_handler:
            self.message_handler(raw)

    def _handle_game(self, raw: str):
        # Only CLAIM affects board state server-side
        if raw.startswith("GAME:CLAIM:"):
            _, data = raw.split("GAME:CLAIM:")
            coord, color = data.split(":")
            r, c = map(int, coord.split(","))
            self.board_state[r][c] = color
        # Propagate to UI
        if self.message_handler:
            self.message_handler(raw)

    def get_local_ip(self) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            return s.getsockname()[0]
        except:
            return "127.0.0.1"
        finally:
            s.close()

    def quit(self):
        # Notify leave or shutdown
        if not self.is_host:
            self._send_raw(f"LEAVE:{self.username}")
        else:
            self._send_raw("SERVER_SHUTDOWN")
        self.running = False
        _lib.destroy_network_manager(self._handle)