# Introducción

En este laboratorio se diseña e implementa un programa servidor de archivos basado en el protocolo HFTP. El programa cliente fue dado por la cátedra. El cliente y el servidor se pueden ejecutar en distintas maquinas pero sobre la misma red.
Para la nomenclatura de variables se selecciono "mivariable" (todo minúsculas y seguido) y para funciones "mi_función" (todo minúsculas y con _).

# Estructura del Servidor (server.py)

Se crea un socket para que haya un canal de comunicación entre un servidor y un cliente, en este caso son ambos locales. Para ello utilizamos la librería de python socket.
Utilizamos los constantes testdata, localhost y 19500 que son valores predeterminados para directory, address y port.
En la inicialización de los atributos se crea un socket de familia AF_INET y de tipo SOCK_STREAM, se agrega una función setsockopt para que deje habilitado el mismo puerto rápidamente cuando estemos probando ya en la terminal la conexión, se setea bind con la tupla que contiene la dirección y el puerto y listen con cantidad de publico igual a 1, finalmente al atributo directory de self le asignamos el directorio del servidor, que es localhost en este caso.
Luego en la función serve nos faltaba aceptar la conexión y crear la Connection para la conexión propiamente dicha y atenderla hasta que terminase. Se logra con la función accept del atributo serversocket asignándole a un clientsocket y clientaddr, el clientsocket se utiliza junto con directory para crear un objeto 'myconnection' de la clase Connection (que esta en el modulo connection). Y por ultimo se llama a handle desde myconnetion.
La función main venia implementada ya en el esqueleto, se ocupa en resumen de hacer el parser de los argumentos y lanzar el server.

# Estructura de la Conexión (connection.py)

Se inicializan los atributos clientsocket y directory. Además se crean 2 buffers para poder recibir al servidor y enviar al cliente: bufferin y bufferout. Además se crea una constante en constants.py para el tamaño de buffer que sera el tamaño del paquete de red, se decide hacerlo de 2^12 bytes.
En esta estructura debemos implementar handle que es el encargado de enviar y recibir los pedidos. Para la implementación creamos una variable connectionquit bandera inicializada en false que cuando sucede un estado fatal o el cliente pide terminar la conexión, es la encargada de salir del loop principal para cerrar la conexión.
Dentro del loop nos encargamos de verificar que el pedido sea válido, que comando es y que función ejecutar. Se ayuda esta implementación con un diccionario creado en constants.py con los 4 comandos y la cantidad de argumentos que requiere.
Respecto a las decisiones de diseños elegimos que las funciones implementadas devuelvan 2 resultados: code, de aceptación o error definidos en constants.py, y result, que es el resultado a enviar al cliente.

## valid_request
El problema que nos surgió fue como comprobar si el comando existía y si la cantidad de argumentos era correcta. Para ello, creamos un diccionario *comands_args* en el que las entradas eran los comandos y la definición la cantidad de argumentos. De esta forma, con los métodos de un diccionario podíamos corroborar si el comando estaba entre las entradas y también saber cuantos argumentos tomaba.

## get_file_listing
Al listar los archivos, no queríamos listar los directorios que pudieran estar en la carpeta. Para esto utilizamos *os.path.isdir* junto con *os.path.join* para excluir a los directorios del resultado.

## get_metadata
Al obtener el tamaño del archivo, no queríamos que el cliente pueda ver el de directorios o archivos fuera del directorio del server. Para ello llamamos a get_file_listing y así saber que archivos puede ver el cliente.

## get_slice
Aquí fue donde surgieron más problemas o casos a tener en cuenta. Lo primero era no poder leer archivos que no correspondían y lo segundo fue que podía haber archivos demasiado grandes.
Lo primero se soluciono utilizando get_metadata para obtener el tamaño del archivo. Como consideramos en dicha función qué archivos se podían ver, utilizamos el código que devuelve para solucionar el primer problema y el tamaño para controlar si el cliente quería leer por fuera del archivo.
Para poder leer archivos grandes, utilizamos generadores. Creamos un método **read_fragment** que lee el un archivo por fragmentos de tamaño, devolviendo cada fragmento con yield. Si un fragmento es más grande de lo que faltaba leer, se tira la ultima parte para enviar exactamente lo que pidió el cliente.

# Bibliografía

### Librerías de python: python.org y tutorialspoint.com
### Consultas en general: stackoverflow.com
