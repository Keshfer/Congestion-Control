import socket
import time
PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

#5319693 is the size of this file
with open('docker/file.mp3', 'rb') as f:
    data = f.read()
perPacket_list = []
jitter_list = []
with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:
    throughput_start = time.time()
    sender_socket.settimeout(1)
    sender_socket.bind(("localhost", 4000))
    dest = ("0.0.0.0", 5001)
    id_counter = 0
    while id_counter < len(data):
        #print("size of data: ",len(data))
        #create message
        message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
        #print("created message with length: ", len(message))
        #update id_counter to point at next sequence id and data's index
        #id_counter += MESSAGE_SIZE
        id_counter += len(message) - SEQ_ID_SIZE
        expected_id = id_counter
        #print("expect id: ", expected_id)

        sender_socket.sendto(message, dest)
        per_start = time.time()
        while True:
            try:
                response, addr = sender_socket.recvfrom(1024)
            except socket.timeout:
                sender_socket.sendto(message, dest)
                continue

            res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
            #print(res_id, res_message)
            if(res_id == expected_id and 'ack' == res_message.decode()):
                #expected ack received so no need to resend
                per_rtt = time.time() - per_start
                if len(perPacket_list) <= 0: #can't calculate jitter yet
                    perPacket_list.append(per_rtt)
                else: # use the last appended item to calculate jitter
                    jitter = abs(perPacket_list[-1] - per_rtt)
                    jitter_list.append(jitter)
                    perPacket_list.append(per_rtt)
                break
    throughput_rtt = time.time() - throughput_start
    throughput = len(data) / throughput_rtt
    avg_perPacket_delay = sum(perPacket_list) / len(perPacket_list)
    avg_jitter = sum(jitter_list) / len(jitter_list)
    metric = (0.2 * (throughput / 2000)) + (0.1 / avg_jitter) + (0.8 / avg_perPacket_delay)
    print("Throughput: {:.7f},".format(throughput))
    print("Average per packet delay: {:.7f},".format(avg_perPacket_delay))
    print("Average jitter: {:.7f},".format(avg_jitter))
    print("Metric: {:.7f},".format(metric))
    finished_message = int.to_bytes(id_counter, 4, signed=True, byteorder='big') + b''
    sender_socket.sendto(finished_message, dest)
    while True:
        try:
            #ack_response, _ = sender_socket.recvfrom(PACKET_SIZE)
            fin_response, _ = sender_socket.recvfrom(PACKET_SIZE)
            fin_id, fin_message = int.from_bytes(fin_response[:SEQ_ID_SIZE], byteorder='big'), fin_response[SEQ_ID_SIZE:]
            print(fin_id, fin_message)
            if(fin_id == expected_id+ 3 and'fin' == fin_message.decode()):
                #print('all collected') #due to cumulative acknowledgement
                break
            else:
                sender_socket.sendto(finished_message, dest)
                continue
        except socket.timeout:
            print('Timeout occurred')
            sender_socket.sendto(finished_message, dest)
    #ack_id, ack_message = int.from_bytes(ack_response[:SEQ_ID_SIZE], byteorder='big'), ack_response[SEQ_ID_SIZE:]
    #fin_id, fin_message = int.from_bytes(fin_response[:SEQ_ID_SIZE], byteorder='big'), fin_response[SEQ_ID_SIZE:]
    #print(ack_id, ack_message)
    
    close_message = int.to_bytes(fin_id + 10, 4, byteorder='big') + b"==FINACK=="
    sender_socket.sendto(close_message, dest)
    

    

