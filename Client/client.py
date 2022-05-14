import socket
import time
from os.path import isfile

from ..Modules.response import Response

class UDPClient:
    ''' A simple UDP Client '''
    def __init__(self, host, port):
        self.host = host    # Host address
        self.port = port    # Host port
        self.sock = None    # Socket

    def configure_client(self):
        ''' Configure the client to use UDP protocol with IPv4 addressing '''
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        print('Socket creato')
        
    def connection_setup(self):
        msg = Response.RESPONSE_HELLO + ' Client connected'
        self.sock.sendto(msg.encode('utf-8'), (self.host, self.port))
        resp, server_address = self.sock.recvfrom(4096)
        content = resp.decode()
        print('\n', content, '\n')
        if content.startswith(Response.RESPONSE_FAIL):
            return False
        return True
    
    def get_file(self, data, resp):
        file_name = str.split(str(data), ' ', 2)[1]
        if isfile('./' + file_name):
            print('Esiste già un file con questo nome nella cartella, ma verrà sovrascritto')
        try:
            file = open('./' + file_name , 'wb')
            file.write(resp)
            print('File creato nella cartella corrente')
        except Exception as info:
            print(info)
        finally:
            file.close()
            
    def put_file(self, file_name):
        file = open('./' + file_name, 'rb')
        self.sock.sendto(file.read(), (self.host, self.port))
        file.close()
        resp, server_address = self.sock.recvfrom(4096)
        content = resp.decode()
        print('\n', content, '\n')

    def interact_with_server(self):
        ''' Send request to a UDP Server and receive reply from it. '''
        try:
            if not self.connection_setup():
               return
            while True:
                data=input('Inserire comando: ')
                data=data.lower()
                t1=time.time()
                
                if data.startswith('put'):
                    file_name = str.split(str(data), ' ', 2)[1]
                    if not isfile('./' + file_name):
                        file_data='File non trovato, reinserire comando completo.\r\n'
                        print(file_data)
                        continue
                
                self.sock.sendto(str(data).encode('utf-8'), (self.host, self.port))
                resp, server_address = self.sock.recvfrom(4096)
                print('Tempo ricezione risposta: ', (time.time()-t1)  )
                content = resp.decode()
                
                if content.startswith(Response.RESPONSE_FAIL):
                    print('\n', content, '\n')
                    continue
                
                if data.startswith('exit') :
                    print('\n', content, '\n')
                    return
                elif data.startswith('list'):
                    print('\n', content, '\n')
                elif data.startswith('get'):
                    self.get_file(data, resp)
                elif data.startswith('put'):  
                    self.put_file(file_name)
                    
                    
        except OSError as err:
            print(err)
        except KeyboardInterrupt():
            return
        finally:
            # close socket
            self.sock.close()

def main():
    ''' Create a UDP Client, send message to a UDP Server and receive reply. '''
    udp_client = UDPClient('127.0.0.1', 10002)
    udp_client.configure_client()
    udp_client.interact_with_server()

if __name__ == '__main__':
    main()