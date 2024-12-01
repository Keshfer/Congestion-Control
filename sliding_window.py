import socket
import time
from concurrent.futures import ThreadPoolExecutor
from threading import Lock, Condition, Thread

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
WINDOW_SIZE = 100

#5319693 is the size of this file
with open('docker/file.mp3', 'rb') as f:
    data = f.read()
perPacket_list = []
perPacket_start = []
jitter_list = []
pending_acks = [] #think of this as the window
messages = []
dest = ("0.0.0.0", 5001)
id_counter = 0
min_id = None # the expected response id of the packet that is the tail of the sliding window
#IMPORTANT: For perPacket_start, pending_acks, and messages, their ith index corresponds to the ith pending packet . 
#EX: the 0th pending packet(ie the base) has perPacket_start[0], pending_acks[0], messages[0]
def receive_response(socket_:socket, messages: list, dest = dest):
    while True:
        try:
            response, addr = socket_.recvfrom(PACKET_SIZE)
            break
        except socket.timeout:
            #print("Timeout occurred")
            for message in messages:    
                    socket_.sendto(message, dest)
    res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
    return res_id, res_message

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
    throughput_start = time.time()
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    
    
    while id_counter < len(data):
        #print(len(data))
        #print(f"size of pending acks list {len(pending_acks)}")
        # fill window and make sure there is data left to fill window
        while len(pending_acks) < 100 and id_counter < len(data):
            #create message
            message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
            #print(f"created message with length: {len(message)} with id {id_counter}")
            id_counter += len(message) - SEQ_ID_SIZE
            #if min_id == None: # initialize min_id
                #min_id = id_counter
            expected_id = id_counter
            pending_acks.append(expected_id)
            #print(f"expect id: {expected_id} appended")
            messages.append(message)
            sender_socket.sendto(message, dest)
            perPacket_start.append(time.time())
        min_id = pending_acks[0] #tail end of window is always in the 0th index
        #print(f"min_id set as {min_id}")

        # while True:
        #     try:
        #         response, addr = sender_socket.recvfrom(PACKET_SIZE)
                
        #         break
        #     except socket.timeout:
        #         print("timeout occurred")
        #         for message in messages:    
        #             sender_socket.sendto(message, dest)
        # res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
        res_id, res_message = receive_response(socket_=sender_socket, messages=messages)
        #print(f"received {res_id} with message {res_message}")
        if min_id <= res_id and 'ack' == res_message.decode():
            #print("enter")
            finished_ts = time.time()
            #+1 to exclude the red_id from the list
            ack_index = pending_acks.index(res_id) + 1
            #pending_acks and messages have the same list length and matching order of ids and messages. So acK_index can be used for both
            pending_acks = pending_acks[ack_index:]
            messages = messages[ack_index:]
            finished_perPackets = perPacket_start[:ack_index]
            perPacket_start = perPacket_start[ack_index:]
            for ts in finished_perPackets:
                per_rtt = finished_ts - ts
                if len(perPacket_list) <= 0: #can't calculate jitter yet
                    perPacket_list.append(per_rtt)
                else: # perPacket_list has at least 1 item so jitter can be calculated
                    jitter = abs(perPacket_list[-1] - per_rtt)
                    jitter_list.append(jitter)
                    perPacket_list.append(per_rtt)

            
            
        else:
            #print("retransmitting")
            for message in messages:    
                    sender_socket.sendto(message, dest)
        
    #case when there is no new message to be created but sill have pending messages in the list
    while len(messages) > 0:
        #print("retransmitting remaining")
        min_id = pending_acks[0]
        for message in messages:
            sender_socket.sendto(message, dest)
        # while True:
        #     try:
        #         response, addr = sender_socket.recvfrom(PACKET_SIZE)
                
        #         break
        #     except socket.timeout:
        #         print("timeout occurred")
        #         for message in messages:    
        #             sender_socket.sendto(message, dest)  
        # res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
        res_id, res_message = receive_response(socket_=sender_socket, messages=messages)
        #print(f"received {res_id} with message {res_message}")
        if min_id <= res_id and 'ack' == res_message.decode():
            #print("enter")
            finished_ts = time.time()
            ack_index = pending_acks.index(res_id) + 1
            #pending_acks and messages have the same list length and matching order of ids and messages. So acK_index can be used for both
            pending_acks = pending_acks[ack_index:]
            messages = messages[ack_index:]  
            finished_perPackets = perPacket_start[:ack_index]
            perPacket_start = perPacket_start[ack_index:]
            for ts in finished_perPackets:
                per_rtt = finished_ts - ts
                if len(perPacket_list) <= 0: #can't calculate jitter yet
                    perPacket_list.append(per_rtt)
                else: # perPacket_list has at least 1 item so jitter can be calculated
                    jitter = abs(perPacket_list[-1] - per_rtt)
                    jitter_list.append(jitter)
                    perPacket_list.append(per_rtt)

            #print(f"amount of messages left:{len(messages)}")

    throughput_rtt = time.time() - throughput_start
    throughput = len(data) / throughput_rtt
    avg_perPacket_delay = sum(perPacket_list) / len(perPacket_list)
    avg_jitter = sum(jitter_list) / len(jitter_list)
    metric = (0.2 * (throughput / 2000)) + (0.1 / avg_jitter) + (0.8 / avg_perPacket_delay)
    print("Throughput: {:.7f},".format(throughput))
    print("Average per packet delay: {:.7f},".format(avg_perPacket_delay))
    print("Average jitter: {:.7f},".format(avg_jitter))
    print("Metric: {:.7f},".format(metric))
    #print('Sending closing messages')
    close_message = int.to_bytes(id_counter, 4, signed=True, byteorder='big') + b''
    sender_socket.sendto(close_message, dest)
    message_list = [close_message]
    fin_id, fin_message  = receive_fin(sender_socket, message_list)
    #print(f"fin packet id {fin_id} and the message {fin_message}")
    close_message = int.to_bytes(fin_id + 10, 4, byteorder='big') + b"==FINACK=="
    sender_socket.sendto(close_message, dest)