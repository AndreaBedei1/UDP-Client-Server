import socket as sk
import sys
import os
import threading
import time
from os.path import isfile, exists

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Modules.response import Response
from Modules.response import BUF_SIZE

class State:
    STATE_OPENING = 0
    STATE_REGULAR = 1
    STATE_WAITFORFILESTATUS = 2   # wait for 'data' or 'close' command, go to state STATE_WAITFORFILEDATA if 'data'
    STATE_WAITFORFILEDATA = 3   # wait for binary content, go to state STATE_WAITFORFILESTATUS after receive
    STATE_SENDFILESTATUS = 4
    STATE_SENDFILEDATA = 5
    STATE_SENDCOMPLETE = 6
    STATE_CLOSED = 7
    
class ServerThread(threading.Thread):
    def __init__(self, server_address):
        threading.Thread.__init__(self)
        self.sock = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.clients=[]
        self.states=[]
        self.files=[]
        self.do_run = True
        self.norecv = False
        
        # Associamo il socket alla porta
        print ('\n\r starting up on %s port %s' % server_address)
        self.sock.bind(server_address)

    def run(self):
        try:
            while self.do_run:
                try:
                    if not self.norecv:
                        print("In ascolto")
                    data, address = self.sock.recvfrom(BUF_SIZE)
                    self.norecv = False
                    # print(address[0] + ': ' + data.decode('utf-8'))
                    if address not in self.clients:
                        self.clients.append(address)
                        self.states.append(State.STATE_OPENING)
                        self.files.append('')
                    index = self.clients.index(address)
                    self.handle_request(index, data)
                    self.check_for_closed_conns()        # Alternativa all'uso di un lock
                except OSError:
                    self.norecv = True
                    continue
        finally:
            self.sock.close()

    def send_message(self, client_ind, response_type, message):       # Da usare in giro
        response = '\r\n' + response_type + ' ' + message + '\r\n'
        self.sock.sendto(response.encode(), self.clients[client_ind])
        print(self.clients[client_ind][0] + ': ' + message)
    
    def connection_opening(self, client_ind, data):
            if str.split(data.decode('utf-8'), ' ', 2)[0] == Response.RESPONSE_HELLO:
                self.states[client_ind] = State.STATE_REGULAR
                welcome_message = '\r\nBenvenuto sul Server come posso rendermi utile?\r\n\r\nOpzioni disponibili:\r\n\r\n\tlist -> \t\tRestituisce la lista dei nomi dei file disponibili.\r\n\tget <NomeFile> -> Restituisce il file se disponibile.\r\n\tput <NomeFile> -> Carica il file se disponibile.\r\n\t\texit -> \t\tEsce\r'
                self.sock.sendto(welcome_message.encode(), self.clients[client_ind])
                print(self.clients[client_ind][0] + ': Client connesso')
            else:
                failure_message = '\r\n' + Response.RESPONSE_FAIL + ' connessione incorretta\r\n'
                self.sock.sendto(failure_message.encode(), self.clients[client_ind])
                print(self.clients[client_ind][0] + ': Fallimento connessione')
                self.states[client_ind] = State.STATE_CLOSED  # Connessione chiusa
    
    def wait_for_file_status(self, client_ind, data):
        content = data.decode('utf-8')
        if content == Response.RESPONSE_DATA:
            response = Response.RESPONSE_OK + ' In attesa...'
            self.sock.sendto(response.encode(), self.clients[client_ind])
            print(self.clients[client_ind][0] + ': In attesa...')
            self.states[client_ind] = State.STATE_WAITFORFILEDATA
        elif content == Response.RESPONSE_DONE:
            response = Response.RESPONSE_OK + ' File chiuso'
            self.sock.sendto(response.encode(), self.clients[client_ind])
            print(self.clients[client_ind][0] + ': File chiuso')
            self.files[client_ind].close()                           # Chiusura file
            self.files[client_ind] = ''
            self.states[client_ind] = State.STATE_REGULAR
        else:
            response = Response.RESPONSE_FAIL + ' Comando errato. Ricezione abortita'
            self.sock.sendto(response.encode(), self.clients[client_ind])
            print(self.clients[client_ind][0] + ': Comando errato. Ricezione abortita')
            self.files[client_ind].close()                           # Chiusura file
            self.files[client_ind] = ''
            self.states[client_ind] = State.STATE_REGULAR
    
    def wait_for_file_data(self, client_ind, data):
        try:
            file = self.files[client_ind]
            file.write(data)
            response = Response.RESPONSE_OK + ' Dato scritto'
            self.sock.sendto(response.encode(), self.clients[client_ind])
            print(self.clients[client_ind][0] + ': Dato scritto')
            self.states[client_ind] = State.STATE_WAITFORFILESTATUS  # Attesa della prossima direttiva
        except Exception as info:
            print(info)
            response = Response.RESPONSE_FAIL + ' Errore'
            self.sock.sendto(response.encode(), self.clients[client_ind])
            self.states[client_ind] = State.STATE_REGULAR
            
        # c_data = Response.RESPONSE_OK + ' Dato ricevuto'
        # sock.sendto(c_data.encode(), clients[client_ind])
        # print(clients[client_ind][0] + ': Dato ricevuto')
            
        # files[client_ind] = ''
        # states[client_ind] = State.STATE_WAITFORFILESTATUS  
    
    def listing(self, destinationAddress):
        files=os.listdir('./file/');
        onlyFile=''
        for elem in files:
            if isfile('./file/'+elem):
                onlyFile=  onlyFile + '- ' + str(elem) + '\r\n'
        data = '\r\n'+onlyFile+'\r\n'
        self.sock.sendto(data.encode(), destinationAddress)       
    
    def putting(self, c_data, client_ind):
        if c_data == '':        # Nome del file mancante
            response = Response.RESPONSE_FAIL + ' Nome del file mancante, reinserire comando completo.'
            print(self.clients[client_ind][0] + ': Nome del file mancante')
            self.sock.sendto(response.encode(), self.clients[client_ind]);
            return
        
        if '../' in c_data:
            self.send_message(client_ind, Response.RESPONSE_FAIL, 'Percorso a file illegale')
            return
            
        if exists('./file/'+ c_data):
            response = Response.RESPONSE_FAIL + ' File già esistente'
            print(self.clients[client_ind][0] + ': File già esistente')
            self.sock.sendto(response.encode(), self.clients[client_ind]);
            return
        
        # creazione file
        self.states[client_ind] = State.STATE_WAITFORFILESTATUS    # Passaggio allo stato di attesa di invio
        self.files[client_ind] = open('./file/'+ c_data, 'wb')
    
        response='OK In attesa del file...'
        print(self.clients[client_ind][0] + ': In attesa del file...')
        self.sock.sendto(response.encode(), self.clients[client_ind])
    
    def getting(self, c_data, client_ind):
        if '../' in c_data:
            self.send_message(client_ind, Response.RESPONSE_FAIL, 'Percorso a file illegale')
            return
        
        if isfile('./file/'+ c_data):
            try:
                print(self.clients[client_ind][0] + ': Richiesta get su file ' + c_data)
                self.files[client_ind] = open('./file/'+ c_data, 'rb')
                #sock.send(c_data.encode())
                response = Response.RESPONSE_OK + ' File disponibile'
                self.sock.sendto(response.encode(), self.clients[client_ind])
                print(self.clients[client_ind][0] + ': File disponibile')
                self.states[client_ind] = State.STATE_SENDFILESTATUS
            except Exception as info:
                print(info)
                response = Response.RESPONSE_FAIL + ' Errore. Invio abortito'
                self.sock.sendto(response.encode(), self.clients[client_ind])
                print(self.clients[client_ind][0] + ': Errore. Invio abortito')
                self.states[client_ind] = State.STATE_REGULAR
                try:
                    self.files[client_ind].close()
                finally:
                    return
        else:
            file_data = Response.RESPONSE_FAIL + ' File non trovato, reinserire comando completo.\r\n'
            print(self.clients[client_ind][0] + ': File ' + c_data + ' inesistente')
            self.sock.sendto(file_data.encode(), self.clients[client_ind])
    
    def exiting(self, c_data, client_ind):
        c_data = Response.RESPONSE_OK + 'Connessione conclusa'
        self.sock.sendto(c_data.encode(), self.clients[client_ind])
        print(self.clients[client_ind][0] + ': Chiusura connessione')
        self.states[client_ind] = State.STATE_CLOSED         # Connessione chiusa
    
    def regular_actions(self, client_ind, data):
        # data parsing
        data = data.decode('utf-8')
        content = str.split(data, ' ', 2)
        cmd = content[0].lower()
        c_data = ''
        if len(content) == 2:
            c_data = content[1]
        
        if data == 'list':
            print(self.clients[client_ind][0] + ': Listing')
            self.listing(self.clients[client_ind])
        elif cmd == 'put':
            self.putting(c_data, client_ind)
        elif cmd == 'get':
            self.getting(c_data, client_ind)
        elif data == 'exit':
            self.exiting(c_data, client_ind)
        else:
            c_data = Response.RESPONSE_FAIL + ' Comando sconosciuto'
            self.sock.sendto(c_data.encode(), self.clients[client_ind])
            print(self.clients[client_ind][0] + ': Comando sconosciuto')
            
    def send_file_status(self, client_ind, data):
        content = data.decode('utf-8')
        if content == Response.RESPONSE_OK:
            file = self.files[client_ind]
            pos = file.tell()
            if file.read(BUF_SIZE):     # Lettura nel file per capire se è finito o meno
                self.sock.sendto(Response.RESPONSE_DATA.encode(), self.clients[client_ind])
                self.states[client_ind] = State.STATE_SENDFILEDATA
                file.seek(pos, 0)       # Ripristino posizione originale
                print(self.clients[client_ind][0] + ': Invio stato...')
            else:
                self.sock.sendto(Response.RESPONSE_DONE.encode(), self.clients[client_ind])
                self.states[client_ind] = State.STATE_SENDCOMPLETE
                file.close()
                self.files[client_ind] = ''
        else:
            self.send_message(client_ind, Response.RESPONSE_FAIL, 'Comando errato. Invio abortito')
            self.files[client_ind].close();
            self.files[client_ind] = ''
            self.states[client_ind] = State.STATE_REGULAR
    
    def send_file_data(self, client_ind, data):
        file = self.files[client_ind]
        f_data = file.read(BUF_SIZE)
        self.sock.sendto(f_data, self.clients[client_ind])
        self.states[client_ind] = State.STATE_SENDFILESTATUS
        print(self.clients[client_ind][0] + ': Invio dati...')
    
    def send_complete(self, client_ind, data):
        self.states[client_ind] = State.STATE_REGULAR
        print(self.clients[client_ind][0] + ': Invio concluso.')
    
    def handle_request(self, client_ind, data):
        state = self.states[client_ind]
        
        if state == State.STATE_OPENING:
            self.connection_opening(client_ind, data)
        elif state == State.STATE_REGULAR:   
            self.regular_actions(client_ind, data)
        elif state == State.STATE_WAITFORFILESTATUS:
            self.wait_for_file_status(client_ind, data)
        elif state == State.STATE_WAITFORFILEDATA:
            self.wait_for_file_data(client_ind, data)
        elif state == State.STATE_SENDFILESTATUS:
            self.send_file_status(client_ind, data)
        elif state == State.STATE_SENDFILEDATA:
            self.send_file_data(client_ind, data)
        elif state == State.STATE_SENDCOMPLETE:
            self.send_complete(client_ind, data)
    
    def check_for_closed_conns(self):
        closed = []
        for i in range(0, len(self.clients)):
            if self.states[i] == State.STATE_CLOSED:
                closed.append(i)
        closed = closed[::-1]               # Inversione dell'array per assicurare la correttezza delle eliminazioni
        for i in closed:
            self.clients.pop(i)
            self.states.pop(i)
            self.files.pop(i)

if __name__ == '__main__':
    try:
        thread = ServerThread(('localhost', 10002))
        thread.start()
        while True:
            time.sleep(0.2)
    except KeyboardInterrupt:
        print("Il server verrà terminato")
        thread.do_run = False
    finally:
        thread.join()
        print("Server terminato")
    
    