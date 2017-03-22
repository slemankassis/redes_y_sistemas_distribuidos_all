#include "node.h"
#include <arpa/inet.h>

#define ETYPE_ARP 0x0806 //EtherType ARP
#define ETYPE_IP 0x0800 //EtherType IPv4
#define HRD_ETHERNET 1
#define OP_REQUEST 1
#define OP_REPLY 2

const MACAddress BROADCASTMAC = {255, 255, 255, 255, 255, 255};
const MACAddress ZEROMAC = {0, 0, 0, 0, 0, 0};


struct ethfrm_t {
    MACAddress destination;
    MACAddress source;
    uint16_t type;
    unsigned char data[IP_PAYLOAD_SIZE];
} __attribute__ ((packed));

struct arppck_t {
    uint16_t hrd;
    uint16_t pro;
    uint8_t hlen;
    uint8_t plen;
    uint16_t opcode;
    MACAddress sourceMAC;
    IPAddress sourceIP;
    MACAddress destinationMAC;
    IPAddress destinationIP;
} __attribute__ ((packed));


/*
 * Implementar!
 * Intentar enviar `data` al `ip` especificado.
 * `data` es un buffer con IP_PAYLOAD_SIZE bytes.
 * Si la dirección MAC de ese IP es desconocida, debería enviarse un pedido ARP.
 * Devuelve 0 en caso de éxito y distinto de 0 si es necesario reintentar luego
 * (porque se está bucando la dirección MAC usando ARP)
 */
int Node::send_to_ip(IPAddress ip, void *data) {
    ethfrm_t packet;
    arppck_t arpPck;
    MACAddress myMAC;
    IPAddress myIP;

    get_my_mac_address(myMAC);
    get_my_ip_address(myIP);

    // Si la direccion MAC no se encuentra, el paquete IP se descarta.
    if (!memcmp(IPMAC[ip[3]], ZEROMAC, sizeof(MACAddress))) {  // La dirección MAC no esta cargada.
        // Se crea encabezado ethernet con tipo ARP y con dirección broadcast.
        memcpy(packet.destination, BROADCASTMAC, sizeof(MACAddress));
        memcpy(packet.source, myMAC, sizeof(MACAddress));
        packet.type = htons(ETYPE_ARP);

        // Se crea paquete ARP para averiguar la dirección.
        arpPck.hrd = htons(HRD_ETHERNET);
        arpPck.pro = htons(ETYPE_IP);
        arpPck.hlen = sizeof(MACAddress);
        arpPck.plen = sizeof(IPAddress);
        arpPck.opcode = htons(OP_REQUEST);
        memcpy(arpPck.destinationMAC, ZEROMAC, sizeof(MACAddress));
        memcpy(arpPck.sourceMAC, myMAC, sizeof(MACAddress));
        memcpy(arpPck.destinationIP, ip, sizeof(IPAddress));
        memcpy(arpPck.sourceIP, myIP, sizeof(IPAddress));

        // Agregamos el paquete ARP al payload y lo enviamos.
        memcpy(packet.data, &arpPck, sizeof(arppck_t));
        send_ethernet_packet(&packet);
        return 1;
    } else { // La dirección MAC se encuentra en la tabla.
        // Se crea el paquete ethernet y se envia a la direccion encontrada.
        memcpy(packet.destination, IPMAC[ip[3]], sizeof(MACAddress));
        memcpy(packet.source, myMAC, sizeof(MACAddress));
        packet.type = htons(ETYPE_IP);
        // Se carga el paquete ip al payload exactamenete como llego.
        memcpy(packet.data, data, IP_PAYLOAD_SIZE);

        send_ethernet_packet(&packet);
        return 0;
    }
}

/*
 * Implementar!
 * Manejar el recibo de un paquete.
 * Si es un paquete ARP: procesarlo.
 * Si es un paquete con datos: pasarlo a la capa de red con receive_ip_packet.
 * `packet` es un buffer de ETHERFRAME_SIZE bytes.
    Un paquete Ethernet tiene:
     - 6 bytes MAC destino
     - 6 bytes MAC origen
     - 2 bytes tipo
     - 46-1500 bytes de payload (en esta aplicación siempre son 1500)
    Tamaño total máximo: 1514 bytes
 */
 void Node::receive_ethernet_packet(void *packet) {
     bool merge = false;
     arppck_t arpPck;
     MACAddress myMAC;
     IPAddress myIP;
     ethfrm_t ethPck = *(ethfrm_t *) packet;

     get_my_mac_address(myMAC);
     get_my_ip_address(myIP);

     if (ntohs(ethPck.type) == ETYPE_ARP) {  // Si es un paquete del tipo ARP se analiza.
         arpPck = *(arppck_t *) ethPck.data;
         // Siguiendo el RFC, se actualiza la direccion en la tabla si existe.
         if (memcmp(IPMAC[arpPck.sourceIP[3]], ZEROMAC, sizeof(MACAddress))) {
             memcpy(IPMAC[arpPck.sourceIP[3]], arpPck.sourceMAC, sizeof(MACAddress));
             merge = true;
         }
         if (arpPck.destinationIP[3] == myIP[3]) {  // El destino concuerda con mi IP.
             // Si no se actualizo la dirección, significa que no esta disponible y se agrega. (Asumiendo comunicación bidireccional)
             if (merge == false) {
                 memcpy(IPMAC[arpPck.sourceIP[3]], arpPck.sourceMAC, sizeof(MACAddress));
             }

             // Si el opcode es REQUEST, se modifica el paquete ARP, cambiando el tipo a REPLY.
             // Luego se reenvía al mismo destino por el que llego. En el caso de ser REPLY, en
             // este punto ya se actualizo la tabla, entonces se descarta el paquete.
             if (ntohs(arpPck.opcode) == OP_REQUEST) {
                 memcpy(ethPck.destination, ethPck.source, sizeof(MACAddress));
                 memcpy(ethPck.source, myMAC, sizeof(MACAddress));
                 ethPck.type = htons(ETYPE_ARP);

                 arpPck.opcode = htons(OP_REPLY);
                 memcpy(arpPck.destinationIP, arpPck.sourceIP, sizeof(IPAddress));
                 memcpy(arpPck.destinationMAC, arpPck.sourceMAC, sizeof(MACAddress));
                 memcpy(arpPck.sourceMAC, myMAC, sizeof(MACAddress));
                 memcpy(arpPck.sourceIP, myIP, sizeof(IPAddress));

                 memcpy(ethPck.data, &arpPck, sizeof(arppck_t));
                 send_ethernet_packet(&ethPck);
             }
         }
     } else if (ntohs(ethPck.type) == ETYPE_IP) { // Si es un paquete del tipo IP, se envía a la capa de red.
         if (!memcmp(ethPck.destination, myMAC, sizeof(MACAddress))) {
             receive_ip_packet(ethPck.data);
         }
     }
 }

/*
 * Constructor de la clase. Poner inicialización aquí.
 */
Node::Node()
{
    timer = NULL;
    for (unsigned int i = 0; i != AMOUNT_OF_CLIENTS; ++i) {
        seen[i] = 0;
    }

    // Se inicializan las entradas de la tabla con la direccion ZEROMAC. Esta dirección, indica que
    // no se encuentra la MAC real. Asumimos que ningun host tendra esta dirección para el lab.
    for (unsigned int i = 0; i < 256; i++) {
        memcpy(IPMAC[i], ZEROMAC, sizeof(MACAddress));
    }
}
