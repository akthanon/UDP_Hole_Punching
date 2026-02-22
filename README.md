# UDP Hole Punching – Chat P2P por Terminal

Este proyecto implementa un **chat P2P por UDP** entre dos clientes ubicados detrás de **NATs diferentes**, utilizando la técnica de **UDP Hole Punching** y un **servidor de señalización (tipo STUN simplificado)**.

El servidor solo se utiliza para el **intercambio inicial de direcciones IP y puertos**; una vez establecida la comunicación, los clientes se comunican **directamente entre sí**.

---

## 📐 Arquitectura

Cliente A (NAT)  
↕  
Servidor de señalización (IP pública)  
↕  
Cliente B (NAT)

Una vez completada la señalización:

Cliente A ↔ Cliente B (UDP P2P)

---

## 📦 Componentes

### 1. Servidor de señalización
- Escucha conexiones UDP.
- Detecta automáticamente la IP y puerto público de cada cliente.
- Intercambia la información de conexión entre los clientes.
- **No participa en la comunicación final.**

### 2. Cliente UDP P2P
- Se conecta al servidor de señalización.
- Obtiene la IP y puerto del peer remoto.
- Envía paquetes UDP repetidos para perforar el NAT.
- Establece un chat por terminal usando UDP directo.

---

## ⚙️ Requisitos

- Python 3.x
- Acceso a red (local o Internet)
- Un servidor accesible públicamente para la señalización
- Dos clientes detrás de NAT (idealmente NATs distintos)

---

## 🚀 Uso

### 1️⃣ Ejecutar el servidor de señalización

En una máquina con IP accesible (preferiblemente pública):

```bash
python servidor.py
```

Salida esperada:
```
Servidor de señalizacion escuchando en puerto 12345...
```

---

### 2️⃣ Configurar el cliente

Editar en el archivo del cliente:

```python
servidor_ip = "IP_DEL_SERVIDOR"
servidor_puerto = 12345
mi_puerto = 33342
```

> Cada cliente debe usar **un puerto local distinto**.

---

### 3️⃣ Ejecutar los clientes

En cada cliente:

```bash
python cliente.py
```

Flujo esperado:
1. El cliente envía un `PING` al servidor.
2. El servidor responde con la IP:PUERTO del otro cliente.
3. Ambos clientes envían paquetes UDP entre sí.
4. Se abre el mapeo del NAT.
5. El chat queda listo.

---

## 💬 Funcionamiento del Chat

- Cada cliente puede escribir mensajes por terminal.
- Los mensajes se envían directamente al peer por UDP.
- No hay cifrado (ideal para análisis y aprendizaje).
- No hay control de sesión ni autenticación.

---

## 🧠 Conceptos Aplicados

- UDP Hole Punching
- NAT Traversal
- Comunicación P2P
- Sockets UDP
- Servidores de señalización
- Multithreading básico en Python

---

## ⚠️ Limitaciones

- No funciona con NATs simétricos estrictos.
- No maneja más de 2 clientes.
- No implementa reconexión automática.
- No incluye seguridad ni cifrado.
- El servidor mantiene clientes en memoria sin limpieza.

---

## 🎯 Uso Educativo

Este proyecto está diseñado para:
- Laboratorios de redes
- Clases de ciberseguridad
- Comprender NAT traversal
- Demostraciones prácticas de P2P

No está pensado para uso en producción.

---

## 📌 Posibles Mejoras

- Soporte para múltiples pares de clientes
- Timeouts y limpieza de clientes
- Cifrado de mensajes
- Detección de tipo de NAT
- Interfaz gráfica
- Uso de protocolos STUN reales

---

## 📜 Licencia

Proyecto educativo. Uso libre para aprendizaje y enseñanza.
