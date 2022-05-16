import socket as sk
import sys
import os
from os.path import isfile, exists

sys.path.append(os.path.dirname(os.path.dirname(__file__)))

from Modules.response import Response
from Modules.response import BUF_SIZE

# Creiamo il socket
sock = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
clients=[]
states=[]
files=[]

# Associamo il socket alla porta
server_address = ('localhost', 10002)
print ('\n\r starting up on %s port %s' % server_address)
sock.bind(server_address)

class State:
    STATE_OPENING = 0
    STATE_REGULAR = 1
    STATE_WAITFORFILESTATUS = 2   # wait for 'data' or 'close' command, go to state STATE_WAITFORFILEDATA if 'data'
    STATE_WAITFORFILEDATA = 3   # wait for binary content, go to state STATE_WAITFORFILESTATUS after receive
    STATE_SENDFILESTATUS = 4
    STATE_SENDFILEDATA = 5
    STATE_SENDCOMPLETE = 6
    STATE_CLOSED = 7
    
def send_message(client_ind, response_type, message):       # Da usare in giro
    response = '\r\n' + response_type + ' ' + message + '\r\n'
    sock.sendto(response.encode(), clients[client_ind])
    print(clients[client_ind][0] + ': ' + message)

def connection_opening(client_ind, data):
        if str.split(data.decode('utf-8'), ' ', 2)[0] == Response.RESPONSE_HELLO:
            states[client_ind] = State.STATE_REGULAR
            welcome_message = '\r\nBenvenuto sul Server come posso rendermi utile?\r\n\r\nOpzioni disponibili:\r\n\r\n\tlist -> \t\tRestituisce la lista dei nomi dei file disponibili.\r\n\tget <NomeFile> -> Restituisce il file se disponibile.\r\n\tput <NomeFile> -> Carica il file se disponibile.\r\n\t\texit -> \t\tEsce\r'
            sock.sendto(welcome_message.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': Client connesso')
        else:
            failure_message = '\r\n' + Response.RESPONSE_FAIL + ' connessione incorretta\r\n'
            sock.sendto(failure_message.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': Fallimento connessione')
            states[client_ind] = State.STATE_CLOSED  # Connessione chiusa

def wait_for_file_status(client_ind, data):
    content = data.decode('utf-8')
    if content == Response.RESPONSE_DATA:
        response = Response.RESPONSE_OK + ' In attesa...'
        sock.sendto(response.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': In attesa...')
        states[client_ind] = State.STATE_WAITFORFILEDATA
    elif content == Response.RESPONSE_DONE:
        response = Response.RESPONSE_OK + ' File chiuso'
        sock.sendto(response.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': File chiuso')
        files[client_ind].close()                           # Chiusura file
        files[client_ind] = ''
        states[client_ind] = State.STATE_REGULAR
    else:
        response = Response.RESPONSE_FAIL + ' Comando errato. Ricezione abortita'
        sock.sendto(response.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': Comando errato. Ricezione abortita')
        files[client_ind].close()                           # Chiusura file
        files[client_ind] = ''
        states[client_ind] = State.STATE_REGULAR

def wait_for_file_data(client_ind, data):
    try:
        file = files[client_ind]
        file.write(data)
        response = Response.RESPONSE_OK + ' Dato scritto'
        sock.sendto(response.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': Dato scritto')
        states[client_ind] = State.STATE_WAITFORFILESTATUS  # Attesa della prossima direttiva
    except Exception as info:
        print(info)
        response = Response.RESPONSE_FAIL + ' Errore'
        sock.sendto(response.encode(), clients[client_ind])
        states[client_ind] = State.STATE_REGULAR
        
    # c_data = Response.RESPONSE_OK + ' Dato ricevuto'
    # sock.sendto(c_data.encode(), clients[client_ind])
    # print(clients[client_ind][0] + ': Dato ricevuto')
        
    # files[client_ind] = ''
    # states[client_ind] = State.STATE_WAITFORFILESTATUS  

def listing(destinationAddress):
    files=os.listdir('./file/');
    onlyFile=''
    for elem in files:
        if isfile('./file/'+elem):
            onlyFile=  onlyFile + '- ' + str(elem) + '\r\n'
    data = '\r\n'+onlyFile+'\r\n'
    sock.sendto(data.encode(), destinationAddress)       

def putting(c_data, client_ind):
    if c_data == '':        # Nome del file mancante
        response = Response.RESPONSE_FAIL + ' Nome del file mancante, reinserire comando completo.'
        print(clients[client_ind][0] + ': Nome del file mancante')
        sock.sendto(response.encode(), clients[client_ind]);
        return

    if exists('./file/'+ c_data):
        response = Response.RESPONSE_FAIL + ' File già esistente'
        print(clients[client_ind][0] + ': File già esistente')
        sock.sendto(response.encode(), clients[client_ind]);
        return
    
    # creazione file
    states[client_ind] = State.STATE_WAITFORFILESTATUS    # Passaggio allo stato di attesa di invio
    files[client_ind] = open('./file/'+ c_data, 'wb')

    response='OK In attesa del file...'
    print(clients[client_ind][0] + ': In attesa del file...')
    sock.sendto(response.encode(), clients[client_ind])

