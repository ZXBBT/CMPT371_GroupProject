import socket
import threading

class NetworkClient:
    def __init__(self, host='127.0.0.1', port=25565):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((host, port))
        self.running = True
        self.on_message = None

        threading.Thread(target=self._receive_loop, daemon=True).start()

    def _receive_loop(self):
        while self.running:
            try:
                data = self.sock.recv(1024).decode()
                if data:
                    print("Received:", data)
                    if self.on_message:
                        self.on_message(data)
            except Exception:
                break

    def send(self, msg: str):
        try:
            self.sock.sendall(msg.encode())
        except Exception as e:
            print("Send failed:", e)

    def close(self):
        self.running = False
        self.sock.close()