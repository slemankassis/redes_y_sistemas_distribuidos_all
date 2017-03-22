# encoding: utf-8
# $Rev: 512 $

"""
Módulo que provee manejo de conexiones genéricas.
"""

from socket import error as socket_error
import logging
from random import randint
from queue import Queue, ProtocolError
from config import BUFFSIZE, BAD_REQUEST, BAD_GATEWAY, FORBIDDEN, SEPARATOR, \
    INTERNAL_ERROR, PROTOCOL, PREFIX

# Estados posibles de la conexion
DIR_READ = +1  # Hay que esperar que lleguen más datos.
DIR_WRITE = -1  # Hay datos para enviar.


class Connection(object):
    """
    Abstracción de conexión. Maneja colas de entrada y salida de datos,
    y una función de estado (task). Maneja también el avance de la máquina de
    estados.
    """

    def __init__(self, fd, address=''):
        """
        Crea una conexión asociada al descriptor fd.
        """
        self.socket = fd
        self.task = None  # El estado de la maquina de estados.
        self.input = Queue()
        self.output = Queue()
        # Se setea a true para pedir al proxy que desconecte.
        self.remove = False
        self.address = address

    def fileno(self):
        """
        Número de descriptor del socket asociado.
        Este metodo tiene que existir y llamarse así para poder pasar
        instancias de esta clase a select.poll().
        """
        return self.socket.fileno()

    def direction(self):
        """
        Modo de la conexión, devuelve una de las constantes DIR_*; también
        puede devolver None si el estado es el final y no hay datos
        para enviar.
        """
        if self.output.data:
            return DIR_WRITE
        elif self.task is not None:
            return DIR_READ
        else:
            return None

    def recv(self):
        """
        Lee datos del socket y los pone en la cola de entrada.
        También maneja lo que pasa cuando el remoto se desconecta.
        Aquí va la única llamada a recv() sobre sockets.
        """
        try:
            data = self.socket.recv(BUFFSIZE)
            self.input.put(data)
            if len(data) == 0:
                self.remove = True
        except:
            self.remove = True

    def send(self):
        """
        Manda lo que se pueda de la cola de salida.
        """
        try:
            bytes_sent = self.socket.send(self.output.data)
            self.output.remove(bytes_sent)
        except:
            self.remove = True
            self.output.clear()

    def close(self):
        """
        Cierra el socket. También hay que avisarle al proxy que borre.
        """
        self.socket.close()
        self.remove = True
        self.output.clear()

    def send_error(self, code, message):
        """
        Función auxiliar para mandar un mensaje de error.
        """
        logging.warning(
            "Generating error response %s [%s]", code, self.address)
        self.output.put("HTTP/1.1 %d %s\r\n" % (code, message))
        self.output.put("Content-Type: text/html\r\n")
        self.output.put("\r\n")
        self.output.put(
            "<body><h1>%d ERROR: %s</h1></body>\r\n" % (code, message))
        self.remove = True


class Forward(object):
    """
    Estado: todo lo que venga lo retransmito a la conexión target.
    """

    def __init__(self, target):
        self.target = target

    def apply(self, connection):
        self.target.output.put(connection.input.data)
        connection.input.clear()

        if connection.remove:
            return None
        else:
            return self


class RequestHandlerTask(object):
    def __init__(self, proxy):
        self.proxy = proxy
        self.host = None
        self.url = None
        self.method = None
        self.protocol = None

    def apply(self, connection):
        if not self.url:
            try:
                self.method, self.url, self.protocol = (
                    connection.input.read_request_line())
                if not self.url:
                    return self
            except ProtocolError, e:
                connection.send_error(e.code, e.message)
                return None

        if connection.input.parse_headers():
            if not self.url.startswith('/'):  # URL absoluta.
                if not self.url.startswith(PREFIX):
                    connection.send_error(
                        BAD_REQUEST, 'Missing prefix http://')
                    return None

                self.host = self.url[len(PREFIX):]
                self.host = self.host.split('/', 1)[0]

                if not any('Host' in head for head in (
                           connection.input.headers)):
                    if self.protocol == 'HTTP/1.1':
                        connection.send_error(BAD_REQUEST, 
                            "Invalid request. Missing 'Host' header")
                        return None
                    connection.input.headers.append(['Host', ' ' + self.host])
            else:  # URL relativa.
                for header in connection.input.headers:
                    if header[0] == 'Host':
                        self.host = header[1].strip()

            if not self.host:
                connection.send_error(
                    BAD_REQUEST, "Invalid request. Missing host")
                return None

            if self.host not in self.proxy.host_map:
                connection.send_error(FORBIDDEN, "Invalid host")
                return None

            servers = self.proxy.host_map[self.host]
            ip = servers[randint(0, len(servers) - 1)]
            try:
                new_connection = self.proxy.connect(ip)
            except socket_error, e:
                connection.send_error(BAD_GATEWAY, e.strerror)
                return None
            except ValueError:
                connection.send_error(INTERNAL_ERROR, "Internal proxy error")
                return None

            new_connection.task = Forward(connection)
            new_connection.output.put("{} {} {}{}".format(
                self.method, self.url, PROTOCOL, SEPARATOR))
            new_connection.output.put('Connection: close' + SEPARATOR)
            for header in connection.input.headers:
                if header[0] != 'Connection':
                    new_connection.output.put('{}:{}{}'.format(
                        header[0], header[1], SEPARATOR))
            new_connection.output.put(SEPARATOR)
            return Forward(new_connection)
        else:
            return self
