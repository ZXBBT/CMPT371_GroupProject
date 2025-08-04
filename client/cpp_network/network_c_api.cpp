#include "network_c_api.h"
#include "NetworkManager.hpp"

#include <cstring>
#include <string>
#include <algorithm>

using namespace std;

NetworkManagerHandle create_network_manager(int role) {
    NetworkManager::Role r;
    if (role == 0)
        r = NetworkManager::Role::HOST;
    else
        r = NetworkManager::Role::CLIENT;
    NetworkManager* nm = new NetworkManager(r);
    return reinterpret_cast<NetworkManagerHandle>(nm);
}

bool start_network_manager(NetworkManagerHandle handle, const char* ip, int port) {
    NetworkManager* nm = reinterpret_cast<NetworkManager*>(handle);
    string address;
    if (ip != nullptr)
        address = string(ip);
    else
        address = string();
    bool success = nm->start(address, port);
    return success;
}

bool poll_network_message(NetworkManagerHandle handle, char* buffer, int buffer_size) {
    NetworkManager* nm = reinterpret_cast<NetworkManager*>(handle);
    string message;
    bool hasMessage = nm->pollMessage(message);
    if (hasMessage == false)
        return false;
    int copyLen = static_cast<int>(message.size());
    if (copyLen > buffer_size-1)
        copyLen = buffer_size - 1;
    memcpy(buffer, message.data(), copyLen);
    buffer[copyLen] = '\0';
    return true;
}

void broadcast_network_message(NetworkManagerHandle handle, const char* message) {
    NetworkManager* nm = reinterpret_cast<NetworkManager*>(handle);
    string text;
    if (message != nullptr)
        text = string(message);
    else
        text = string();
    nm->sendMessage(text);
}

void destroy_network_manager(NetworkManagerHandle handle) {
    NetworkManager* nm = reinterpret_cast<NetworkManager*>(handle);
    nm->shutdown();
    delete nm;
}