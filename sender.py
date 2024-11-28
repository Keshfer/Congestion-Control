import socket

with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sender_socket:

    sender_socket.bind(("localhost", 4000))

    message = int.to_bytes(0, length = 4, byteorder='big', signed = True) + int.to_bytes(20, length = 4, byteorder='big')
    print("len is ", len(message))
    message1 = int.to_bytes(4, length = 4, byteorder='big', signed = True) + int.to_bytes(20, length = 4, byteorder='big')
    dest = ("0.0.0.0", 5001)
    sender_socket.sendto(message, dest)
    response, addr = sender_socket.recvfrom(1024)
    decoded_id = int.from_bytes(response[:4], byteorder='big')
    res_message = response[4:]
    print(decoded_id, res_message)
    sender_socket.sendto(message1, dest)
    response, addr = sender_socket.recvfrom(1024)
    decoded_id = int.from_bytes(response[:4], byteorder='big')
    res_message = response[4:]
    print(decoded_id, res_message)


