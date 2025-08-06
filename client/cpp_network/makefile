CXX ?= g++
CXXFLAGS = -std=c++17 -fPIC -Wall -Wextra
LDFLAGS = -shared -pthread
INCLUDES = -I.
SOURCES = network_c_api.cpp NetworkManager.cpp
OBJECTS = $(SOURCES:.cpp=.o)
TARGET = libnetapi.so

.PHONY: all clean rebuild

all: $(TARGET)

$(TARGET): $(OBJECTS)
	$(CXX) $(LDFLAGS) -o $@ $(OBJECTS)

%.o: %.cpp
	$(CXX) $(CXXFLAGS) $(INCLUDES) -c $< -o $@

clean:
	rm -f $(OBJECTS) $(TARGET)

rebuild: clean all
