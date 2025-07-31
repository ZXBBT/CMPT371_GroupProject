#include "NetworkManager/NetworkManager.hpp"
#include <iostream>
#include <thread>
#include <chrono>

int main(int argc, char* argv[]) {
    if (argc != 3) {
        std::cerr << "Usage: ./main [host|client] <port>\n";
        return 1;
    }

    std::string mode = argv[1];
    int port = std::stoi(argv[2]);

    if (mode == "host") {
        NetworkManager manager(NetworkManager::Role::HOST);
        manager.start("", port);
        std::this_thread::sleep_for(std::chrono::seconds(60)); // keep server running
    } else if (mode == "client") {
        NetworkManager manager(NetworkManager::Role::CLIENT);
        manager.start("127.0.0.1", port);
        std::string msg;
        while (std::getline(std::cin, msg)) {
            manager.sendMessage(msg);
        }
    } else {
        std::cerr << "Invalid mode: " << mode << "\n";
        return 1;
    }

    return 0;
}