#!/usr/bin/env python
# encoding: utf-8
# Revisión 2014 Carlos Bederián
# Revisión 2011 Nicolás Wolovick
# Copyright 2008-2010 Natalia Bidart y Daniel Moisset
# $Id: server.py 656 2013-03-18 23:49:11Z bc $

import optparse
import socket
import os
import connection
import select
from constants import DEFAULT_DIR, DEFAULT_ADDR, DEFAULT_PORT


class AsyncServer(object):
    """
    Este servidor crea y atiende el socket en la dirección y puerto
    especificados donde se reciben nuevas conexiones de clientes.
    """
    def __init__(self, addr=DEFAULT_ADDR, port=DEFAULT_PORT,
                 directory=DEFAULT_DIR):
        print "Serving %s on %s:%s." % (directory, addr, port)
        self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server_socket.setblocking(0)
        self.server_socket.setsockopt(socket.SOL_SOCKET,
                                      socket.SO_REUSEADDR, 1)
        self.server_socket.bind((addr, port))
        self.server_socket.listen(10)
        self.directory = directory
        self.connections = {}
        try:
            os.mkdir(directory)
        except OSError:
            pass

    def serve(self):
        """
        Loop principal del servidor. Se aceptan multiples conexiones
        y se atienden en simultaneo.
        """
        # Poll object
        p = select.poll()
        p.register(self.server_socket, select.POLLIN)

        while True:
            for connec in self.connections.values():
                client_socket = connec.get_socket()
                if connec.to_remove():
                    print ("Disconnecting client: " + str(connec.address))
                    self.connections.pop(client_socket.fileno())
                    p.unregister(client_socket)
                    client_socket.close()
                else:
                    p.modify(client_socket, connec.events())

            events = p.poll()

            for fileno, event in events:
                if fileno == self.server_socket.fileno():
                    if event & select.POLLIN:
                        (client_socket,
                         client_address) = self.server_socket.accept()
                        client_socket.setblocking(0)
                        p.register(client_socket, select.POLLIN)
                        connec = connection.Connection(client_socket,
                                                       self.directory,
                                                       client_address)
                        self.connections[client_socket.fileno()] = connec
                        print('New client: ' + str(client_address))
                else:
                    if event & select.POLLIN:
                        self.connections[fileno].handle_input()

                    if event & select.POLLOUT:
                        self.connections[fileno].handle_output()


def main():
    """
    Parsea los argumentos y lanza el server.
    """
    parser = optparse.OptionParser()
    parser.add_option(
        "-p", "--port",
        help=u"Número de puerto TCP donde escuchar", default=DEFAULT_PORT)
    parser.add_option(
        "-a", "--address",
        help=u"Dirección donde escuchar", default=DEFAULT_ADDR)
    parser.add_option(
        "-d", "--datadir",
        help=u"Directorio compartido", default=DEFAULT_DIR)

    options, args = parser.parse_args()
    if len(args) > 0:
        parser.print_help()
        sys.exit(1)
    try:
        port = int(options.port)
    except ValueError:
        sys.stderr.write(
            "Numero de puerto invalido: %s\n" % repr(options.port))
        parser.print_help()
        sys.exit(1)
    server = AsyncServer(options.address, port, options.datadir)
    server.serve()

if __name__ == '__main__':
    main()
