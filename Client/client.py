import socket
import time
import sys
import os
from os.path import isfile

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Modules.response import Response
from Modules.response import BUF_SIZE

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
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n')
        if content.startswith(Response.RESPONSE_FAIL):
            return False
        return True
    
    def get_list(self):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n')
    
    def get_file(self, data):
        file_name = str.split(str(data), ' ', 2)[1]
        if isfile('./' + file_name):
            print('Esiste già un file con questo nome nella cartella, ma verrà sovrascritto')
        try:
            file = open('./' + file_name , 'wb')
            print('File creato nella cartella corrente')
            
            resp, server_address = self.sock.recvfrom(BUF_SIZE)
            receiving = False
            
            print('Ricezione disponibilità')   
            if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                receiving = True
                
            while receiving:
                print('Ricezione status') 
                resp, server_address = self.sock.recvfrom(BUF_SIZE)
                if resp.decode('utf-8') == Response.RESPONSE_DATA:
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    print('Invio OK dopo status')

                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    file.write(resp)
                    print('Ricezione dati')
                    
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    print('Invio OK dopo dati')
                elif resp.decode('utf-8') == Response.RESPONSE_DONE:
                    file.close()
                    print('Ricezione conclusa')
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    receiving = False
                else:
                    file.close()
                    receiving = False
        except Exception as info:
            print(info)
        finally:
            file.close()
            
    def put_file(self, file_name):
        file = open('./' + file_name, 'rb')
        self.sock.sendto(file.read(), (self.host, self.port))
        file.close()
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
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
                # resp, server_address = self.sock.recvfrom(BUF_SIZE)
                # print('Tempo ricezione risposta: ', (time.time()-t1)  )
                # content = resp.decode()
                
                # if content.startswith(Response.RESPONSE_FAIL):
                #     resp, server_address = self.sock.recvfrom(BUF_SIZE)
                #     content = resp.decode()  
                #     continue
                
                if data.startswith('exit') :
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    content = resp.decode()
                    print('\n', content, '\n')
                    return
                elif data.startswith('list'):
                    self.get_list()
                elif data.startswith('get'):
                    self.get_file(data)
                elif data.startswith('put'):  
                    self.put_file(file_name)
                    
                    
        except OSError as err:
            print(err)
        except KeyboardInterrupt:
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