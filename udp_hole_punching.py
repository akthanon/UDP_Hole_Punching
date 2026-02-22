import socket
import threading
import time

# Configuración del servidor de señalización
servidor_ip = "192.168.100.185"  # IP del servidor de señalización (la misma IP del servidor)
servidor_puerto = 12345  # Puerto del servidor de señalización

# Configuración manual de la conexión
mi_puerto = int(33342)

# Crear socket UDP
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", mi_puerto))

# Función para escuchar mensajes entrantes
def recibir_mensajes():
    while True:
        try:
            data, addr = sock.recvfrom(1024)
            print(f"\n[Mensaje de {addr[0]}:{addr[1]}] {data.decode()}\n> ", end="")
        except:
            break

# Enviar paquete inicial para perforar NAT
print("Conectando al servidor de señalización...")
sock.sendto(b"PING", (servidor_ip, servidor_puerto))

# Esperar por la respuesta del servidor con la información del peer
print("Esperando información del otro cliente...")

data, _ = sock.recvfrom(1024)
peer_info = data.decode()
print(f"Recibido del servidor: {peer_info}")

# Extraer IP y puerto del otro cliente desde la respuesta del servidor
peer_ip, peer_puerto = peer_info.split(":")

print(f"Conectando con el peer {peer_ip}:{peer_puerto}")

# Enviar paquetes para perforar el NAT
print("Enviando paquetes para abrir el NAT...")
for _ in range(10):  # Aumentamos el número de paquetes
    sock.sendto(b"PING", (peer_ip, int(peer_puerto)))
    time.sleep(0.5)  # Aumentamos el tiempo de espera entre paquetes

print("Conexión lista. Escribe para enviar mensajes:")

# Iniciar hilo para recibir mensajes
threading.Thread(target=recibir_mensajes, daemon=True).start()

# Bucle para enviar mensajes
while True:
    msg = input("> ")
    sock.sendto(msg.encode(), (peer_ip, int(peer_puerto)))
