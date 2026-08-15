import socket
import json
import os


class Message:
    def __init__(self, head, body, start_line):
        self.head = head
        self.body = body
        self.start_line = start_line

def parse_HTTP_message(http_message: bytes):

    particiones = http_message.split(b"\r\n\r\n")
    listhead = particiones[0].decode("utf-8").split("\r\n")
    start_line = listhead[0]
    head = {}
    for linea in listhead[1:]:
        data = linea.split(": ")
        head[data[0]] = data[1]
    body = particiones[1]
    return Message(head,body, start_line)

# test
mensajeoriginal = b"HTTP/1.1 200 OK\r\nContent-Type: text/html; charset=utf-8\r\nContent-Length: 44\r\nServer: nginx/1.18.0\r\nConnection: close\r\n\r\n<html><body><h1>Hola mundo</h1></body></html>"
mensaje = parse_HTTP_message(mensajeoriginal)

def create_HTTP_message(message):
    head = message.head
    body = message.body
    data = message.start_line.encode("utf-8")
    data += b"\r\n"

    for key, value in head.items():
        data += key.encode("utf-8") + b": " + value.encode("utf-8")
        data += b"\r\n"

    data += b"\r\n"

    data += body

    return data

# test
mensajebytes = create_HTTP_message(mensaje)
#print(mensajeoriginal)
#print(mensajebytes)
assert mensajeoriginal == mensajebytes

# Definimos una respuesta estandar

start_line = "HTTP/1.1 200 OK"

with open("test.html", "rb") as f:
    body = f.read()

with open("config.json") as file:
    data = json.load(file)
    nombre = data["X-ElQuePregunta"]

head = {
"Server": "nginx/1.17.0",
"Date": "Thu, 13 Aug 2026 00:02:45 GMT",
"Content-Type": "text/html; charset=utf-8",
"Content-Length": str(len(body)),
"Connection": "keep-alive",
"Access-Control-Allow-Origin": "*",
"X-ElQuePregunta": nombre,
}

response = Message(head,body,start_line)

# Creacion servidor

IP_VM = "192.168.1.193"
socket_adress = (IP_VM,8000)

print("Creando socket - Servidor")

server_socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
server_socket.bind(socket_adress)

server_socket.listen(3)
print("...Esperando clientes")
while True:
    new_socket, new_socket_address = server_socket.accept()
    recv_message = parse_HTTP_message(new_socket.recv(4096))

    print(f"Se ha recibido con exito el mensaje: {recv_message.head}")

    new_socket.send(create_HTTP_message(response))
    new_socket.close()

    print(f"conexion con {new_socket_address} ha sido cerrada")


