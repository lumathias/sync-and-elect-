import os
import sys
import requests
import time
import threading
import heapq
from flask import Flask, request, jsonify

app = Flask(__name__)

# --- Configuração de Ambiente (Local vs Kubernetes) ---
IS_K8S = os.getenv('K8S_ENV', 'false').lower() == 'true'

if IS_K8S:
    # Configuração Kubernetes
    HOSTNAME = os.getenv('HOSTNAME', 'app-0')
    PROCESS_ID = int(HOSTNAME.split('-')[-1])
    NUM_PROCESSES = 3
    PEERS = [f"app-{i}.app-service:5000" for i in range(NUM_PROCESSES)]
    MY_PORT = 5000
    print(f"Rodando em modo KUBERNETES. ID: {PROCESS_ID}")
else:
    # Configuração Local (VS Code)
    try:
        PROCESS_ID = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.getenv('PROCESS_ID', 0))
    except ValueError:
        PROCESS_ID = 0
        
    NUM_PROCESSES = 3
    # Localmente, usamos portas diferentes para cada processo: 5000, 5001, 5002
    base_port = 5000
    PEERS = [f"localhost:{base_port + i}" for i in range(NUM_PROCESSES)]
    MY_PORT = base_port + PROCESS_ID
    print(f"Rodando em modo LOCAL. ID: {PROCESS_ID}, Porta: {MY_PORT}")

# --- Estado Global ---
clock_lock = threading.Lock()
logical_clock = 0

# Estado Task 1 (Total Order)
msg_queue = [] # Heap de prioridade
ack_counts = {} # { (timestamp, process_id): count }
delivery_log = []

# Estado Task 2 (Mutex)
mutex_state = "RELEASED" # RELEASED, WANTED, HELD
mutex_queue = []
mutex_acks = 0

# Estado Task 3 (Bully)
coordinator_id = None
election_in_progress = False

def get_clock():
    with clock_lock:
        return logical_clock

def increment_clock():
    global logical_clock
    with clock_lock:
        logical_clock += 1
        return logical_clock

def update_clock(timestamp):
    global logical_clock
    with clock_lock:
        logical_clock = max(logical_clock, timestamp) + 1
        return logical_clock

def broadcast(endpoint, data):
    """Envia mensagem para todos os peers."""
    for i, peer in enumerate(PEERS):
        if i == PROCESS_ID: continue
        # Evita travar se um peer não estiver rodando localmente
        try:
            url = f"http://{peer}{endpoint}"
            requests.post(url, json=data, timeout=2)
        except requests.exceptions.ConnectionError:
            if not IS_K8S:
                pass # Ignora erros de conexão locais para não sujar o log
        except Exception as e:
            print(f"Erro ao contatar {peer}: {e}")

# ==============================================================================
# TAREFA 1: MULTICAST TOTAL ORDER
# ==============================================================================

@app.route('/multicast/send', methods=['POST'])
def send_multicast():
    msg_content = request.json.get('msg', 'Hello')
    
    # Mensagens transportam marca lógica de tempo
    ts = increment_clock()
    msg_data = {
        'type': 'MULTICAST',
        'content': msg_content,
        'ts': ts,
        'sender': PROCESS_ID
    }
    
    handle_incoming_multicast(msg_data)
    threading.Thread(target=broadcast, args=('/multicast/receive', msg_data)).start()
    
    return jsonify({"status": "multicasted", "timestamp": ts})

@app.route('/multicast/receive', methods=['POST'])
def receive_multicast():
    """Recebe mensagem de outro processo"""
    data = request.json
    handle_incoming_multicast(data)
    
    # Envia ACK de volta (Broadcast do ACK)
    # Simulando atraso se solicitado via query param ?delay=true
    if request.args.get('delay') == 'true' and PROCESS_ID == 1: 
        print("Simulando atraso no ACK...")
        time.sleep(10)

    # Incrementa relógio ao receber
    ts = update_clock(data['ts'])
    
    ack_data = {'type': 'ACK', 'msg_ts': data['ts'], 'msg_sender': data['sender'], 'sender': PROCESS_ID, 'ts': ts}
    
    # 1. Envia ACK para os outros
    threading.Thread(target=broadcast, args=('/multicast/ack', ack_data)).start()

    # 2. CORREÇÃO CRÍTICA: Contabiliza o MEU próprio ACK localmente
    # Sem isso, eu fico esperando um voto que nunca chega (o meu)
    target = (data['ts'], data['sender'])
    if target in ack_counts:
        ack_counts[target] += 1
    check_delivery()
    
    return jsonify({"status": "received"})

def handle_incoming_multicast(data):
    # Ordenação na fila local
    entry = (data['ts'], data['sender'], data)
    if entry not in msg_queue:
        heapq.heappush(msg_queue, entry)
        ack_counts[(data['ts'], data['sender'])] = 1

@app.route('/multicast/ack', methods=['POST'])
def receive_ack():
    data = request.json
    update_clock(data['ts'])
    
    target = (data['msg_ts'], data['msg_sender'])
    if target in ack_counts:
        ack_counts[target] += 1
    
    check_delivery()
    return jsonify({"status": "ack_processed"})

