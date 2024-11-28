from operator import countOf
import socket
import time
PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE
WINDOW_SIZE = 100

with open('docker/file.mp3', 'rb') as f:
    data = f.read()
perPacket_list = []
jitter_list = []
pending_acks = []
messages = []
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    dest = ("0.0.0.0", 5001)
    id_counter = 0
    min_id = None # the id of the packet that is the tail of the sliding window
    while id_counter < len(data):
        # fill window and make sure there is data left to fill window
        while WINDOW_SIZE - len(pending_acks) > 0 and id_counter < len(data):
            #create message
            message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
            print("created message with length: ", len(message))
            id_counter += len(message) - SEQ_ID_SIZE
            #if min_id == None: # initialize min_id
                #min_id = id_counter
            expected_id = id_counter
            pending_acks.append(expected_id)
            print(f"expect id: {expected_id} appended")
            messages.append(message)
        min_id = pending_acks[0] #tail end of window is always in theoth index
        print(f"min_id set as {min_id}")
        for message in messages:    
            sender_socket.sendto(message, dest)

            
        #if len(pending_acks) <= 100: #There is room within the sliding window
        while True:
            try:
                response, addr = sender_socket.recvfrom(1024)
                messages = []
                break
            except socket.timeout:
                for message in messages:    
                    sender_socket.sendto(message, dest)
        res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
        print(res_id, res_message)
        if min_id <= res_id:
            ack_index = pending_acks.index(res_id)
            pending_acks = pending_acks[ack_index:]
