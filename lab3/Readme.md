# Introducción

En este laboratorio se implementa el protocolo ARP(Address Resolution Protocol), el cual se encuentra entre la capa de enlace de datos y la capa de red. Este protocolo se encarga de hacer la traducción de direcciones entre los protocolos de las capas antes mencionadas y por ello debe interactuar con ambas.
En este caso solo se implementara para traducir direcciones IP a direcciones MAC sobre una red Ethernet.

Para implementar este protocolo usamos la especificación oficial que se brinda en RFC826. Se utiliza el simulador de redes llamado **omnet**, que permitirá emular las capas físicas y de red utilizando el código provisto por la cátedra.

Para simplificar el proyecto, su supone que el ARP maneja un único enlace Ethernet y que se maneja sobre una red IP clase C. Esto significa que solo hay 255 direcciones posibles, por lo que se utiliza una tabla ARP de tamaño fijo. Cada índice de la tabla representa el último byte de cada una de las 255 direcciones IP.


# Tipos de Datos

Se implementan 2 estructuras que serán utilizadas en las 2 funciones explicadas luego en este informe. Primero enunciamos 2 tipos principales que se utilizaran en estas estructuras:

+ *IPAddress*: Es un arreglo de 4 bytes, utilizado para representar una dirección IP.
+ *MACAddress*: Es un arreglo de 6 bytes, utilizado para representar una dirección MAC.

A continuación describimos las estructuras definidas en la implementación. Notar que ambos necesitan ser de exactamente el tamaño definido, para ello usamos **\_\_attribute\_\_ ((packed))** en la declaración de las estructuras.


## Paquete Ethernet

Para estos se declara la estructura **ethfrm_t**. Se utilizan 2 constantes:

+ ETHERFRAME_SIZE: 1514.
+ IP_PAYLOAD_SIZE: 1500.

Contiene los siguiente campos en el orden dado:

* ***destination***: Dirección MAC del host de destino. Es de tipo MACAddress (6 bytes).
* ***source***: Dirección MAC del host de origen. Es de tipo MACAddress (6 bytes).
* ***type***: Tipo de paquete, puede ser arp o ip. Es de tipo unsigned int de 16 bits (2 bytes).
* ***data***: Datos que se quieren enviar. Es un arreglo de IP_PAYLOAD_SIZE bytes.

Total: ETHERFRAME_SIZE bytes


## Paquete ARP

Para estos se declara la estructura **arppck_t** siguiendo el RFC826. Contiene los siguientes campos en el orden dado:

+ ***hrd***: Tipo de hardware. Es de tipo unsigned int de 16 bits.
+ ***pro***: Tipo de protocolo. Es de tipo unsigned int de 16 bits.
+ ***hlen***: Tamaño de la dirección de hardware. Es de tipo unsigned int de 8 bits.
+ ***plen***: Tamaño de la dirección de protocolo. Es de tipo unsigned int de 8 bits.
+ ***opcode***: Si es paquete reply o request. Es de tipo unsigned int de 16 bits.
+ ***sourceMAC***: Dirección hardware de quien envía el paquete. Es de tipo MACAddress.
+ ***sourceIP***: Dirección de protocolo de quien envía el paquete. Es de tipo IPAddress.
+ ***destinationMAC***: Dirección hardware a quien esta dirigido el paquete. Es de tipo MACAddress.
+ ***destinationIP***: Dirección de protocolo a quien está dirigido el paquete. Es de tipo IPAddress.


## Constructor de la clase Node
Se inicializan los valores: **timer** a NULL y cada elemento del arreglo **seen** a 0.

Se inicializa la tabla ARP **IPMAC** con todas las direcciones en 0. Se supone que ningún host tendrá esta dirección MAC, así se puede utilizar para comprobar si ya se cargo la dirección MAC real o no.


# Constantes

Definimos las siguientes constantes según RFC826 que serán utilizadas en  las 2 funciones.

+ ***ETYPE_ARP*** = 0x0806, es EtherType ARP.
+ ***ETYPE_IP*** = 0x0800, es EtherType IPv4
+ ***HRD_ETHERNET*** = 1
+ ***OP_REQUEST*** = 1
+ ***OP_REPLY*** = 2

Ademas:

+ ***BROADCASTMAC:*** Es de tipo MACAddress con todos los bytes seteados en 255. Esta dirección MAC se utiliza para enviar un paquete a todos los host de la red.
+ ***ZEROMAC:*** Es de tipo MACAddress con todos los elementos seteados en 0. Se utiliza para comparar si la MAC que buscamos está o no en la tabla.


# Funciones

##  *send to ip*

##### PROTOTIPO
**int Node::send_to_ip(IPAddress ip, void *data)** (Función virtual de Node)

##### PARAMS
Toma la dirección IP y un puntero a los datos que se tienen que enviar hacia esa dirección.

##### RETURNS
Devuelve 0 si se enviaron correctamente los datos. Devuelve 1 si no se encontró la direccion MAC y se envió un paquete ARP para averiguarla.

##### IMPLEMENTACIÓN
Se encarga de enviar un paquete de red ethernet a un receptor.
Si no posee la dirección MAC, la averigua a través del protocolo ARP con la dirección IP.

Se crea un paquete de red (ethernet) **packet** y un paquete arp **arpPck**.