def check_delivery():
    # Entrega se estiver no topo e tiver ACKs de todos
    while msg_queue:
        top_ts, top_sender, top_data = msg_queue[0]
        count = ack_counts.get((top_ts, top_sender), 0)
        
        if count >= NUM_PROCESSES:
            msg = heapq.heappop(msg_queue)
            log = f"Process {PROCESS_ID} ENTREGOU msg '{top_data['content']}' de P{top_sender} com TS {top_ts}"
            print(log)
            delivery_log.append(log)
        else:
            break

# ==============================================================================
# TAREFA 2: EXCLUSÃO MÚTUA (Ricart-Agrawala)
# ==============================================================================

@app.route('/mutex/request', methods=['POST'])
def mutex_request():
    global mutex_state, mutex_acks
    mutex_state = "WANTED"
    mutex_acks = 1 
    
    # Envia pedido a todos com timestamp
    ts = increment_clock()
    req_data = {'ts': ts, 'sender': PROCESS_ID}
    
    threading.Thread(target=broadcast, args=('/mutex/receive_req', req_data)).start()
    
    # Espera OK de todos
    while mutex_acks < NUM_PROCESSES:
        time.sleep(0.1)
    
    mutex_state = "HELD"
    print(f"Process {PROCESS_ID} ENTROU na Seção Crítica")
    time.sleep(3)
    print(f"Process {PROCESS_ID} SAIU da Seção Crítica")
    
    mutex_release()
    return jsonify({"status": "executed_cs"})

@app.route('/mutex/receive_req', methods=['POST'])
def mutex_receive_req():
    # Lógica de decisão
    data = request.json
    req_ts = data['ts']
    req_sender = data['sender']
    update_clock(req_ts)
    
    my_ts = get_clock()
    reply = False
    
    if mutex_state == "HELD":
        reply = False
    elif mutex_state == "WANTED":
        # Desempate pelo menor timestamp, depois pelo menor ID
        if (req_ts < my_ts) or (req_ts == my_ts and req_sender < PROCESS_ID):
             reply = True
        else:
             reply = False
    else: 
        reply = True
        
    if reply:
        send_mutex_reply(req_sender)
    else:
        # Adiciona à fila se não responder agora
        mutex_queue.append(req_sender)
    
    return jsonify({"status": "processed"})

def send_mutex_reply(target_id):
    # Adapta a URL de resposta baseado se é local ou K8s
    if IS_K8S:
        host = f"app-{target_id}.app-service"
        port = 5000
    else:
        host = "localhost"
        port = 5000 + target_id
        
    try:
        requests.post(f"http://{host}:{port}/mutex/reply_ok", json={'sender': PROCESS_ID})
    except: pass

@app.route('/mutex/reply_ok', methods=['POST'])
def mutex_reply_ok():
    global mutex_acks
    mutex_acks += 1
    return jsonify({"status": "ack_received"})

def mutex_release():
    global mutex_state
    mutex_state = "RELEASED"
    # Responde a todos na fila
    while mutex_queue:
        requester = mutex_queue.pop(0)
        send_mutex_reply(requester)

# ==============================================================================
# TAREFA 3: ELEIÇÃO (Bully)
# ==============================================================================

@app.route('/election/start', methods=['POST'])
def start_election():
    global election_in_progress
    election_in_progress = True
    print(f"Process {PROCESS_ID} iniciou eleição.")
    
    # Envia para IDs maiores
    higher_processes = [p for p in range(NUM_PROCESSES) if p > PROCESS_ID]
    
    if not higher_processes:
        become_coordinator()
        return jsonify({"result": "I am coordinator"})
    
    answered = False
    for p in higher_processes:
        if IS_K8S:
            host = f"app-{p}.app-service"
            port = 5000
        else:
            host = "localhost"
            port = 5000 + p

        try:
            r = requests.post(f"http://{host}:{port}/election/msg", json={'sender': PROCESS_ID}, timeout=1)
            if r.status_code == 200:
                answered = True
        except: pass
            
    if not answered:
        become_coordinator()
    
    return jsonify({"status": "election_running"})

@app.route('/election/msg', methods=['POST'])
def receive_election_msg():
    sender = request.json['sender']
    # Se recebe de ID menor, assume eleição
    if sender < PROCESS_ID:
        threading.Thread(target=start_election).start()
        return jsonify({"status": "OK"}), 200
    return jsonify({"status": "ignored"}), 200

def become_coordinator():
    global coordinator_id, election_in_progress
    coordinator_id = PROCESS_ID
    election_in_progress = False
    print(f"Process {PROCESS_ID} virou COORDENADOR!")
    
    for i in range(NUM_PROCESSES):
        if i == PROCESS_ID: continue
        if IS_K8S:
            host = f"app-{i}.app-service"
            port = 5000
        else:
            host = "localhost"
            port = 5000 + i
            
        try:
            requests.post(f"http://{host}:{port}/coordinator", json={'coord': PROCESS_ID})
        except: pass

@app.route('/coordinator', methods=['POST'])
def set_coordinator():
    global coordinator_id, election_in_progress
    coordinator_id = request.json['coord']
    election_in_progress = False
    print(f"Novo coordenador: Process {coordinator_id}")
    return jsonify({"status": "ok"})

@app.route('/status', methods=['GET'])
def status():
    return jsonify({
        "id": PROCESS_ID,
        "clock": logical_clock,
        "mutex_state": mutex_state,
        "coordinator": coordinator_id,
        "logs": delivery_log[-5:]
    })

if __name__ == '__main__':
    # Roda na porta calculada (5000, 5001, 5002)
    app.run(host='0.0.0.0', port=MY_PORT)