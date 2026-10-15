import socket
import threading
import sys

SERVER_IP = "XX.XX.XX.XX"
SERVER_PORT = 5000

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(4096)
            if not data:
                print("\n[-] Conexión cerrada por el servidor.")
                break
            print(f"\n[Peer]: {data.decode('utf-8')}")
            print("Tú: ", end="", flush=True)
        except:
            break

def main():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    print(f"Conectando al servidor relay en {SERVER_IP}:{SERVER_PORT}...")
    
    try:
        sock.connect((SERVER_IP, SERVER_PORT))
    except Exception as e:
        print(f"No se pudo conectar al servidor: {e}")
        return
        
    print("[*] Esperando a que otro usuario se conecte al chat...")
    
    # Esperamos la señal de que el segundo usuario se unió
    while True:
        msg = sock.recv(1024).decode('utf-8')
        if "CONECTADO" in msg:
            print("\n[+] ¡Emparejado con éxito! Ya puedes chatear.\n")
            break

    # Hilo para escuchar mensajes entrantes
    t = threading.Thread(target=receive_messages, args=(sock,), daemon=True)
    t.start()
    
    print("Escribe tus mensajes (escribe 'exit' para salir):\n")
    while True:
        try:
            text = input("Tú: ")
            if text.lower() == 'exit':
                break
            sock.sendall(text.encode('utf-8'))
        except KeyboardInterrupt:
            break
            
    sock.close()

if __name__ == "__main__":
    main()
