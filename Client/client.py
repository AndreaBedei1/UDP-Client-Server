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
        print('Socket creato', flush = True)
        
    def connection_setup(self):
        msg = Response.RESPONSE_HELLO + ' Client connected'
        self.sock.sendto(msg.encode('utf-8'), (self.host, self.port))
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n', flush = True)
        if content.startswith(Response.RESPONSE_FAIL):
            return False
        return True
    
    def get_list(self):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        content = resp.decode()
        print('\n', content, '\n', flush = True)
    
    def get_file(self, data):
        file_name = str.split(str(data), ' ', 2)[1]
        
        if isfile('./' + file_name):
            print('Esiste già un file con questo nome nella cartella, ma verrà sovrascritto', flush = True)
           
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        receiving = False
        if str(resp.decode()).startswith(Response.RESPONSE_FAIL):
            print('File inesistente sul server', flush = True)
            return
        try:            
            file = open('./' + file_name , 'wb')
            print('File creato nella cartella corrente', flush = True)
            
            print('Ricezione disponibilità', flush = True)   
            if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                print("Inizio ricezione, attendere...")
                receiving = True
                
            while receiving:
                #print('Ricezione status', flush = True) 
                resp, server_address = self.sock.recvfrom(BUF_SIZE)
                if resp.decode('utf-8') == Response.RESPONSE_DATA:
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    #print('Invio OK dopo status', flush = True)

                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    file.write(resp)
                    #print('Ricezione dati', flush = True)
                    
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    #print('Invio OK dopo dati', flush = True)
                elif resp.decode('utf-8') == Response.RESPONSE_DONE:
                    file.close()
                    print('Ricezione conclusa', flush = True)
                    self.sock.sendto(Response.RESPONSE_OK.encode(), (self.host, self.port))
                    receiving = False
                else:
                    file.close()
                    receiving = False
        except Exception as info:
            print(info, flush = True)
        finally:
            file.close()
            
    def put_file(self, file_name):
        resp, server_address = self.sock.recvfrom(BUF_SIZE)
        r = resp.decode('utf-8')
        if r.startswith(Response.RESPONSE_FAIL):
            print(r + '\n', flush = True)
            return
        print("Inizio invio...", flush = True)
        try:
            file_path = './' + file_name
            file = open(file_path, 'rb')
            file_size = os.path.getsize(file_path)
            perc = 0
            tenth = file_size / 10
            threshold = tenth 
            content = file.read(BUF_SIZE)
            while content:
                pos = file.tell()
                if pos >= threshold:
                    perc = perc + 10
                    print(str(perc) + '%', flush = True)
                    threshold = threshold + tenth
                
                self.sock.sendto(Response.RESPONSE_DATA.encode('utf-8'), (self.host, self.port))    # Invio stato
                resp, server_address = self.sock.recvfrom(BUF_SIZE)                                 # Attesa risposta dopo l'invio dello stato
                if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                    self.sock.sendto(content, (self.host, self.port))           # Invio dati 
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)         # Attesa risposta dopo l'invio di dati
                    if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                        content = file.read(BUF_SIZE)                           # Lettura della prossima sezione del file
                    else:
                        print("Errore ricevuto. Chiusura file...", flush = True)
                        return          # Errore del server, termina immediatamente l'invio. Il server non aspetta ulteriori risposte
                else:
                    print("Errore ricevuto. Chiusura file...", flush = True)
                    return          # Errore del server, termina immediatamente l'invio. Il server non aspetta ulteriori risposte
            print("Invio stato DONE. Chiusura file...", flush = True)
            self.sock.sendto(Response.RESPONSE_DONE.encode('utf-8'), (self.host, self.port))    # Invio segnale di terminazione del file
            resp, server_address = self.sock.recvfrom(BUF_SIZE)         # Attesa risposta dopo la terminazione del file
            if resp.decode('utf-8').startswith(Response.RESPONSE_OK):
                print("Invio completato con successo", flush = True)
            else:
                print("Invio completato con errori", flush = True)
        finally:
            file.close()

    def interact_with_server(self):
        ''' Send request to a UDP Server and receive reply from it. '''
        try:
            if not self.connection_setup():
               return
            while True:
                data=input('Inserire comando: ')
                l_data = data.lower()
                t1=time.time()
                
                if l_data.startswith('put'):
                    try:
                        file_name = str.split(str(data), ' ', 2)[1]
                    except:
                        print('Errore nalla scrittura del comando, reinserirlo correttamente', flush = True)
                        continue
                    
                    if not isfile('./' + file_name):
                        file_data='File non trovato, reinserire comando completo.\r\n'
                        print(file_data, flush = True)
                        continue

                if l_data.startswith('get'):
                    try:
                        file_name = str.split(str(data), ' ', 2)[1]
                    except:
                        print('Errore nalla scrittura del comando, reinserirlo correttamente', flush = True)
                        continue

                self.sock.sendto(str(data).encode('utf-8'), (self.host, self.port))
                if l_data == 'exit' :
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    content = resp.decode()
                    print('\n', content, '\n', flush = True)
                    return
                elif l_data.startswith('list'):
                    self.get_list()
                elif l_data.startswith('get'):
                    self.get_file(data)
                elif l_data.startswith('put'):  
                    self.put_file(file_name)
                else :
                    resp, server_address = self.sock.recvfrom(BUF_SIZE)
                    content = resp.decode()
                    print('\n', content, '\n', flush = True)    
                print('Tempo ricezione risposta: ', (time.time()-t1), flush = True)
        except OSError as err:
            print(err, flush = True)
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