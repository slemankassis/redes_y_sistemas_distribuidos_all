#ifndef __NODE_H
#define __NODE_H

#include <omnetpp.h>
#include "EtherFrame.h"

#define AMOUNT_OF_CLIENTS 6
typedef unsigned char IPAddress[4];
typedef unsigned char MACAddress[6];

class Node : public cSimpleModule
{
  private:
    cMessage *timer;
    unsigned char seen[AMOUNT_OF_CLIENTS];
    unsigned char IPMAC[256][6]; //Tabla para guardar dirceccion de cada ip.

  public:
    Node();
    virtual ~Node();

  protected:
    virtual void initialize();
    virtual void handleMessage(cMessage *msg);
    virtual void updateDisplay(void);

    /*
     * To implement!
     * Try to send `data` to a specified `ip`.
     * `data` is a buffer with IP_PAYLOAD_SIZE bytes.
     * If the MAC address for that IP is unknown, an ARP request should be sent.
     * Returns 0 on success and non-zero if it's necessary to retry later (because
     * ARP is figuring out the correct MAC address).
     */
    virtual int send_to_ip(IPAddress ip, void *data);

    /*
     * To implement!
     * Handle a packet.
     * If it's an ARP packet: Processes, if it's a regular data
     * packet then it forwards the data to the network layer using
     * receive_ip_packet.
     * `packet` is a buffer with ETHERFRAME_SIZE bytes.
        An ethernet packet has:
         - 6 bytes destination MAC
         - 6 bytes source MAC
         - 2 bytes type
         - 46-1500 bytes of data payload (in this application is always 1500)
        Total max size: 1514 bytes

     */
    virtual void receive_ethernet_packet(void *packet);

    /*
     * Delivers the `data` buffer with IP_PAYLOAD_SIZE bytes to the network layer
     * as it was delivered to send_to_ip in the node that originated the message.
     */
    virtual void receive_ip_packet(void *data);

    /*
     * Sends a packet through ethernet. `packet` is a buffer with ETHERFRAME_SIZE
     * bytes containing the packet to be sent.
        An ethernet packet has:
         - 6 bytes destination MAC
         - 6 bytes source MAC
         - 2 bytes type
         - 46-1500 bytes of data payload (in this application is always 1500)
        Total max size: 1514 bytes

     */
    virtual void send_ethernet_packet(void *packet);

    /*
     * Assigns this node's IP addresss into `ip`.
     */
    virtual void get_my_ip_address(IPAddress ip);

    /*
     * Assigns this node's MAC addresss into `mac`.
     */
    virtual void get_my_mac_address(MACAddress mac);
};

#endif
