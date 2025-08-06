import ctypes
from ctypes import c_void_p, c_char_p, c_int, c_bool, create_string_buffer
import time

# Load the shared library
_lib = ctypes.CDLL("./cpp_network/libnetapi.so")

# Define the function signatures
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

# Constants
ROLE_HOST = 0
ROLE_CLIENT = 1
PORT = 25565
BUFFER_SIZE = 1024

def test_cpp_api():
    try:
        # Test as Host
        print("Testing as Host...")
        host_manager = _lib.create_network_manager(ROLE_HOST)
        assert host_manager, "Failed to create host network manager"

        success = _lib.start_network_manager(host_manager, b"", PORT)
        assert success, "Failed to start host network manager"

        # Test as Client
        print("Testing as Client...")
        client_manager = _lib.create_network_manager(ROLE_CLIENT)
        assert client_manager, "Failed to create client network manager"

        success = _lib.start_network_manager(client_manager, b"127.0.0.1", PORT)
        assert success, "Failed to connect client to host"

        # Allow some time for the connection to establish
        time.sleep(1)

        # Host sends a message
        print("Host sending message...")
        _lib.broadcast_network_message(host_manager, b"MSG: Hello from Host!")

        # Client polls for the message
        print("Client polling for message...")
        buffer = create_string_buffer(BUFFER_SIZE)
        received = _lib.poll_network_message(client_manager, buffer, BUFFER_SIZE)
        assert received, "Client failed to receive message"
        print(f"Client received: {buffer.value.decode()}")

        # Client sends a message
        print("Client sending message...")
        _lib.broadcast_network_message(client_manager, b"MSG: Hello from Client!")

        # Allow some time for the message to propagate
        time.sleep(2)

        # Host polls for the message
        print("Host polling for message...")
        buffer = create_string_buffer(BUFFER_SIZE)
        received = _lib.poll_network_message(host_manager, buffer, BUFFER_SIZE)
        assert received, "Host failed to receive message"
        print(f"Host received: {buffer.value.decode()}")

        # Cleanup
        print("Destroying host manager...")
        _lib.destroy_network_manager(host_manager)
        print("Host manager destroyed successfully.")

        print("Destroying client manager...")
        _lib.destroy_network_manager(client_manager)
        print("Client manager destroyed successfully.")
        print("Test completed successfully!")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    test_cpp_api()