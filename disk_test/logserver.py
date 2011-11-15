__author__ = 'koder'
import socket
import struct
import pickle
import logging
import logging.handlers
import threading

sz_obj = struct.Struct('>L')
def socket_thread(sock):
    while True:
        data_len_s = sock.recv(sz_obj.size())

        if len(data_len_s) != sz_obj.size():
            return

        data_len = sz_obj.unpack(data_len_s)
        data_s = sock.recv(data_len)

        if len(data_s) != data_len:
            return

        obj = pickle.loads(data_s)
        logging.handle(obj)

def main(_argv):
    sock = socket.socket()
    sock.bind(('0.0.0.0',
                        logging.handlers.DEFAULT_TCP_LOGGING_PORT))
    sock.listen(5)
    sock.settimeout(1)

    while True:
        try:
            conn_sock, _addr = sock.accept()
        except socket.timeout:
            pass
        else:
            th = threading.Thread(None, socket_thread, None, (conn_sock,))
            th.daemon = True
            th.start()

if __name__ == '__main__':
    main()