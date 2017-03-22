# Introducción

En este laboratorio se implementa un servidor que pueda atender varios clientes al mismo tiempo y que sea escalable, es decir que si hay muchos clientes no tenga mal funcionamiento. Se utiliza la syscall poll para multiplexar las conexiones del servidor. El objetivo además es evitar la conexiones bloqueantes, para poder atender a distintos clientes en simultaneo.
Para este laboratorio, utilizamos los siguientes módulos:

+ os
+ os.path
+ socket
+ select
+ handle (implementado en este laboratorio)


# server.py


## Inicialización AsyncServer

Se crea un socket para el servidor, sobre el cual se escucharán pedidos de conexión. Este socket se configura como no bloqueante, para poder atender a las conexiones ya aceptadas mientras se esperan nuevas conexiones. Además se configura el socket para que el puerto quede libre en caso de que se caiga el servidor y este no sea cerrado.

Una vez configurado el socket, se le asigna una dirección con bind y se comienza a escuchar sobre esa dirección. Por último se agrega el directorio sobre el que usaremos el servidor y se crea un diccionario *connections* para guardar las conexiones.

## serve

Crea un objeto poll *p* en el que se registra el servidor esperando eventos de entrada y luego se registraran las distintas conexiones, esperando solo eventos de entrada la primer vez.

Tiene 1 ciclo principal e infinito que contiene 2 iteraciones dentro.
#### Primera iteración
 Chequea el estado de todas las conexiones actuales.
 Si la conexión esta marcada para remover entonces imprime el mensaje de desconexión, se elimina del diccionario *connections*, se desregistra del objeto poll *p* y se cierra el socket.
 Si no esta para remover la conexión entonces va a modificar *p* con los eventos que espera la conexión en ese momento.

#### Segunda iteración
Antes de esta iteración se llama a **poll()** para controlar los eventos que hay registrados.
Luego se atiende cada evento según corresponda.
Hay 2 casos posibles que serán atendidos:

 1. Es un evento de entrada del servidor.
 2. Es un evento de entrada o salida de una conexión.

En el primer caso, significa que un nuevo cliente quiere conectarse. Entonces se acepta la conexión, se configura el socket de la conexión como no bloqueante, se registra en el poll *p* esperando eventos solo de entrada y se agrega al diccionario de conexiones, con el *fileno* del socket de la conexión. Finalmente se indica por pantalla la conexión del nuevo cliente.

En el segundo caso, si el evento es de entrada se llamara al método **handle_input()** de la conexión y si es de salida al método **hanlde_output()**. Pueden ocurrir ambos eventos y se atenderán uno seguido del otro.


## main

Parsea los argumentos y lanza el server.


# handle.py


Se decidió crear este nuevo módulo para que la clase *Connection* no este sobrecargada. Se independizo el módulo del protocolo tanto como fue posible. Hubiera sido más correcto utilizar excepciones, pero queda pendiente para el futuro.


## read_fragment

Este método es un generador que devuelve fragmentos de un archivo hasta terminar de leerlo. Se utiliza como método auxiliar para get_slice.


## get_file_listing

Devuelve la lista de archivos presentes en un directorio, esta lista no contendrá subdirectorios. Acompañando a esta lista, el método devuelve un código especificado en el módulo para detectar errores.


## get_metadata

Devuelve el tamaño de un archivo existente en un directorio específico. Además devuelve un código establecido en el módulo como constante, para poder detectar errores.


## get_slice

Este generador devuelve en su primer iteración un código especificado en el módulo. Si se trata de un código de error se debe cerrar el generador.

En las siguientes iteraciones devuelve fragmentos del archivo pasado como argumento desde el offset indicado hasta completar el tamaño que se pidió.
La iteración final devuelve una cadena vacía para indicar que ya se termino de leer el archivo.

La función que llame este método deberá corroborar que el offset y el tamaño requerido son validos.


# connection.py


## Inicialización Connection

Se asigna el socket de la conexión y el directorio sobre el que esta operara. Luego se inicializan dos buffer, uno de entrada *buffer_in* y otro de salida *buffer_out* y se asigna la dirección del cliente conectado.
Los últimos tres atributos de la conexión son dos banderas *quit* y *removed* inicializadas en False para corroborar si la conexión debe ser cerrada y un generador *gen* inicializado en None. La diferencia entre *quit* y *removed* es que en el primer caso todavía puede haber cosas para enviar, mientras que en el segundo la conexión ya se perdió y no podre enviar nada más.


## handle_output

Este método se encarga de enviar el contenido del buffer de salida. Enviara todo la mayor cantidad de bytes posibles con una sola llamada a send(). Marca la conexión como perdida si ocurre un error.

Una vez que envío datos, se intentara leer el próximo fragmento del generador.
Esto se implemento así para que cuando el cliente pida un archivo demasiado grande no se bloquee enviando todo el archivo y pueda mandarlo en fragmentos.

Luego, si la conexión no esta marcada para ser cerrada se llama a **handle()** para atender los comandos que puedan quedar en el buffer de entrada. Esto se decidió para poder atender los comandos sin que sea necesario otro pedido del cliente.


## handle_input
Este método se encarga de recibir los datos del cliente, marcando la conexión como perdida si se reciben 0 bytes o si ocurre un error.

Luego, si la conexión no esta marcada para ser cerrada se llama a **hanlde()** para atender los comandos que se puedan haber recibido.


## handle
Se encarga de manejar los pedidos realizados por el cliente. Solo intentara leer un mensaje si ya se termino de procesar el pedido anterior, es decir, el buffer de salida esta vacío.

Si se encuentra un pedido en el buffer de entrada, primero se corrobora que sea válido y de ser así se procesa según el comando que contenga.

En el caso de *get_file_listing* y *get_metadata*, se utilizan los respectivos métodos en el modulo handle para obtener la información y luego se la formatea para que cumpla con el protocolo, agregando las respuestas al buffer de salida.

En el caso que el comando sea *quit*, se activa el flag quit y se pone el encabezado en el buffer de salida.

En el caso *get_slice*, se crea el generador con el respectivo método del modulo handle, se pide el código y luego se ira leyendo los fragmentos y formateándolos cada vez que se llame a **handle_output** desde el servidor.

## valid_request
Controla que un pedido realizado por el cliente respete el protocolo. Devuelve el error correspondiente en caso de no hacerlo.

Para implementarlo se decidió definir un diccionario en el que las claves son los comandos validos y los valores la cantidad de argumentos que toma cada comando.

## valid_offset
Cuando el cliente pida un fragmento de un archivo, este método se encarga de corroborar que el offset y tamaño enviados en el pedido del cliente tengan el tipo correcto, como así también corroborar que el offset sea válido y que sumado con el tamaño no superen el final del archivo.

Cuando se llama al método el offset y el tamaño son cadenas, por ello el método también se encarga de convertirlos a enteros y devolverlos con su tipo correcto.

## match_code
Convierte un código del módulo handle en el correspondiente código del protocolo.

## events
Devuelve cuales son los eventos que le interesan a la conexión en el momento que se llama al método. Para ello utiliza las constantes del módulo *select*, *POLLIN* y *POLLOUT*.

Siempre se esperan eventos de entrada, pero solo se esperan de salida si hay datos en el buffer de salida.

## to_remove
Indica si se debe cerrar la conexión.

Solo se deberá cerrar si *removed* esta activado o si *quit* esta activado y no quedan datos por enviar.

## get_socket
Devuelve el socket de la conexión.
