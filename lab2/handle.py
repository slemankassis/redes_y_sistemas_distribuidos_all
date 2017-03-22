# encoding: utf-8
import os
import os.path

READBYTE = 4096
OK = 0
NOT_DIR = 1
NOT_FILE = 2
IO_ERROR = 3


def read_fragment(file_object):
    """
    Generador. Devuelve fragmentos leidos de 'file_object' hasta llegar
    al final del archivo.
    """
    while True:
        data = file_object.read(READBYTE)
        if not data:
            break
        yield data


def get_file_listing(directory):
    """
    Devuelve una lista de archivos presentes en el directorio 'directory', esta
    lista no contendrá subdirectorios.

    --- Código error ---
    NOT_DIR si el directorio no existe. Devuelve una lista vacía.
    """
    files = []
    try:
        files = os.listdir(directory)
    except OSError:
        return NOT_DIR, files
    for file in files:
        # Se remueven subdirectorios de la lista
        if os.path.isdir(os.path.join(directory, file)):
            files.remove(file)
    return OK, files


def get_metadata(directory, filename):
    """
    Devuelve el tamaño del archivo 'filename' que se encuentra en 'directory'.

    --- Código error ---
    NOT_DIR si el directorio no existe.
    NOT_FILE si el archivo no existe en el directorio o es inaccesible.

    Devuelven 0.
    """
    filesize = 0
    code, list_dir = get_file_listing(directory)
    if code != OK:
        return code, filesize
    if filename not in list_dir:
        return NOT_FILE, filesize
    try:
        filesize = os.path.getsize(os.path.join(directory, filename))
    except os.error:
        return NOT_FILE, filesize
    return OK, filesize


def get_slice(directory, filename, offset, size):
    """
    Generador. Devuelve fragmentos leídos del archivo 'filename' desde el
    offset dado hasta devolver 'size' bytes. El archivo se encuentra en el
    directorio 'directory'.
    Al finalizar devuelve una cadena vacía.

    El primer valor devuelto sera un código. Si este no es OK, quien creo el
    generador deberá cerrarlo.

    --- Precondición ---
    'filename' existe, es accesible y se encuentra en 'directory'.
    'offset' + 'size' <= "Tamaño archivo"

    --- Código error ---
    IO_ERROR si no puedo abrir el archivo para leerlo.
    """
    # Se abre archivo para obtener fragemntos.
    try:
        readfile = open(os.path.join(directory, filename))
    except IOError:
        yield IO_ERROR
    yield OK
    # Se posiciona en el offset correspondiente.
    readfile.seek(offset)
    # Devuelve fragmento por fragmento, hasta devolver 'size' bytes.
    for fragment in read_fragment(readfile):
        # Al tamaño que falta enviar se le resta el tamaño del fragmento.
        size -= len(fragment)
        # Si el fragmento contiene más de lo que falta enviar, se tira el
        # sobrante.
        if size < 0:
            fragment = fragment[:size]
            yield fragment
            break
        else:
            yield fragment
    # Devuelve cadena vacía al terminar.
    yield ''
    readfile.close()
