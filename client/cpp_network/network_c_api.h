#ifndef NETWORK_C_API_H
#define NETWORK_C_API_H

#ifdef __cplusplus
extern "C" {
#endif

#include <stdbool.h>

typedef void* NetworkManagerHandle;

NetworkManagerHandle create_network_manager(int role);
bool start_network_manager(NetworkManagerHandle handle, const char* ip, int port);
bool poll_network_message(NetworkManagerHandle handle, char* buffer, int buffer_size);
void broadcast_network_message(NetworkManagerHandle handle, const char* message);
void destroy_network_manager(NetworkManagerHandle handle);

#ifdef __cplusplus
}
#endif

#endif