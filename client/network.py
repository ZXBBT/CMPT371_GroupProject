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
        success = _lib.start_network_manager(self._handle, self.server_ip.encode(), self.port)
        if not success:
            raise RuntimeError(f"NM_Start failed (role={role}, ip={ip}, port={port})")
        if not is_host:
            self.send_raw(f"JOIN:{self.username}")
    
    def set_message_handler(self, h):
        self.message_handler = h

    def set_player_update_handler(self, h):
        self.player_update_handler = h

    def get_server_info(self):
        if self.is_host:
            return f"Host IP: {self.host_ip}:{self.port}"
        else:
            return f"Connected to: {self.server_ip}:{self.port}"

    # def add_message(self, msg: str):
    #     with self.lock:
    #         self.messages.append(msg)
    #     if self.message_handler:
    #         # prefix like original code
    #         self.message_handler(f"MSG:{msg}")

    def send_message(self, text: str):
        if not self.running:
            return
        full = f"{self.username}: {text}"
        self._route_out(f"MSG:{full}")

    def send_game_command(self, cmd: str):
        if not self.running:
            return
        self._route_out(f"GAME:{cmd}")

    def poll(self, bufsize: int = 1024) -> str | None:
        buf = create_string_buffer(bufsize)
        got = _lib.poll_network_message(self._handle, buf, bufsize)
        if not got:
            return None
        raw = buf.value.decode()

        # Dispatch internal state updates
        if raw.startswith("PLAYERS:"):
            plist = raw.split(":",1)[1].split(",") if ":" in raw else []
            with self.lock:
                self.players = plist
            if self.player_update_handler:
                self.player_update_handler(plist)

        elif raw.startswith("JOIN:"):
            name = raw.split(":",1)[1]
            with self.lock:
                if name not in self.players:
                    self.players.append(name)
            self._send_raw(f"PLAYERS:{','.join(self.players)}")
            self._invoke_message(raw)

        elif raw.startswith("LEAVE:"):
            name = raw.split(":",1)[1]
            with self.lock:
                if name in self.players:
                    self.players.remove(name)
            self._send_raw(f"PLAYERS:{','.join(self.players)}")
            self._invoke_message(raw)

        elif raw.startswith("MSG:"):
            self._invoke_message(raw)

        elif raw.startswith("GAME:"):
            cmd = raw.split(":",1)[1]
            if self.is_host and cmd.startswith("CLAIM:"):
                self._handle_game(raw)
            self._invoke_message(raw)

        elif raw == "SERVER_SHUTDOWN":
            self._invoke_message(raw)
            self.running = False

        return raw
    
    def _route_out(self, raw: str):
        """Local echo + broadcast over C++ API"""
        # Local processing first
        if raw.startswith("MSG:"):
            msg = raw.split(":",1)[1]
            with self.lock:
                self.messages.append(msg)
        if raw.startswith("GAME:") and raw.split(":",1)[1].startswith("CLAIM:"):
            self._handle_game(raw)
        # Send
        _lib.broadcast_network_message(self._handle, raw.encode())

    def _send_raw(self, raw: str):
        _lib.broadcast_network_message(self._handle, raw.encode())

    def _invoke_message(self, raw: str):
        if raw.startswith("MSG:"):
            msg = raw.split(":",1)[1]
            with self.lock:
                self.messages.append(msg)
        if self.message_handler:
            self.message_handler(raw)

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
            s.close()

    # def broadcast(self, message: str) -> None:
    #     _lib.broadcast_network_message(self._handle, message.encode())

    # send = broadcast

    # def close(self) -> None:
    #     _lib.destroy_network_manager(self._handle)
    #     self._handle = None

    # quit = close
    
    def quit(self):
        # Client informs server
        if not self.is_host:
            self._send_raw(f"LEAVE:{self.username}")
        else:
            self._send_raw("SERVER_SHUTDOWN")
        self.running = False
        _lib.destroy_network_manager(self._handle)