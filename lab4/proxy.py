# encoding: utf-8
import socket
import select
import logging

from connection import Connection, DIR_READ, DIR_WRITE, RequestHandlerTask, \
    Forward


class Proxy(object):
    """
    Proxy HTTP.
    """

    def __init__(self, port, hosts):
        """
        Inicializar, escuchando en port, y sirviendo los hosts indicados en
        el mapa 'hosts'.
        """

        # Conexión maestra (entrante).
        master_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        master_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        master_socket.bind(('', port))
        logging.info("Listening on %d", port)
        master_socket.listen(5)
        self.host_map = hosts
        self.connections = []
        self.master_socket = master_socket

    def run(self):
        """
        Manejar datos de conexiones hasta que todas se cierren.
        """
        while True:
            self.handle_ready()
            p = self.polling_set()
            # Poll.
            events = p.poll()

            self.handle_events(events)
            self.remove_finished()

    def polling_set(self):
        """
        Devuelve objeto polleable, con los eventos que corresponden a cada
        una de las conexiones.
        Si alguna conexión tiene procesamiento pendiente (que no requiera
        I/O) realiza ese procesamiento antes de poner la conexión en el
        conjunto.
        """
        p = select.poll()
        p.register(self.master_socket, select.POLLIN)
        for c in self.connections:
            if c.direction() == DIR_READ:
                p.register(c, select.POLLIN)
            elif c.direction() == DIR_WRITE:
                p.register(c, select.POLLOUT)
        return p

    def connection_with_fd(self, fd):
        """
        Devuelve la conexión con el descriptor fd.
        """
        for c in self.connections:
            if c.fileno() == fd:
                return c
        assert False

    def handle_ready(self):
        """
        Hace procesamiento en las conexiones que tienen trabajo por hacer,
        es decir, las que están leyendo y tienen datos en la cola de entrada.
        """
        for c in self.connections:
            # Hacer avanzar la máquina de estados.
            if c.input.data:
                c.task = c.task.apply(c)

    def handle_events(self, events):
        """
        Maneja eventos en las conexiones. events es una lista de pares
        (fd, evento).
        """
        for fd, event in events:
            if fd == self.master_socket.fileno():
                if event & select.POLLIN:
                    self.accept_new()
            else:
                c = self.connection_with_fd(fd)
                if event & select.POLLIN:
                    c.recv()
                if event & select.POLLOUT:
                    c.send()

    def accept_new(self):
        """
        Acepta una nueva conexión.
        """
        sock, address = self.master_socket.accept()
        sock.setblocking(0)
        connection = Connection(sock, address)
        connection.task = RequestHandlerTask(self)
        self.append(connection)

    def remove_finished(self):
        """
        Elimina conexiones marcadas para terminar.
        """
        for c in self.connections:
            if c.remove is True and not c.output.data:
                if isinstance(c.task, Forward):
                    c.task.target.remove = True
                c.close()
                self.connections.remove(c)

    def connect(self, hostname):
        """
        Establece una nueva conexión saliente al hostname dado.
        El hostname puede tener la forma host:puerto y si se omite el
        :puerto se asume puerto 80.

        Aquí está la única llamada a connect() del sistema.
        No preocuparse por el caso de connect() bloqueante.
        """
        port = 80
        if ':' in hostname:
            hostname, port = hostname.split(':', 1)
            port = int(port)
        new_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        new_socket.connect((hostname, port))
        new_socket.setblocking(0)
        new_connection = Connection(new_socket)
        self.append(new_connection)
        return new_connection

    def append(self, c):
        self.connections.append(c)
