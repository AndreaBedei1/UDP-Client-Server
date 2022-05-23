import socket as sk
import sys
import os
import threading
import time
from os.path import isfile, exists

sys.path.append(os.path.dirname(os.path.dirname(__file__)))
from Modules.response import Response
from Modules.response import BUF_SIZE

# Classe interna conenente i diversi stati assumibili dal server.
class State:
    STATE_OPENING = 0
    STATE_REGULAR = 1
    STATE_WAITFORFILESTATUS = 2     # In attesa di un comando 'data' o 'close', se 'data' bisogna passare allo stato STATE_WAITFORFILEDATA.
    STATE_WAITFORFILEDATA = 3   # In attesa di contenuto binario: all'arrivo passare allo stato STATE_WAITFORFILESTATUS.
    STATE_SENDFILESTATUS = 4
    STATE_SENDFILEDATA = 5
    STATE_SENDCOMPLETE = 6
    STATE_CLOSED = 7
    
class ServerThread(threading.Thread):
    # Semplice costruttore che inizializza i campi.
    def __init__(self, server_address):
        threading.Thread.__init__(self)
        self.sock = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
        self.sock.settimeout(5)
        self.clients=[] # Vettore degli indirizzi dei client connessi.
        self.states=[]  # Vettore degli stati del server in base al client.
        self.files=[]   # Vettore di file aperti per ogni client.
        self.do_run = True  # Booleano di controllo esecuzione thread.
        self.norecv = False
        
        # Associamo il socket alla porta.
        print ('\n\rStarting up on %s port %s' % server_address)
        self.sock.bind(server_address)

    # Metodo del thread.
    def run(self):
        try:
            while self.do_run:
                try:
                    data, address = self.sock.recvfrom(BUF_SIZE)    # Riceve messaggio dal client per instaurare la connessione.
                    self.norecv = False
                    # print(address[0] + ': ' + data.decode('utf-8'))
                    if address not in self.clients:
                        # Aggiunta del nuovo client.
                        self.clients.append(address)
                        self.states.append(State.STATE_OPENING)
                        self.files.append('')
                    client_index = self.clients.index(address)
                    self.handle_request(client_index, data)
                    self.check_for_closed_connections()   # Alternativa all'uso di un lock.
                except OSError:
                    self.norecv = True
                    continue
        finally:
            self.sock.close()
            
    def send_message(self, client_ind, response_type, message):       # Da usare in giro
        response = '\r\n' + response_type + ' ' + message + '\r\n'
        self.sock.sendto(response.encode(), self.clients[client_ind])
        print(self.clients[client_ind][0] + ': ' + message)

    
    # Funzione di apertura nuova connessione.
    def connection_opening(self, client_index, data):
            if str.split(data.decode('utf-8'), ' ', 2)[0] == Response.RESPONSE_HELLO:
                # Invio messaggio di benvenuto e lista comandi disponibili.
                self.states[client_index] = State.STATE_REGULAR
                welcome_message = '\r\nBenvenuto sul Server come posso rendermi utile?\r\n\r\nOpzioni disponibili:\r\n\r\n\tlist -> \t\tRestituisce la lista dei nomi dei file disponibili.\r\n\tget <NomeFile> -> Restituisce il file se disponibile.\r\n\tput <NomeFile> -> Carica il file se disponibile.\r\n\t\texit -> \t\tEsce\r'
                self.sock.sendto(welcome_message.encode(), self.clients[client_index])
                print(self.clients[client_index][0] + ': Client connesso')
            else:
                failure_message = '\r\n' + Response.RESPONSE_FAIL + ' connessione incorretta\r\n'
                self.sock.sendto(failure_message.encode(), self.clients[client_index])
                print(self.clients[client_index][0] + ': Fallimento connessione')
                self.states[client_index] = State.STATE_CLOSED  # Connessione chiusa
    
    # Questa funzione viene eseguita in seguito al cambio di stato operato dal comando put.
    def wait_for_file_status(self, client_index, data):
        content = data.decode('utf-8')
        if content == Response.RESPONSE_DATA:
            # Se il client comunica di spedire altri dati aggiorniamo lo stato in modo da permettere la scrittura di tali dati.
            response = Response.RESPONSE_OK + ' In attesa...'
            self.sock.sendto(response.encode(), self.clients[client_index])
            #print(self.clients[client_ind][0] + ': In attesa...')
            self.states[client_index] = State.STATE_WAITFORFILEDATA
        elif content == Response.RESPONSE_DONE:
            # Invece, se il client comunica di aver finito l'upload, lo stato sarà regolare (in attesa del prossimo comando.)
            self.send_message(client_index, Response.RESPONSE_OK, 'File chiuso')
            self.files[client_index].close()                           # Chiusura file
            self.files[client_index] = ''
            self.states[client_index] = State.STATE_REGULAR
        else:
            # In caso di errori.
            self.send_message(client_index, Response.RESPONSE_FAIL, 'Comando errato. Ricezione abortita')
            self.files[client_index].close()  # Chiusura file.
            self.files[client_index] = ''
            self.states[client_index] = State.STATE_REGULAR
    
    # Questa funzione gestisce lo stato del server STATE_WAITFORFILEDATA. 
    def wait_for_file_data(self, client_index, data):
        # Si effettua la put vera e propria, scrivendo i dati ricevuti sul file creato.
        try:
            file = self.files[client_index]
            file.write(data)
            response = Response.RESPONSE_OK + ' Dato scritto'
            self.sock.sendto(response.encode(), self.clients[client_index])
            #print(self.clients[client_ind][0] + ': Dato scritto')
            self.states[client_index] = State.STATE_WAITFORFILESTATUS  # Attesa della prossima direttiva
        except Exception as info:
            print(info)
            response = Response.RESPONSE_FAIL + ' Errore'
            self.sock.sendto(response.encode(), self.clients[client_index])
            self.states[client_index] = State.STATE_REGULAR
    
    # Funzione che gestisce il comando list.
    def listing(self, destinationAddress):
        # Viene creato ed inviato al client un elenco dei file nella directory corrente.
        folder_content=os.listdir('./file/');
        files=''
        for elem in folder_content:
            if isfile('./file/'+elem):
                files=  files + '- ' + str(elem) + '\r\n'
        data = '\r\n'+files+'\r\n'
        self.sock.sendto(data.encode(), destinationAddress)       
    
    # Funzione che gestisce il comando put. In realtà, questa funzione s'occupa solo di cambiare lo stato del server per permettere la put vera e propria.
    def putting(self, file_name, client_index):
        if file_name == '':    # Nome del file mancante.
            response = Response.RESPONSE_FAIL + ' Nome del file mancante, reinserire comando completo.'
            print(self.clients[client_index][0] + ': Nome del file mancante')
            self.sock.sendto(response.encode(), self.clients[client_index]);
            return
        if '../' in file_name: # Se si indica un file in un'altra cartella rispetto a quella prevista.
            self.send_message(client_index, Response.RESPONSE_FAIL, 'Percorso o file illegale')
            return
        if exists('./file/'+ file_name):
            self.send_message(client_index, Response.RESPONSE_FAIL, 'File già esistente')
            return
        # Inizio sequenza di download del file inviato dal client.
        print(self.clients[client_index][0] + ': Ricevuta richiesta put')
        self.states[client_index] = State.STATE_WAITFORFILESTATUS     # Passaggio allo stato di attesa di invio.
        self.files[client_index] = open('./file/'+ file_name, 'wb')
        self.send_message(client_index, Response.RESPONSE_OK, 'In attesa del file...')
        print(self.clients[client_index][0] + ': Inizio trasferimento')
    
    # Funzione che gestisce il comando get. In realtà, questa funzione s'occupa solo di cambiare lo stato del server per permettere la get vera e propria.
    def getting(self, file_name, client_index):
        if '../' in file_name: # Se si cerca d'ottenere un file in un'altra cartella da quella prevista.
            self.send_message(client_index, Response.RESPONSE_FAIL, 'Percorso o file illegale')
            return
        if isfile('./file/'+ file_name):   # Controllo presenza file richiesto.
            try:
                # Invio del nome del file e cambiamento di stato.
                print(self.clients[client_index][0] + ': Richiesta get su file ' + file_name)
                self.files[client_index] = open('./file/'+ file_name, 'rb')
                self.send_message(client_index, Response.RESPONSE_OK, 'File disponibile')
                self.states[client_index] = State.STATE_SENDFILESTATUS
            except Exception as info:
                print(info)
                self.send_message(client_index, Response.RESPONSE_FAIL, 'Errore: invio abortito')
                self.states[client_index] = State.STATE_REGULAR
                try:
                    self.files[client_index].close()
                finally:
                    return
        else:   # In caso di errore, come file non trovato sul server o comando incompleto.
            file_data = Response.RESPONSE_FAIL + ' File non trovato, reinserire comando completo.\r\n'
            print(self.clients[client_index][0] + ': File ' + file_name + ' inesistente')
            self.sock.sendto(file_data.encode(), self.clients[client_index])
    
    # Funzione che gestice il comando exit. In realtà si occupa solo di aggiornare lo stato del server.
    def exiting(self, client_index):
        self.send_message(client_index, Response.RESPONSE_OK, 'Connessione conclusa')
        self.states[client_index] = State.STATE_CLOSED    # Connessione chiusa.
    
    # Funzione core che gestisce la richiesta di uno specifico comando. 
    def regular_actions(self, client_index, command_inserted):
        # Manipolazione e scomposizione della stringa di comando arrivata.
        command_inserted = command_inserted.decode('utf-8')
        content = str.split(command_inserted, ' ', 2)
        command = content[0].lower()
        file_target = ''
        if len(content) == 2:
            file_target = content[1]
        
        # Identificazione comando.
        if command_inserted.lower() == 'list':
            print(self.clients[client_index][0] + ': Listing')
            self.listing(self.clients[client_index])
        elif command == 'put':
            self.putting(file_target, client_index)
        elif command == 'get':
            self.getting(file_target, client_index)
        elif command_inserted.lower() == 'exit':
            self.exiting(client_index)
        else:
            self.send_message(client_index, Response.RESPONSE_FAIL, 'Comando sconosciuto')
         
    # Questa funzione viene eseguita in seguito al cambio di stato operato dal comando get.
    def send_file_status(self, client_index, data):
        content = data.decode('utf-8')
        if content == Response.RESPONSE_OK:
            file = self.files[client_index]
            position = file.tell()
            if file.read(BUF_SIZE):     # Se nel file richiesto dalla get c'è altro contenuto da trasferire.
                self.sock.sendto(Response.RESPONSE_DATA.encode(), self.clients[client_index])
                self.states[client_index] = State.STATE_SENDFILEDATA
                file.seek(position, 0)   # Ripristino posizione originale.
                #print(self.clients[client_ind][0] + ': Invio stato...')
            else:   # Tutto il file richiesto è stato trasferito. 
                # Bisogna comunicare al client che il trasferimento è stato completato, chiudere il file aperto ed aggiornare lo stato..
                self.sock.sendto(Response.RESPONSE_DONE.encode(), self.clients[client_index])
                self.states[client_index] = State.STATE_SENDCOMPLETE
                file.close()
                self.files[client_index] = ''
        else:
            self.send_message(client_index, Response.RESPONSE_FAIL, 'Comando errato. Invio abortito')
            self.files[client_index].close();
            self.files[client_index] = ''
            self.states[client_index] = State.STATE_REGULAR
    
    # Questa funzione gestisce lo stato del server STATE_SENDFILEDATA. 
    def send_file_data(self, client_index):
        # Esegue l'invio effettivo del contenuto del file richiesto tramite il comando get.
        file = self.files[client_index]
        file_content = file.read(BUF_SIZE)
        self.sock.sendto(file_content, self.clients[client_index])
        self.states[client_index] = State.STATE_SENDFILESTATUS
        #print(self.clients[client_ind][0] + ': Invio dati...')
    
    # Questa funzione gestisce lo stato del server STATE_SENDCOMPLETE. 
    def send_complete(self, client_index):
        # Aggiorna lo stato attuale del server in seguito al completamento di una get da parte del client.
        self.states[client_index] = State.STATE_REGULAR
        print(self.clients[client_index][0] + ': Invio concluso.')
    
    # Funzione contenente le azioni di intraprendere in base allo stato attuale del server.
    def handle_request(self, client_index, data):
        state = self.states[client_index]
        
        # Ad ogni stato assunto dal server corrisponde un'azione diversa.
        if state == State.STATE_OPENING:
            self.connection_opening(client_index, data)
        elif state == State.STATE_REGULAR:   
            self.regular_actions(client_index, data)
        elif state == State.STATE_WAITFORFILESTATUS:
            self.wait_for_file_status(client_index, data)
        elif state == State.STATE_WAITFORFILEDATA:
            self.wait_for_file_data(client_index, data)
        elif state == State.STATE_SENDFILESTATUS:
            self.send_file_status(client_index, data)
        elif state == State.STATE_SENDFILEDATA:
            self.send_file_data(client_index)
        elif state == State.STATE_SENDCOMPLETE:
            self.send_complete(client_index)
            
    # Funzione di controllo ed eliminazione riferimenti a connessioni chiuse.
    def check_for_closed_connections(self):
        # Si controlla se esistono connessioni chiuse, in modo da aggiornare le strutture dati.
        closed = []
        for i in range(0, len(self.clients)):
            if self.states[i] == State.STATE_CLOSED:
                closed.append(i)
        closed = closed[::-1]   # Inversione dell'array per assicurare la correttezza delle eliminazioni.
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
        print("Terminazione server in corso")
        thread.do_run = False   # Terminazione thread.
    finally:
        thread.join()
        print("Server terminato")