def getting(c_data, client_ind):
    if isfile('./file/'+ c_data):
        try:
            print(clients[client_ind][0] + ': Richiesta get su file ' + c_data)
            files[client_ind] = open('./file/'+ c_data, 'rb')
            #sock.send(c_data.encode())
            response = Response.RESPONSE_OK + ' File disponibile'
            sock.sendto(response.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': File disponibile')
            states[client_ind] = State.STATE_SENDFILESTATUS
        except Exception as info:
            print(info)
            response = Response.RESPONSE_FAIL + ' Errore. Invio abortito'
            sock.sendto(response.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': Errore. Invio abortito')
            states[client_ind] = State.STATE_REGULAR
            try:
                files[client_ind].close()
            finally:
                return
    else:
        file_data = Response.RESPONSE_FAIL + ' File non trovato, reinserire comando completo.\r\n'
        print(clients[client_ind][0] + ': File ' + c_data + ' inesistente')
        sock.sendto(file_data.encode(), clients[client_ind])

def exiting(c_data, client_ind):
    c_data = Response.RESPONSE_OK + 'Connessione conclusa'
    sock.sendto(c_data.encode(), clients[client_ind])
    print(clients[client_ind][0] + ': Chiusura connessione')
    states[client_ind] = State.STATE_CLOSED         # Connessione chiusa

def regular_actions(client_ind, data):
    # data parsing
    data = data.decode('utf-8').lower()
    content = str.split(data, ' ', 2)
    cmd = content[0]
    c_data = ''
    if len(content) == 2:
        c_data = content[1]
    
    if data == 'list':
        print(clients[client_ind][0] + ': Listing')
        listing(address)
    elif cmd == 'put':
        putting(c_data, client_ind)
    elif cmd == 'get':
        getting(c_data, client_ind)
    elif data == 'exit':
        exiting(c_data, client_ind)
    else:
        c_data = Response.RESPONSE_FAIL + ' Comando sconosciuto'
        sock.sendto(c_data.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': Comando sconosciuto')
        
def send_file_status(client_ind, data):
    content = data.decode('utf-8')
    if content == Response.RESPONSE_OK:
        file = files[client_ind]
        pos = file.tell()
        if file.read(BUF_SIZE):     # Lettura nel file per capire se è finito o meno
            sock.sendto(Response.RESPONSE_DATA.encode(), clients[client_ind])
            states[client_ind] = State.STATE_SENDFILEDATA
            file.seek(pos, 0)       # Ripristino posizione originale
            print(clients[client_ind][0] + ': Invio stato...')
        else:
            sock.sendto(Response.RESPONSE_DONE.encode(), clients[client_ind])
            states[client_ind] = State.STATE_SENDCOMPLETE
            file.close()
            files[client_ind] = ''
    else:
        send_message(client_ind, Response.RESPONSE_FAIL, 'Comando errato. Invio abortito')
        files[client_ind].close();
        files[client_ind] = ''
        states[client_ind] = State.STATE_REGULAR

def send_file_data(client_ind, data):
    file = files[client_ind]
    f_data = file.read(BUF_SIZE)
    sock.sendto(f_data, clients[client_ind])
    states[client_ind] = State.STATE_SENDFILESTATUS
    print(clients[client_ind][0] + ': Invio dati...')

def send_complete(client_ind, data):
    states[client_ind] = State.STATE_REGULAR
    print(clients[client_ind][0] + ': Invio concluso.')

def handle_request(client_ind, data):
    state = states[client_ind]
    
    if state == State.STATE_OPENING:
        connection_opening(client_ind, data)
    elif state == State.STATE_REGULAR:   
        regular_actions(client_ind, data)
    elif state == State.STATE_WAITFORFILESTATUS:
        wait_for_file_status(client_ind, data)
    elif state == State.STATE_WAITFORFILEDATA:
        wait_for_file_data(client_ind, data)
    elif state == State.STATE_SENDFILESTATUS:
        send_file_status(client_ind, data)
    elif state == State.STATE_SENDFILEDATA:
        send_file_data(client_ind, data)
    elif state == State.STATE_SENDCOMPLETE:
        send_complete(client_ind, data)

def check_for_closed_conns():
    closed = []
    for i in range(0, len(clients)):
        if states[i] == State.STATE_CLOSED:
            closed.append(i)
    closed = closed[::-1]               # Inversione dell'array per assicurare la correttezza delle eliminazioni
    for i in closed:
        clients.pop(i)
        states.pop(i)
        files.pop(i)

try:
    while True:
        print("In ascolto")
        data, address = sock.recvfrom(BUF_SIZE)
        print('received %s bytes from %s' % (len(data), address))
        if address not in clients:
            clients.append(address)
            states.append(State.STATE_OPENING)
            files.append('')
        index = clients.index(address)
        handle_request(index, data)
        check_for_closed_conns()        # Alternativa all'uso di un lock
finally:
    sock.close()