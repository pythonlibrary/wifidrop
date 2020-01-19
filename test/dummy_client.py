import socket, threading 


def service_socket():
    s = socket.socket() 
    host = socket.gethostname()
    port = 12345               
    s.bind(('', port))
    # f = open('torecv.png','wb')
    s.listen(5)                 # Now wait for client connection.
    while True:
        c, addr = s.accept()    
        while True:
            size = c.recv(16) # Note that you limit your filename length to 255 bytes.
            if not size:
                break
            size = int(size.decode(), 2)
            filename = c.recv(size)
            filesize = c.recv(32)
            filesize = int(filesize.decode(), 2)
            file_to_write = open(filename, 'wb')
            chunksize = 4096
            while filesize > 0:
                if filesize < chunksize:
                    chunksize = filesize
                data = c.recv(chunksize)
                file_to_write.write(data)
                filesize -= len(data)

            file_to_write.close()
            print('File received successfully')
#        c.close()





s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(1)
#s.setblocking(False)
s.bind(('',54545))


server_thread = threading.Thread(target=service_socket)
server_thread.start()


while True:
    m = None
    address = None
    try:
        m, address = s.recvfrom(1024)
    except socket.timeout:
        print("timeout....")

    if m and address:
        recv_str = m.decode("utf-8")  # pythonlibrary 192.168.1.100 on
        print(recv_str)
        if recv_str == 'Init':
            s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            hostname = socket.gethostname()
            s.sendto('Exchange {} ServerOn'.format(hostname).encode('utf-8'), ('255.255.255.255', 54545))  # send broadcast message on 54545
        elif recv_str == 'SendConfirm':
            s.sendto('SendMe'.encode('utf-8'), ('255.255.255.255', 54545))  # send broadcast message on 54545
        else:
            print(recv_str, address)
