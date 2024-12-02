import socket
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Condition, Thread

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

window_size = 1
ssthreshold = 64

#5319693 is the size of this file
with open('docker/file.mp3', 'rb') as f:
    data = f.read()
perPacket_list = []
perPacket_start = []
jitter_list = []
dest = ("0.0.0.0", 5001)
id_counter = 0
ack_dict = {} #key: ack id value: is received? true or false
id_message_dict = {} # key: seq id of start of message value: message bytes
id_list = []
messages = []
window = []
base = None
expected_ack = None
congest_control = False
dup_ack = 0
def send_packet (sender_socket:socket, id: int, dest=dest):
    global data
    message = int.to_bytes(id, length=4, byteorder='big', signed=True) + data[id : id + MESSAGE_SIZE]

def receive_response(socket_:socket, messages: list, dest = dest):
    global ssthreshold
    global congest_control
    global window_size
    try:
        response, addr = socket_.recvfrom(PACKET_SIZE)
    except socket.timeout:
        ssthreshold = window_size / 2
        window_size = 1
        congest_control = False
        return None
    res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
    return (res_id, res_message)
def receive_fin(socket_:socket, messages: list, dest=dest):
    while True:
        try:
            #ack_response, _ = socket.recvfrom(PACKET_SIZE)
            fin_response, _ = socket_.recvfrom(PACKET_SIZE)
            fin_id, fin_message = int.from_bytes(fin_response[:SEQ_ID_SIZE], byteorder='big'), fin_response[SEQ_ID_SIZE:]
            if 'fin' == fin_message.decode(): # due to culmulative acknowledgement we can assume the final ack has been sent from the receiver
                break
            else:
                for message in messages:    
                    socket_.sendto(message, dest)
                continue
        except socket.timeout:
            #print("Timeout occurred")
            for message in messages:    
                    socket_.sendto(message, dest)
    #ack_id, ack_message = int.from_bytes(ack_response[:SEQ_ID_SIZE], byteorder='big'), ack_response[SEQ_ID_SIZE:]
    return fin_id, fin_message

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    #create all packets from data
    while id_counter < len(data):
        message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
        id_list.append(id_counter)
        messages.append(message)
        id_counter += len(message) - SEQ_ID_SIZE
        ack_dict[id_counter] = False
    
    #initialize base and minimum expected ack id
    base = id_list[0]
    expected_ack = id_list[0] + len(messages[0])

    #send the amount of packets equal to window_size
    while not all(ack_dict.values()):
        base_index = id_list.index(base)
        index = base_index #index of packet to be sent

        while index < window_size:
            id = id_list[index]
            message = messages[index]
            sender_socket.sendto(message, dest)
            index += 1
        #get response from server
        #res_tuple will have response's id and message as a tuple (id, message) or None
        res_tuple = receive_response(sender_socket=sender_socket)
        if res_tuple != None:
            #timeout did not occurred
            if not congest_control:
                #slow start phase
                window_size = window_size * 2
                if window_size >= ssthreshold:
                    window_size = ssthreshold
                    congest_control = True
            else:
                #congestion control phase
                window_size += 1

            res_id = res_tuple[0]
            res_message = res_tuple[1]
            if expected_ack <= res_id and 'ack' == res_message.decode():
                #update ack_dict
                resId_index = list(ack_dict.keys()).index(res_id)
                expected_ack_index = list(ack_dict.keys()).index(expected_ack)
                i = expected_ack_index
                while i <= resId_index:
                    ack_dict[i] = True
                    i += 1
                #update base and expected_ack
                base = id_list[resId_index]
                expected_ack = id_list[resId_index] + len(messages[resId_index])
            elif expected_ack > res_id:
                # duplicate ack has occurred
                dup_ack += 1
                if dup_ack == 3:
                    dup_ack = 0
                    ssthreshold = window_size / 2
                    window_size = 1
                    congest_control = False 
        
        #else timeout occurred
        
    #closing message
    close_message = int.to_bytes(id_counter, 4, signed=True, byteorder='big') + b''
    sender_socket.sendto(close_message, dest)
    message_list = [close_message]
    fin_id, fin_message  = receive_fin(sender_socket, message_list)
    #print(f"fin packet id {fin_id} and the message {fin_message}")
    close_message = int.to_bytes(fin_id + 10, 4, byteorder='big') + b"==FINACK=="
    sender_socket.sendto(close_message, dest)