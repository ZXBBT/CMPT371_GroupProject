# CMPT 371 Group Project – Deny and Conquer 

##  Overview

This project implements **Client/Server networked game** using **Pygame 2.5.2+**, without any external game frameworks. The game is a simplified version of **Deny & Conquer**, an 8×8 grid where players compete to capture squares by drawing freehand lines. Concurrency through socket-based locking ensures that only one player can attempt each square at a time.

---

##  Prerequisites

- **Python 3.10 or newer**  
- **Pygame ≥ 2.5.2**  


```bash
git clone https://github.com/ZXBBT/CMPT371_GroupProject.git

cd CMPT371_GroupProject

pip install pygame>=2.5.2

python client/main.py
```

---

## Application Usage

Players begin at the main menu, where they can choose to **Create a Game**, **Join a Game**, or **Exit**.

- **Create a Game**  
  Prompts the player to enter a username and a port number (default: `25565`).  
  Clicking the **Create Server** button will launch the server and bring the player to the lobby page.

- **Join a Game**  
  Allows the player to input a username, server IP address, and port number.  
  Clicking the **Join Server** button connects the player to the existing server lobby.

Once in the lobby:

- The server displays all connected players on the right.
- Players can chat with each other while waiting.
- When **all players click the Ready button**, the game 
transitions to the game board and begins.

---

## Game Logic

The game interface is divided into two main sections:

- **Left Panel**: Displays player information including:
  - Player usernames and their assigned colors
  - A live-updating percentage of squares each player has captured
  - An **Exit** button at the bottom left, allowing players to leave the game at any time  
    > ⚠️ If the server host exits, the game will automatically terminate for all clients.

- **Right Panel**: The 8×8 gameboard where players interact and compete to capture squares.

### Basic Mechanics

- **Square Locking**:  
  When a player starts scribbling in a square, it becomes *locked* — no other player can draw on it until the current player releases it.

- **Capturing a Square**:  
  A square is considered captured if the player colors at least **50%** of its area during a continuous scribble (mouse held down).  
  - If successful, the square changes to the player’s color.
  - If unsuccessful (less than 50% colored), the square resets to white and becomes available again.

- **End-of-Game**:
  - The game ends when **all squares are captured**.
  - The player with the **highest number of captured squares** is declared the winner.


### Game End Screen

Once the game ends:
- All players see a **winner announcement screen**.
- A **Return to Main Menu** button is displayed, allowing players to restart or exit.




