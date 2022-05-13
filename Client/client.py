import socket
import time

class UDPClient:
    ''' A simple UDP Client '''

    def __init__(self, host, port):
        self.host = host    # Host address
        self.port = port    # Host port
        self.sock = None    # Socket

    def printwt(self, msg):
        ''' Print message with current date and time '''

    def configure_client(self):
        ''' Configure the client to use UDP protocol with IPv4 addressing '''

        # create UDP socket with IPv4 addressing
        self.printwt('Creating UDP/IPv4 socket ...')
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.printwt('Socket created')

    def interact_with_server(self):
        ''' Send request to a UDP Server and receive reply from it. '''
        try:
            name = 'HELLO Client connected'
            self.sock.sendto(name.encode('utf-8'), (self.host, self.port))
            self.printwt('[ SENT ]')
            
            # receive data from server
            resp, server_address = self.sock.recvfrom(4096)
            self.printwt('[ RECEIVED ]')
            
            content = resp.decode()
            print('\n', content, '\n')
            if content.startswith('FAIL'):
                return
            
            while True:
                data=input('Inserire comando: ')
                t1=time.time_ns()
                self.sock.sendto(str(data).encode('utf-8'), (self.host, self.port))
                resp, server_address = self.sock.recvfrom(4096)
                print('Tempo ricezione risposta: ', time.time_ns()-t1  )
                self.printwt('[ RECEIVED ]')
                content = resp.decode()
                
                if content.startswith('FAIL'):
                    continue
                
                if str(data).lower().startswith('list') or str(data).lower().startswith('exit') :
                    print('\n', content, '\n')
                
                if str(data).lower().startswith('get'):
                    file_name = str.split(str(data), ' ', 2)[1]
                    try:
                        file = open('./' + file_name , 'wb')
                        file.write(resp)
                        print('File creato nella cartella del client')
                    except Exception as info:
                        print(info)
                    finally:
                        file.close()
                
                if str(data).lower().startswith('put'):
                    file_name = str.split(str(data), ' ', 2)[1]
                    file = open('./' + file_name, 'rb')
                    self.sock.sendto(file.read(), (self.host, self.port))
                    file.close()
                    
                    resp, server_address = self.sock.recvfrom(4096)
                    self.printwt('[ RECEIVED ]')
                    
                    content = resp.decode()
                    print('\n', content, '\n')
                    
        except OSError as err:
            print(err)

        finally:
            # close socket
            self.printwt('Closing socket...')
            self.sock.close()
            self.printwt('Socket closed')

def main():
    ''' Create a UDP Client, send message to a UDP Server and receive reply. '''

    udp_client = UDPClient('127.0.0.1', 17771)
    udp_client.configure_client()
    udp_client.interact_with_server()

if __name__ == '__main__':
    main()