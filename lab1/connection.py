# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
import os
import os.path
from constants import EOL, BUFFSIZE, CODE_OK, BAD_EOL, BAD_REQUEST, \
    INTERNAL_ERROR, INVALID_COMMAND, INVALID_ARGUMENTS, FILE_NOT_FOUND, \
    BAD_OFFSET, error_messages, commands_args, fatal_status, VALID_CHARS


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """

    def __init__(self, socket, directory):
        self.clientsocket = socket
        self.directory = directory
        self.bufferin = ''
        self.bufferout = ''

    def send(self):
        """
        Envía lo que quede en el buffer de salida al cliente.

        """
        while self.bufferout:
            bytes_sent = self.clientsocket.send(self.bufferout)
            assert bytes_sent > 0
            self.bufferout = self.bufferout[bytes_sent:]

    def valid_request(self, request):
        """
        Verifica si el pedido que envia el cliente es valido, devolviendo el
        codigo que corresponda. Para ser válido debe cumplir:
        1. No hay '\n' fuera del terminador
        2. No posee caracteres inválidos
        3. El comando existe
        4. Tiene la cantidad de argumentos correctos
        """
        req = request.split(' ')
        command = req[0]
        if '\n' in request:
            return BAD_EOL
        for char in list(request):
            if char not in VALID_CHARS and char != ' ':
                return INVALID_ARGUMENTS
        if command not in commands_args.keys():
            return INVALID_COMMAND
        if (len(req)-1) != commands_args[command]:
            return INVALID_ARGUMENTS
        return CODE_OK

    def read_fragment(self, file_object):
        """
        Lee fragmentos de 'file_object' hasta llegar al final del archivo.
        """
        while True:
            data = file_object.read(BUFFSIZE)
            if not data:
                break
            yield data

    def get_file_listing(self):
        """
        Devuelve el código de exito y una cadena con el nombre de cada archivo
        presente en el servidor seguido por el terminador del protocolo y un
        terminador extra al final para indicar que no hay más archivos.

        Si se produce un error, devuelve el código de error y una cadena vacía.
        """
        result = ''
        try:
            dirs = os.listdir(self.directory)
        except OSError:
            return INTERNAL_ERROR, result
        for file in dirs:
            if not os.path.isdir(os.path.join(self.directory, file)):
                result += file + EOL
        result += EOL
        return CODE_OK, result

    def get_metadata(self, filename):
        """
        Devuelve codigo de éxito y una cadena con el tamaño del archivo seguida
        por el terminador de protocolo.
        Si el archivo 'filename' no existe devuelve el código de error adecuado
        y una cadena vacía.
        """

        result = ''
        code, listdir = self.get_file_listing()
        if filename not in listdir.split(EOL):
            return FILE_NOT_FOUND, result
        try:
            filesize = os.path.getsize(os.path.join(self.directory, filename))
        except os.error:
            return FILE_NOT_FOUND, result
        result += str(filesize) + EOL
        return CODE_OK, result

    def get_slice(self, filename, offset, size):
        """
        Envía al cliente una parte del archivo 'filename', comenzando desde
        la posición 'offset' y de tamaño 'size'.

        Se enviara en uno o varios fragmentos.
        Por cada uno de estos se enviará el tamaño del fragmento, un espacio y
        el fragmento seguido por el terminador del protocolo. El ultimo mensaje
        sera un 0 seguido del terminador del protocolo para indicar que se
        enviaron todos los fregmentos.

        Si finaliza correctamente, devolvera el código de éxito.

        Devolverá un código de error en los siguientes casos:
        1. 'filename' no existe en el servidor.
        2. 'offset' o 'size' no tienen el tipo correcto.
        3. Se produce un error al intentar leer el archivo.
        """
        code, realsize = self.get_metadata(filename)
        if code != CODE_OK:
            return code
        realsize = int(realsize.split(EOL)[0])
        try:
            offset, size = int(offset), int(size)
        except ValueError:
            return INVALID_ARGUMENTS
        if offset + size > realsize:
            return BAD_OFFSET
        try:
            readfile = open(os.path.join(self.directory, filename))
        except IOError:
            return INTERNAL_ERROR

        readfile.seek(offset)

        for fragment in self.read_fragment(readfile):
            size -= len(fragment)
            if size < 0:
                fragment = fragment[:size]
            self.bufferout += str(len(fragment)) + ' ' + fragment + EOL
            self.send()
            if size < 0:
                break
        self.bufferout += "0 " + EOL
        readfile.close()
        return CODE_OK

    def handle(self):
        """
        Atiende eventos de la conexión hasta que termina.
        """
        connectionquit = False

        while not connectionquit:
            data = self.clientsocket.recv(BUFFSIZE)
            self.bufferin += data
            if len(data) == 0:
                connectionquit = True
                continue
            if EOL in self.bufferin:
                request, self.bufferin = self.bufferin.split(EOL, 1)
                code = self.valid_request(request)
                self.bufferout = str(code) + ' ' + error_messages[code] + EOL
                if code == CODE_OK:
                    arg = request.split(' ')
                    command = arg[0]
                    result = ''
                    if command == "get_file_listing":
                        code, result = self.get_file_listing()
                    elif command == "get_metadata":
                        code, result = self.get_metadata(arg[1])
                    elif command == "get_slice":
                        code = self.get_slice(arg[1], arg[2], arg[3])
                    else:
                        connectionquit = True

                    self.bufferout += result

                    if code != CODE_OK:
                        self.bufferout = str(code) + ' ' + \
                            error_messages[code] + EOL
                if fatal_status(code):
                    connectionquit = True
                self.send()

        self.clientsocket.close()
