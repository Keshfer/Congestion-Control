from operator import countOf
import socket
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Condition, Thread

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
WINDOW_SIZE = 100

with open('docker/file.mp3', 'rb') as f:
    data = f.read()
perPacket_list = []
jitter_list = []
pending_acks = [] #think of this as the window
messages = []
dest = ("0.0.0.0", 5001)
id_counter = 0
min_id = None # the id of the packet that is the tail of the sliding window
def send_packets(socket:socket, data: bytes, condition:Condition):
    id_counter = 0
    global pending_acks
    with condition:
        while id_counter < len(data):
            # fill window and make sure there is data left to fill window
            while WINDOW_SIZE - len(pending_acks) > 0 and id_counter < len(data):
                message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
                print(f"created message with length: {len(message)} with id {id_counter}")
                id_counter += len(message) - SEQ_ID_SIZE
                expected_id = id_counter
                pending_acks.append(expected_id)
                print(f"expect id: {expected_id} appended")
                #messages.append(message)
                sender_socket.sendto(message, dest)
            min_id = pending_acks[0] #tail end of window is always in the 0th index
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    
    
    while id_counter < len(data):
        print(len(data))
        # fill window and make sure there is data left to fill window
        while len(pending_acks) <= 100 and id_counter < len(data):
            #create message
            message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
            print(f"created message with length: {len(message)} with id {id_counter}")
            id_counter += len(message) - SEQ_ID_SIZE
            #if min_id == None: # initialize min_id
                #min_id = id_counter
            expected_id = id_counter
            pending_acks.append(expected_id)
            print(f"expect id: {expected_id} appended")
            messages.append(message)
            sender_socket.sendto(message, dest)
        min_id = pending_acks[0] #tail end of window is always in the 0th index
        print(f"min_id set as {min_id}")
        # for message in messages:    
        #     sender_socket.sendto(message, dest)

            
        #if len(pending_acks) <= 100: #There is room within the sliding window
        while True:
            try:
                response, addr = sender_socket.recvfrom(PACKET_SIZE)
                
                break
            except socket.timeout:
                print("timeout occurred")
                for message in messages:    
                    sender_socket.sendto(message, dest)
        res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
        print(f"received {res_id} with message {res_message}")
        if min_id <= res_id and 'ack' == res_message.decode():
            print("enter")
            ack_index = pending_acks.index(res_id) + 1
            #pending_acks and messages have the same list length and matching order of ids and messages. So acK_index can be used for both
            pending_acks = pending_acks[ack_index:]
            messages = messages[ack_index:]
            
        else:
            print("retransmitting")
            for message in messages:    
                    sender_socket.sendto(message, dest)
        print(pending_acks)
    #case when there is no new message to be created but sill have pending messages in the list
    while len(messages) > 0:
        print("retransmitting remaining")
        min_id = pending_acks[0]
        for message in messages:
            sender_socket.sendto(message, dest)
        while True:
            try:
                response, addr = sender_socket.recvfrom(PACKET_SIZE)
                
                break
            except socket.timeout:
                print("timeout occurred")
                for message in messages:    
                    sender_socket.sendto(message, dest)  
        res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
        print(f"received {res_id} with message {res_message}")
        if min_id <= res_id and 'ack' == res_message.decode():
            print("enter")
            ack_index = pending_acks.index(res_id) + 1
            #pending_acks and messages have the same list length and matching order of ids and messages. So acK_index can be used for both
            pending_acks = pending_acks[ack_index:]
            messages = messages[ack_index:]  
    
    close_message = int.to_bytes(-1, 4, signed=True, byteorder='big')
    sender_socket.sendto(close_message, dest)
