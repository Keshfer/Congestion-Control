import socket
import time
import operator

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
id_counter = 0
dest = ("0.0.0.0", 5001)
id_list = []
messages = []
ack_dict = {} #key: ack id value: is received? true or false
dup_id = None
dup_ack = 0
congest_control = False
is_timeout = False
estimated_rtt = 0.1  # Initial RTT estimate
dev_rtt = 0.25
alpha = 0.125
beta = 0.25
sample_rtt = None  # Placeholder for RTT measurement
def receive_response(socket_:socket):
    global ssthreshold
    global congest_control
    global window_size
    global is_timeout
    try:
        response, addr = socket_.recvfrom(PACKET_SIZE)
    except socket.timeout:
        #print("timeout occurred")
        socket_.settimeout(socket_.timeout * 2)
        ssthreshold = max(1, window_size / 2)
        window_size = 1
        congest_control = False
        is_timeout = True
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
def retransmit_packets(socket_:socket, curr_window:list, next_index: int):
    global ack_dict
    global window_size
    global id_list
    global messages
    retrans_index = 0
    ack_vals = list(ack_dict.values())
    while len(curr_window) < window_size and retrans_index < next_index:
        ack_bool = ack_vals[retrans_index]
        if not ack_bool:
            retransmit_id = id_list[retrans_index]
            retransmit_message = messages[retrans_index]
            socket_.sendto(retransmit_message, dest)
            curr_window.append(retransmit_id)
            #print(f"Resent message with id {retransmit_id}")
        retrans_index += 1

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:
    throughput_start = time.time()
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    #create all packets from data
    while id_counter < len(data):
        message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
        id_list.append(id_counter)
        messages.append(message)
        ack_dict[id_counter] = False
        id_counter += len(message) - SEQ_ID_SIZE
    #print("finished creating all packets")
    #initialize next_id and minimum expected ack id
    next_index = 0
    expected_ack = len(messages[0]) - SEQ_ID_SIZE
    while not all(ack_dict.values()):
        #print(f"window size is {window_size}")
        #print(f"ssthreshold is {ssthreshold}")
        curr_window = []
        if next_index < len(id_list):
            next_id = id_list[next_index]
        else:
            next_index = len(id_list) - 1
            next_id = id_list[next_index]

        if is_timeout:
            is_timeout = False
            retransmit_packets(socket_=sender_socket, curr_window=curr_window, next_index=next_index)
        if next_id - expected_ack < window_size: # if space between next_id and expect_ack is greater than window size, don't send packets until next ack
            if expected_ack < next_id:
                #retransmit packets
                #retrans_index = id_list.index(base_retrains_id)
                # retrans_index = 0
                # ack_vals = list(ack_dict.values())
                # while len(curr_window) < window_size and retrans_index < next_index:
                #     ack_bool = ack_vals[retrans_index]
                #     if not ack_bool:
                #         retransmit_id = id_list[retrans_index]
                #         retransmit_message = messages[retrans_index]
                #         sender_socket.sendto(retransmit_message, dest)
                #         curr_window.append(retransmit_id)
                #         #print(f"Resent message with id {retransmit_id}")
                #     retrans_index += 1
                retransmit_packets(socket_=sender_socket, curr_window=curr_window, next_index=next_index)

            #send packets up to window_size
            while len(curr_window) < window_size and next_index < len(id_list):
                #print(f"next_index is {next_index}")
                id = id_list[next_index]
                message = messages[next_index]
                sender_socket.sendto(message, dest)
                curr_window.append(id)
                perPacket_start.append(time.time())
                next_index += 1
            send_start = time.time()
        #print(curr_window)
        #get response from server
        #res_tuple will have response's id and message as a tuple (id, message) or None
        res_tuple = receive_response(socket_=sender_socket)
        #print(f"got response {res_tuple}")

        if res_tuple != None:
            #timeout did not occurred
            finished_ts = time.time()
            #adjust timeout timer
            sample_rtt = time.time() - send_start
            estimated_rtt = (1 - alpha) * estimated_rtt + alpha * sample_rtt
            dev_rtt = (1 - beta) * dev_rtt + beta * abs(sample_rtt - estimated_rtt)
            time_interval = estimated_rtt + 4 * dev_rtt
            sender_socket.settimeout(time_interval)

            res_id = res_tuple[0]
            res_message = res_tuple[1]
            #print(f"expected ack {expected_ack} vs res id {res_id}")

            if expected_ack <= res_id and 'ack' == res_message.decode():
                if not congest_control:
                    #slow start phase
                    window_size = window_size * 2
                    if window_size >= ssthreshold:
                        window_size = ssthreshold
                        congest_control = True
                else:
                    #congestion control phase
                    if res_id < len(data):
                        #num_acks = id_list.index(res_id) - expected_ack_index 
                        num_acks = 0
                        for id in curr_window:
                            if id < res_id:
                                num_acks += 1
                        if num_acks > 0:
                            window_size += ((1/window_size) * num_acks)
                        #print(f"num acks are {num_acks}")
                    
            if expected_ack <= res_id and 'ack' == res_message.decode():
                if res_id >= len(data):
                    throughput_rtt = time.time() - throughput_start
                    res_index = len(id_list)
                else:
                    res_index = id_list.index(res_id)
                    expected_ack = res_id + (len(messages[res_index]) - SEQ_ID_SIZE) 
                #calculate per packet and jitter time
                perPacket_finished = perPacket_start[:res_index]
                perPacket_start = perPacket_start[res_index:]
                for ts in perPacket_finished:
                    per_rtt = finished_ts - ts
                    if len(perPacket_list) <= 0: #can't calculate jitter yet
                        perPacket_list.append(per_rtt)
                    else: # perPacket_list has at least 1 item so jitter can be calculated
                        jitter = abs(perPacket_list[-1] - per_rtt)
                        jitter_list.append(jitter)
                        perPacket_list.append(per_rtt)
                
                for i in range(res_index):
                    ack_id = id_list[i]
                    ack_dict[ack_id] = True
                tempy = operator.countOf(ack_dict.values(), True)
                #print(f"{tempy} trues out of {len(id_list)}")
            else: # dup error
                if dup_id == None or dup_id == res_id:
                    dup_ack += 1
                    dup_id = res_id
                else:
                    dup_ack = 1
                    dup_id = res_id
                if dup_ack == 3:
                    #print("3 dup acks occurred")
                    #time.sleep(1)
                    dup_ack = 0
                    ssthreshold = max(1,window_size / 2)
                    window_size = 1
                    congest_control = False 
                    dup3_index = id_list.index(res_id)
                    dup3_message = messages[dup3_index]
                    sender_socket.sendto(dup3_message, dest)
    throughput = len(data) / throughput_rtt
    avg_perPacket_delay = sum(perPacket_list) / len(perPacket_list)
    avg_jitter = sum(jitter_list) / len(jitter_list)
    metric = (0.2 * (throughput / 2000)) + (0.1 / avg_jitter) + (0.8 / avg_perPacket_delay)
    print("Throughput: {:.7f},".format(throughput))
    print("Average per packet delay: {:.7f},".format(avg_perPacket_delay))
    print("Average jitter: {:.7f},".format(avg_jitter))
    print("Metric: {:.7f},".format(metric))
    print("closing message")
    close_message = int.to_bytes(id_counter, 4, signed=True, byteorder='big') + b''
    sender_socket.sendto(close_message, dest)
    message_list = [close_message]
    fin_id, fin_message  = receive_fin(sender_socket, message_list)
    #print(f"fin packet id {fin_id} and the message {fin_message}")
    close_message = int.to_bytes(fin_id + 10, 4, byteorder='big') + b"==FINACK=="
    sender_socket.sendto(close_message, dest)