Se inicializan las variables **myMAC** y **myIP** obteniéndolas con **get_my_mac_address** y **get_my_ip_address** respectivamente. Notar que myMAC es de tipo MACAddress y myIP de tipo IPAddress.

Seguidamente se corrobora la información que tiene de la MAC, esto se hace con la función memcmp que toma la IPMAC[ip[3]] y la constante ZEROMAC que indica que no se tiene la direccion MAC.  
Si no se tiene la dirección MAC entonces se carga el paquete ARP y se lo agrega al payload del paquete Ethernet para enviarlo. Por lo contrario, si ya la tiene, setea el encabezado Ethernet con la MAC como destino y lo envia. Esto se explica con mas detalle a continuación.


Si no se tiene la MAC:

Se debe enviar un paquete ARP por toda la red para obtener la MAC.  
Para ello se hace broadcasting utilizando **BROADCASTMAC** como destino del paquete ethernet y **myMAC** como origen, el tipo se setea como **ETYPE_ARP**.

Luego se setea el paquete ARP de la siguiente manera:

+ A **hdr** se le asigna **HDR_ETHERNET**,
+ a **pro** se le asigna **ETYPE_IP**
+ a **hlen** se le asigna el tamaño de **MACAddress**
+ a **plen** se le asigna el tamaño de **IPAddress**
+ a **opcode** se le asigna **OP_REQUEST**
+ a **destinacionMAC** se le asigna **ZEROMAC**,
+ a **sourceMAC** se le asigna **myMAC**,
+ a **destinationIP** se le asigna **ip**,
+ y a **sourceIP** se le asigna **myIP**

Luego se carga este paquete ARP en el payload del paquete Ethernet y se envía.

En el caso de asignaciones de 2 bytes, se debe usar la función **htons** (host to network short) de la librería **arpa/inet.h** ya que la red utiliza Big Endian. Para el caso de direcciones, se utiliza **memcpy** ya que estan definidas como arreglos.

Si ya se tiene la MAC:

En el paquete Ethernet se carga esta como direccion de destino, **myMAC** como dirección de origen y el tipo como **ETYPE_IP**. Finalemente se carga en el payload los datos recibidos y se envía el paquete.


En ambos casos se envia el paquete Ethernet con **send_ethernet_packet**.


## *receive ethernet packet*

##### PROTOTIPO
**void Node::receive_ethernet_packet(void *packet)** (Función virtual de Node)

##### PARAMS
Toma el puntero a un paquete de red.

##### RETURNS
No tiene retorno.

##### IMPLEMENTACIÓN
La implementación de esta función intenta seguir de la mejor fomra el psudocódigo provisto en el RFC826.

Se crea un paquete de red (ethernet) **ethPck**, el cual se utiliza para manejar los datos de entrada, y un paquete arp **arpPck**.

Al igual que **send_to_ip** se inicializan las variables **myMAC** y **myIP** obteniéndolas con **get_my_mac_address** y **get_my_ip_address** respectivamente.

Luego se tienen 2 casos: que el tipo del paquete de red sea ARP (**ETYPE_ARP**) o IP (**ETYPE_IP**).

En el primer caso a **arpPck** se le asigna **data** el cual sería el paquete ARP que se envio.

Si ya existe la direccion MAC asociada a la IP de quien envió el paquete, se actualiza en la tabla.

Luego si el paquete esta dirigifo a **myIP**, asocio el IP y la MAC de quien envió el pauqete agregandolo en la tabla **IPMAC** si no se actualizo.

En el caso de que el opcode sea **OP_REPLY** no se prosigue ya que se actualizo la tabla y se descarta el paquete. En el caso que sea **OP_REQUEST** se debe proseguir de la siguiente manera:

Primero **ethPck**:

A **destination** le asigna **source**, a **source** le asigna **myMAC** y se setea **type** a **ETYPE_ARP** utilizando **htons**.

Ahora **arpPck**:

Se setea **opcode** a **OP_REPLY** utilizando **htons**, luego se sobreescriben los destination a los source tanto IP como MAC y a los source se les asigna myMAC y myIP respectivamente.

Luego copia a **data** de ethPck el contenido de arpPck y envía la respuesta con **send_ethernet_packet(&ethPck)**.

En el segundo caso, donde el tipo de paquete es IP se corrobora que la direccion MAC de destino sea **myMAC** y se llama a la función **receive_ip_packet** con parametro **data**.  
Esto debimos realizarlo porque el simulador envía los paquetes a todos los host.


#Compilación

Tenemos un script para poder correr omnet (64 bits únicamente) ya que al estar precompilada la versión, solo utiliza la carpeta temporal del sistema operativo.

+ ***$ cd /.../lab3/***
+ ***$ . setenv***
+ ***$ make***
+ ***$ ./arplab***


# Bibliografía

* ***RFC826*** http://www.faqs.org/rfcs/rfc826.html/
* ***Funciones Virtuales*** https://es.wikipedia.org/wiki/Funci%C3%B3n_virtual/
* ***C Standard Library*** http://www.tutorialspoint.com/c_standard_library/
* ***memcmp y memcpy*** http://www.cplusplus.com/
* ***EtherType*** https://en.wikipedia.org/wiki/EtherType/
* ***Endianness (Big Endian y Little Endian)*** http://www.codeproject.com/Articles/4804/Basic-concepts-on-Endianness/
* ***MAC*** https://es.wikipedia.org/wiki/Direcci%C3%B3n_MAC/
