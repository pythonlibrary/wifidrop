import socket
s=socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
s.settimeout(1)
#s.setblocking(False)
s.bind(('',54545))



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
        else:
            print(recv_str, address)
