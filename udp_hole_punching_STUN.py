import socket

# Configuracion del servidor de señalizacion
servidor_puerto = 12345
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(("0.0.0.0", servidor_puerto))

print(f"Servidor de señalizacion escuchando en puerto {servidor_puerto}...")

# Diccionario para almacenar los clientes conectados
clientes = {}

while True:
    data, addr = sock.recvfrom(1024)
    print(f"Recibido mensaje desde {addr[0]}:{addr[1]} con datos: {data.decode()}")
    
    # El servidor obtiene automáticamente la IP y el puerto del cliente que envió el paquete
    clientes[addr] = f"{addr[0]}:{addr[1]}"  # Almacenar la IP y el puerto del cliente

    # Verificar si hay al menos dos clientes
    if len(clientes) >= 2:
        # Obtener los clientes conectados
        cliente1, cliente2 = list(clientes.keys())[:2]

        # Enviar la direccion del cliente 1 al cliente 2 y viceversa
        sock.sendto(clientes[cliente2].encode(), cliente1)
        sock.sendto(clientes[cliente1].encode(), cliente2)
        print(f"Informacion de peer enviada a ambos clientes: {clientes[cliente1]} <-> {clientes[cliente2]}")
