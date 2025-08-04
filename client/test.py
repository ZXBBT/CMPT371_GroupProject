import socket

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
s.connect(("127.0.0.1", 25565))
s.send(b"MSG: Hello from Python!\n")
s.close()