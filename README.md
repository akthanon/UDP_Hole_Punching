# UDP Hole Punching Demo

A simple Python implementation of UDP hole punching using a signaling server.  
The project allows two clients to discover each other's UDP endpoint and attempt direct peer-to-peer communication through NAT.

## Files

- `udp_hole_punching.py` — Client application.  
  Connects to the signaling server, receives the peer's IP and port, sends UDP packets to open NAT mappings, and then allows chatting with the peer.

- `udp_hole_punching_STUN.py` — Signaling server.  
  Listens on UDP port `12345`, records connected clients, pairs the first two clients, and exchanges their `IP:PORT` information.

> **Note:** Despite the name, `udp_hole_punching_STUN.py` does **not** implement STUN. It is only a basic signaling server.

## Requirements

- Python 3.x
- Network connectivity between the clients and the signaling server
- For real NAT traversal:
  - The signaling server should be reachable from both clients (public IP or port-forwarded).
  - Both clients should be behind NATs or on different networks.

## Configuration

In `udp_hole_punching.py`:

```python
servidor_ip = "192.168.100.185"  # Signaling server IP
servidor_puerto = 12345          # Signaling server port
mi_puerto = int(33342)           # Local UDP port to bind
```

In `udp_hole_punching_STUN.py`:

```python
servidor_puerto = 12345  # Signaling server listening port
```

## Usage

1. Start the signaling server on a machine reachable by both clients:

```bash
python3 udp_hole_punching_STUN.py
```

2. Start the client on two different machines, or in two separate terminals for testing:

```bash
python3 udp_hole_punching.py
```

3. Each client sends a `PING` packet to the signaling server.  
   Once two clients are registered, the server sends each client the other client's `IP:PORT`.

4. Each client sends a series of `PING` packets to the peer to create and maintain NAT mappings.

5. After the hole-punching phase, type a message in the client terminal and press Enter.  
   Messages are sent directly to the peer over UDP.

## How It Works

1. The signaling server records the source `(IP, port)` of every UDP packet it receives.
2. When at least two clients are known, it sends the first client's endpoint to the second client and vice versa.
3. Each client then sends UDP packets to the peer's endpoint.
4. If both NATs allow outbound UDP and keep the mappings open, the packets may reach each other.
5. A background thread on each client listens for incoming UDP messages.

## Limitations

- Supports only two clients at a time (pairs the first two endpoints).
- No authentication, encryption, or reliability.
- Hardcoded configuration; no command-line arguments.
- No STUN implementation or NAT type detection.
- May not work with symmetric NATs or restrictive firewalls.
- The server does not remove disconnected clients.

## Disclaimer

This project is for educational purposes only.  
Use it only on networks you own or have permission to test.
