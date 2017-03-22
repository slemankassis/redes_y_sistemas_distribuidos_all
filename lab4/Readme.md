# Introdución

En este laboratorio se implementa un **proxy reverso** (del lado del cliente) del protocolo **HTTP 1.1** que balancea la carga entre múltiples servidores y además atiende varios clientes de forma concurrente. HTTP 1.1 permite conexiones persistentes.

Funciona únicamente con los sitios que están agregados en **config.py**, si se ingresa a uno que no está en esa lista va a devolver un mensaje de error.

Un **proxy** es un intermediario entre cliente y servidor. Los pedidos del cliente van al proxy en vez de al servidor final, y el proxy actúa como cliente ante el servidor _(C->P->S)_. La respuesta del servidor es enviada al proxy, quien entonces se la retorna al cliente _(S->P->C)_.


Donde

+ S = Servidor

+ C = Cliente

+ P = Proxy


El proxy se implementa con 5 módulos:

+ **connection**

+ **proxy**

+ **queue** Contiene al objeto **ProtocolError** implementado para devolver código de error y mensaje y **Queue** que es una implementación para los buffers con las operaciones básicas más las funciones para leer los request y parsear sus encabezados.

+ **config** Contiene las constantes y el diccionario de hosts que se van a permitir.

+ **main** Ejecuta el proxy.


Estos últimos 3 fueron provistos por la cátedra.

**connections** y **proxy** se detallan a continuación.


## connection.py

Consta de 3 objetos: **Connection**, **Forward** y **RequestHandlerTask**.

Utiliza 2 constantes principales que indican el estado posible de la conexión: **DIR_READ** y **DIR_WRITE**, la primera indica que falta que lleguen datos y hay que esperar y se representa con el valor numérico **+1**, mientras que la segunda indica que hay aún datos por envíar y se representa con el número **-1**.


### Connection (objeto)

Es la abstracción de la conexión. Maneja colas de entrada y salida de datos, y una función de estado llamada **task**. Maneja también el avance de la máquina de estados.


#### Inicialización

El objeto tiene 6 atributos:

+ **socket** El socket fd.

+ **task** Las tareas.

+ **input** El buffer de entrada.

+ **output** El buffer de salida.

+ **remove** Una variable bandera que con valor booleano indica si la conexión se puede desconectar (el proxy).

+ **address** Es la dirección y se la inicializa con **''**.


Ambos bufferes se inicializan como cola, el objeto queue se importa del módulo **queue.py**.


##### fileno

Número de descriptor del socket asociado. Se usa para pasar las instancias de esta clase a **select.poll**.


##### direction

Modo de la conexión, devuelve **DIR_READ** o **DIR_WRITE** o bien None si el estado es el final y no hay datos para enviar.


##### recv

Lee datos del socket y los pone en la cola de entrada considerando qué pasa si el remoto se desconecta. Aquí va la única llamada a **recv** sobre sockets.


##### send

Manda lo que se pueda de la cola de salida.


##### close

Cierra la conexión socket y setea el atributo **remove** a True.


##### send error

Función auxiliar para mandar un mensaje de error.


### Forward (objeto)

Es el objeto que se encarga de la retransmición.


#### Inicialización

Se crea el atributo de la conexión para **target**.


##### apply

Se encarga de ir añadiendo al buffer de salida de **target** el de entrada de **connections** e ir borrando este último. Retorna **self** si hay que seguir retransmitiendo, caso contrario retorna None.


### RequestHandlerTask (objeto)

Se encarga de manejar los pedidos.


#### Inicialización

Crea el atributo **proxy** para el proxy que se le pasa al objeto y también **host** y **url** que los inicializa con None.


##### apply

Si aún no pudo leer la request line devuelve **self** y si ocurre algún error de parseo o si la url no empieza con "**http://"** devuelve **None**, lo mismo pasa con los encabezados: si falta un encabezado **Host** y la url del pedido tampoco tiene host va parseando lo que puede de **self.input** con los métodos de parseo del objeto **Queue**.
Finalmente retransmite la conexión si se se cumplen los criterios.


## proxy.py

Consta de un único objeto explicado a continuación:


### Proxy (objeto)


#### Inicialización

Crea una conexión, setea el reusado de puerto y escucha el puerto con máximo 5 clientes. Luego imprime el estado de escucha. Además sirve los hosts indicados en el mapa **host** ingresado al objeto y crea una lista vacía para las conexiones.


##### run

Maneja los datos de las conexiones hasta que todas se cierren.


##### polling set

Devuelve objeto polleable con los eventos que corresponden a cada una de las conexiones. Si alguna conexión tiene procesamiento pendiente (que no requiera entrada / salida) realiza ese procesamiento antes de poner la conexión en el conjunto.


##### connection with fd

Devuelve la conexión con el descriptor **fd**.


##### handle ready

Hace procesamiento en las conexiones que tienen trabajo por hacer, es decir, las que están leyendo y tienen datos en la cola de entrada.


##### handle events

Maneja eventos en las conexiones. **events** es una lista de pares **(fd, evento)**.


##### accept new

Acepta una nueva conexión.


##### remove finished

Elimina conexiones marcadas para terminar.


##### connect

Establece una nueva conexión saliente al **hostname** dado que puede tener la forma **host:puerto** y si se omite el **:puerto** se asume puerto **80**. Aquí está la única llamada a **connect** del sistema.


##### append

Agrega conexiones a la lista **connections**.


# Ejecución

$ cd .../lab4

$ sudo python main.py

Introducir contraseña de usuario root para habilitar el uso del puerto 80.


# Estilo de código

[PEP8](https://www.python.org/dev/peps/pep-0008/)


# Bibliografía
[Forward Proxy vs Reverse Proxy](http://www.jscape.com/blog/bid/87783/Forward-Proxy-vs-Reverse-Proxy/)
