import socket as sk
import os
from os.path import isfile, exists

# Creiamo il socket
sock = sk.socket(sk.AF_INET, sk.SOCK_DGRAM)
clients=[]
states=[]
files=[]
# associamo il socket alla porta
server_address = ('localhost', 10002)
print ('\n\r starting up on %s port %s' % server_address)
sock.bind(server_address)

class State:
    STATE_OPENING = 0
    STATE_REGULAR = 1
    STATE_WAITFORFILECONTENTS = 2
    STATE_CLOSED = 3
    # STATE_WAITFORFILECONTENTS_1 = 3   # wait for 'data' or 'close' command, go to state STATE_WAITFORFILECONTENTS_2 if 'data'
    # STATE_WAITFORFILECONTENTS_2 = 4   # wait for binary content, go to state STATE_WAITFORFILECONTENTS_1 after receive

def connection_opening(client_ind, data):
        if str.split(data.decode('utf-8'), ' ', 2)[0].lower() == 'hello':
            states[client_ind] = State.STATE_REGULAR
            welcome_message = '\r\nBenvenuto sul Server come posso rendermi utile?\r\n\r\nOpzioni disponibili:\r\n\r\n\tlist -> \t\tRestituisce la lista dei nomi dei file disponibili.\r\n\tget <NomeFile> -> Restituisce il file se disponibile.\r\n\tput <NomeFile> -> Carica il file se disponibile.\r\n\t\texit -> \t\tEsce\r'
            sock.sendto(welcome_message.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': Client connesso')
        else:
            failure_message = '\r\nFAIL connessione incorretta\r\n'
            sock.sendto(failure_message.encode(), clients[client_ind])
            print(clients[client_ind][0] + ': Fallimento connessione')
            states[client_ind] = State.STATE_CLOSED  # Connessione chiusa

def wait_for_file(client_ind, data):
    try:
        file = open('./file/'+ files[client_ind], 'wb')
        file.write(data)
    except Exception as info:
        print(info)
    finally:
        file.close()
        
    c_data = 'DONE File ricevuto'
    sock.sendto(c_data.encode(), clients[client_ind])
    print(clients[client_ind][0] + ': File ricevuto')
        
    files[client_ind] = ''
    states[client_ind] = State.STATE_REGULAR    # Ritorno allo stato regolare dopo la scrittura

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
        response='FAIL Nome del file mancante, reinserire comando completo.'
        print(clients[client_ind][0] + ': Nome del file mancante')
        sock.sendto(response.encode(), clients[client_ind]);
        return
    
    if exists('./file/'+ c_data):
        response='FAIL File già esistente'
        print(clients[client_ind][0] + ': File già esistente')
        sock.sendto(response.encode(), clients[client_ind]);
        return
    
    # creazione file
    states[client_ind] = State.STATE_WAITFORFILECONTENTS    # Passaggio allo stato di attesa di invio
    files[client_ind] = c_data
    
    response='OK In attesa del file...'
    print(clients[client_ind][0] + ': In attesa del file...')
    sock.sendto(response.encode(), clients[client_ind])

def getting(c_data, client_ind):
    if isfile('./file/'+ c_data):
        try:
            print(clients[client_ind][0] + ': Richiesta get su file ' + c_data)
            file=open('./file/'+ c_data, 'rb')
            #sock.send(c_data.encode())
            file_data=file.read()
            sock.sendto(file_data, clients[client_ind])
        except Exception as info:
            file_data=''
            print(info)
        finally:
            file.close()
    else:
        file_data='FAIL File non trovato, reinserire comando completo.\r\n'
        print(clients[client_ind][0] + ': File ' + c_data + ' inesistente')
        sock.sendto(file_data.encode(), clients[client_ind])

def exiting(c_data, client_ind):
    c_data = 'Connessione conclusa'
    sock.sendto(c_data.encode(), clients[client_ind])
    print(clients[client_ind][0] + ': Chiusura connessione')
    states[client_ind] = State.STATE_CLOSED # Connessione chiusa

def operative_actions(client_ind, data):
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
        c_data = 'FAIL Comando sconosciuto'
        sock.sendto(c_data.encode(), clients[client_ind])
        print(clients[client_ind][0] + ': Comando sconosciuto')
    

def handle_request(client_ind, data):
    state = states[client_ind]
    
    if state == State.STATE_OPENING:
        connection_opening(client_ind, data)
    elif state == State.STATE_REGULAR:   
        operative_actions(client_ind, data)
    elif state == State.STATE_WAITFORFILECONTENTS:
        wait_for_file(client_ind, data)

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
        data, address = sock.recvfrom(4096)
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