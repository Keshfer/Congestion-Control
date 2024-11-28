import socket

PACKET_SIZE = 1024
SEQ_ID_SIZE = 4
MESSAGE_SIZE = PACKET_SIZE - SEQ_ID_SIZE

with open('docker/file.mp3', 'rb') as f:
    data = f.read()

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:

    sender_socket.bind(("localhost", 4000))
    dest = ("0.0.0.0", 5001)
    id_counter = 0
    while id_counter < len(data):
        print(len(data))
        #create message
        message = int.to_bytes(id_counter, length = 4, byteorder = 'big', signed = True) + data[id_counter : id_counter + MESSAGE_SIZE]
        print("created message with length: ", len(message))
        #update id_counter to point at next sequence id and data's index
        id_counter += MESSAGE_SIZE
        expected_id = id_counter
        print("expect id: ", expected_id)

        sender_socket.sendto(message, dest)
        while True:
            response, addr = sender_socket.recvfrom(1024)
            res_id, res_message = int.from_bytes(response[:SEQ_ID_SIZE], byteorder='big'), response[SEQ_ID_SIZE:]
            print(res_id, res_message)
            if(res_id == expected_id and 'ack' == res_message.decode()):
                #expected ack received so no need to resend
                break
    close_message = int.to_bytes(-1, 4, signed=True, byteorder='big')
    sender_socket.sendto(close_message, dest)

