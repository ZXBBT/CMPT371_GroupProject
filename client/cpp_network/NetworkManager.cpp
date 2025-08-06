#include "NetworkManager.hpp"

#include <iostream>
#include <cstring>
#include <arpa/inet.h>
#include <sys/socket.h>
#include <netinet/in.h>
#include <unistd.h>
#include <queue>
#include <mutex>

NetworkManager::NetworkManager(Role role) {
    this->role = role;
    serverSocket = -1;
    clientSocket = -1;
    running = false;
}
NetworkManager::~NetworkManager() {
    shutdown();
}

bool NetworkManager::start(const string& ip, int port) {
    running = true;
    if (role == Role::HOST)
        listenerThread = thread(&NetworkManager::hostLoop, this, port);
    else
        listenerThread = thread(&NetworkManager::clientLoop, this, ip, port);
    return true;
}

void NetworkManager::hostLoop(int port) {
    serverSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (serverSocket < 0) {
        cerr << "Failed to create socket.\n";
        return;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_addr.s_addr = INADDR_ANY;
    serverAddr.sin_port = htons(port);

    if (::bind(serverSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
        cerr << "Bind failed.\n";
        return;
    }

    if (listen(serverSocket, 5) < 0) {
        cerr << "Listen failed.\n";
        return;
    }

    cout << "Hosting on port " << port << "...\n";
    thread(&NetworkManager::acceptClients, this).detach();
}

void NetworkManager::acceptClients() {
    while (running) {
        sockaddr_in clientAddr;
        socklen_t clientLen = sizeof(clientAddr);
        int clientSock = accept(serverSocket, (sockaddr*)&clientAddr, &clientLen);
        if (clientSock >= 0) {
            lock_guard<mutex> lock(clientMutex);
            clientSockets.push_back(clientSock);
            thread(&NetworkManager::receiveLoop, this, clientSock).detach();
        }
    }
}

void NetworkManager::clientLoop(const string& ip, int port) {
    clientSocket = socket(AF_INET, SOCK_STREAM, 0);
    if (clientSocket < 0) {
        cerr << "Failed to create client socket.\n";
        return;
    }

    sockaddr_in serverAddr{};
    serverAddr.sin_family = AF_INET;
    serverAddr.sin_port = htons(port);
    inet_pton(AF_INET, ip.c_str(), &serverAddr.sin_addr);

    if (connect(clientSocket, (sockaddr*)&serverAddr, sizeof(serverAddr)) < 0) {
        cerr << "Failed to connect to server.\n";
        return;
    }

    cout << "Connected to server at " << ip << ":" << port << "\n";
    while (running) {
        receiveLoop(clientSocket);
    }
}

void NetworkManager::receiveLoop(int sockfd) {
    char buffer[1024];
    while (running) {
        memset(buffer, 0, sizeof(buffer));
        ssize_t bytes = recv(sockfd, buffer, sizeof(buffer) - 1, 0);
        if (bytes <= 0) {
            if (!running) break;
            break;
        }
        string msg(buffer);
        // cout << "Received: " << msg << "\n";
        lock_guard<mutex> lock(queueMutex);
        messageQueue.push(msg);
    }
    close(sockfd);
}

void NetworkManager::sendMessage(const std::string& message) {
    if (role == Role::HOST)
        broadcast(message);
    else
        send(clientSocket, message.c_str(), message.size(), 0);
}

void NetworkManager::broadcast(const std::string& message) {
    lock_guard<mutex> lock(clientMutex);
    for (vector<int>::iterator it = clientSockets.begin(); it != clientSockets.end(); ++it) {
        send(*it, message.c_str(), message.size(), 0);
    }
}

bool NetworkManager::pollMessage(string& message) {
    lock_guard<mutex> lock(queueMutex);
    if (!messageQueue.empty()) {
        message = messageQueue.front();
        messageQueue.pop();
        return true;
    }
    return false;
}

void NetworkManager::shutdown() {
    running = false;

    if (clientSocket >= 0) {
        ::shutdown(clientSocket, SHUT_RDWR);
        ::close(clientSocket);
        clientSocket = -1;
    }
    if (serverSocket >= 0) {
        ::shutdown(serverSocket, SHUT_RDWR);
        ::close(serverSocket);
        serverSocket = -1;
    }
    if (listenerThread.joinable()) {
        listenerThread.join();
    }
}
