# encoding: utf-8
# Copyright 2014 Carlos Bederián
# $Id: connection.py 455 2011-05-01 00:32:09Z carlos $

import socket
import select
import os
import os.path
import handle
from constants import BUFFSIZE, CODE_OK, BAD_EOL, INTERNAL_ERROR, EOL, \
    INVALID_COMMAND, INVALID_ARGUMENTS, FILE_NOT_FOUND, BAD_OFFSET, \
    commands_args, VALID_CHARS, error_messages, fatal_status


class Connection(object):
    """
    Conexión punto a punto entre el servidor y un cliente.
    Se encarga de satisfacer los pedidos del cliente hasta
    que termina la conexión.
    """
    def __init__(self, socket, directory, address=' '):
        self.socket = socket
        self.directory = directory
        self.buffer_in = ''
        self.buffer_out = ''
        self.address = address
        self.removed = False  # True cuando se pierde la conexión.
        self.gen = None
        self.quit = False  # True cuando se debe cerrar la conexión.

    def handle_output(self):
        """
        Envía la mayor cantidad de bytes posibles del contendio restante del
        buffer de salida al cliente. Si no se pueden enviar datos o se produce 
        un error, se pide la desconexión.

        Intenta leer lo que reste en el generador y luego atiende los pedidos
        que pueda haber en el buffer de entrada si no se pidio desconexión.
        """
        try:
            bytes_sent = self.socket.send(self.buffer_out)
            if bytes_sent == 0:
                self.removed = True
            self.buffer_out = self.buffer_out[bytes_sent:]
        except:
            self.removed = True

        # Lee el próximo fragmento y lo pone en el buffer de salida con el
        # formato correcto, solo si se está enviando un archivo.
        try:
            fragment = self.gen.next()
            self.buffer_out += "{} {}{}".format(len(fragment), fragment, EOL)
        except:
            self.gen = None
        # Si no se pidio desconectar la conexión, intento atender pedidos que
        # esten en el buffer de entrada esperando.
        if not (self.removed or self.quit):
            self.handle()

    def handle_input(self):
        """
        Se reciben datos del cliente y se guardan en el buffer de entrada.
        Se pide desconexión si no se reciben datos (cliente desconectado) o si
        se produce un error. Mientras atiende los pedidos que pueda haber en el
        buffer de entrada.
        """
        try:
            data = self.socket.recv(BUFFSIZE)
            self.buffer_in += data
            if len(data) == 0:
                self.removed = True
        except:
            self.removed = True

        # Si no se pidio desconectar la conexión, intenta atender pedidos que
        # esten en el buffer de entrada esperando.
        if not (self.removed or self.quit):
            self.handle()

    def handle(self):
        head = "{} {}{}"
        # Solo se atiende un pedido si se termino de atender al anterior, es
        # decir,  si el buffer de salida está vacío.
        if (EOL in self.buffer_in) and self.buffer_out == '':
            request, self.buffer_in = self.buffer_in.split(EOL, 1)
            code = self.valid_request(request)
            header = head.format(code, error_messages[code], EOL)

            if code == CODE_OK:
                #Se separa el pedido segun el protocolo.
                arg = request.split(' ')
                command = arg[0]
                # Se ejecuta el comando correcto.
                if command == "get_file_listing":
                    code, result = handle.get_file_listing(self.directory)
                    code = self.match_code(code)
                    if code == CODE_OK:
                        self.buffer_out += header
                        for file in result:
                            self.buffer_out += file + EOL
                        self.buffer_out += EOL
                elif command == "get_metadata":
                    code, size = handle.get_metadata(self.directory, arg[1])
                    code = self.match_code(code)
                    if code == CODE_OK:
                        self.buffer_out += header
                        self.buffer_out += "{}{}".format(size, EOL)
                elif command == "get_slice":
                    code, real_size = handle.get_metadata(self.directory,
                                                          arg[1])
                    code = self.match_code(code)
                    if code == CODE_OK:
                        code, offset, size = self.valid_offset(real_size,
                                                               arg[2], arg[3])
                        if code == CODE_OK:
                            self.gen = handle.get_slice(self.directory,
                                                        arg[1], offset, size)
                            code = self.gen.next()
                            code = self.match_code(code)
                            if code == CODE_OK:
                                self.buffer_out += header
                            else:
                                self.gen = None
                else:
                    self.buffer_out += header
                    self.quit = True

                if code != CODE_OK:
                    self.buffer_out += head.format(code,
                                                   error_messages[code], EOL)
            else:
                self.buffer_out += header

            if fatal_status(code):
                self.quit = True

    def valid_request(self, request):
        """
        Verifica si el pedido que envia el cliente es valido, devolviendo el
        codigo que corresponda. Para ser válido debe cumplir:
        1. No debe haber '\n' fuera del terminador.
        2. No posee caracteres inválidos.
        3. El comando existe.
        4. Tiene la cantidad de argumentos correctos.
        """
        req = request.split(' ')
        command = req[0]
        if '\n' in request:
            return BAD_EOL
        for char in request:
            if char not in VALID_CHARS and char != ' ':
                return INVALID_ARGUMENTS
        if command not in commands_args.keys():
            return INVALID_COMMAND
        if (len(req)-1) != commands_args[command]:
            return INVALID_ARGUMENTS
        return CODE_OK

    def valid_offset(self, real_size, string_offset, string_size):
        """
        Comprueba que los argumentos 'string_offset' y 'string_size' puedan
        convertirse en int, y que la suma de estos no sea
        mayor que 'real_size'.

        Retorna el código, seguido de offset y size como enteros.
        """
        offset, size = 0, 0
        try:
            offset, size = int(string_offset), int(string_size)
        except ValueError:
            return INVALID_ARGUMENTS, offset, size
        if (offset + size > real_size) or offset < 0:
            return BAD_OFFSET, offset, size
        return CODE_OK, offset, size

    def match_code(self, code):
        """
        Se encarga de traducir el código recibido del módulo handle en el
        correspondiente código del protocolo.
        """
        if code == handle.OK:
            return CODE_OK
        elif code == handle.NOT_DIR:
            return INTERNAL_ERROR
        elif code == handle.NOT_FILE:
            return FILE_NOT_FOUND
        elif code == handle.IO_ERROR:
            return INTERNAL_ERROR

    def events(self):
        """
        Devuelve los eventos que deberan ser capturados para la conexión en el
        momento que se llame al método.
        A la conexión siempre le interesan los eventos de entrada, mientras que
        los de salida solo le interesan si tiene datos para enviar.
        """
        if (self.buffer_out != ''):
            return select.POLLIN | select.POLLOUT
        else:
            return select.POLLIN

    def to_remove(self):
        """
        Determina si se debe cerrar la conexión. Esto depende si la
        conexión con el cliente se perdió o si se intenta cerrar. En el último
        caso, es posible que todavía queden datos por enviar.
        """
        return (self.quit and self.buffer_out == '') or self.removed

    def get_socket(self):
        """
        Devuelve el socket de la conexión.
        """
        return self.socket
