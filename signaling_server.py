import socket
import threading

HOST = '0.0.0.0'
PORT = 5000

clients = []

def relay_traffic(c1, c2):
    """Mantiene un puente bidireccional retransmitiendo mensajes entre ambos clientes"""
    def forward(source, destination):
        try:
            while True:
                data = source.recv(4096)
                if not data:
                    break
                destination.sendall(data)
        except:
            pass
        finally:
            try: source.close()
            except: pass
            try: destination.close()
            except: pass

    t1 = threading.Thread(target=forward, args=(c1, c2), daemon=True)
    t2 = threading.Thread(target=forward, args=(c2, c1), daemon=True)
    t1.start()
    t2.start()

def handle_server():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    print(f"[*] Servidor Relay/Señalización activo en el puerto {PORT}...")
    
    while True:
        conn, addr = server.accept()
        print(f"[+] Nuevo cliente conectado desde {addr}")
        clients.append(conn)
        
        # Cuando hay 2 clientes, los emparejamos y abrimos el puente de comunicación
        if len(clients) >= 2:
            c1 = clients.pop(0)
            c2 = clients.pop(0)
            print("[*] ¡Emparejamiento exitoso! Abriendo canal de retransmisión...")
            
            # Avisamos a ambos que ya están conectados
            try:
                c1.sendall(b"CONECTADO\n")
                c2.sendall(b"CONECTADO\n")
            except:
                continue
            
            # Iniciamos el retransmisor en segundo plano
            threading.Thread(target=relay_traffic, args=(c1, c2), daemon=True).start()

if __name__ == "__main__":
    handle_server()
