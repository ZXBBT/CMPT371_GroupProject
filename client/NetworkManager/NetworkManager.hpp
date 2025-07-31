#ifndef NETWORK_MANAGER_HPP
#define NETWORK_MANAGER_HPP

#include <string>
#include <vector>
#include <thread>
#include <mutex>

using namespace std;

class NetworkManager {
public:
    enum class Role {
        HOST,
        CLIENT,
    };

    NetworkManager(Role role);
    ~NetworkManager();

    bool start(const string& ip, int port);
    void sendMessage(const string& message);
    void shutdown();

private:
    Role role;
    int serverSocket;
    int clientSocket;
    vector<int> clientSockets;
    thread listenerThread;
    mutex clientMutex;
    bool running;

    void hostLoop(int port);
    void clientLoop(const string& ip, int port);
    void acceptClients();
    void receiveLoop(int sockfd);
    void broadcast(const string& message);
};

#endif