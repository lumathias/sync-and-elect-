# Algoritmos de Coordenação em Sistemas Distribuídos
## Sincronização e Eleição


**Autor(a):** Luisa M. G. Mathias

**Disciplina:** Sistemas Distribuídos (DCA3704)

**Curso:** Engenharia da Computação

**Instituição:** Universidade Federal do Rio Grande do Norte (UFRN)

---

Este projeto apresenta a implementação prática de algoritmos fundamentais de coordenação em sistemas distribuídos, desenvolvidos em **Python** com **Flask**. O sistema foi projetado para rodar tanto localmente quanto em ambientes orquestrados com **Kubernetes**.

O projeto cobre três tópicos principais do Capítulo 5 (Coordenação) da disciplina de Sistemas Distribuídos: **Multicast com Ordenação Total**, **Exclusão Mútua Distribuída** e **Eleição de Líder**.

## Funcionalidades Implementadas

### 1. Multicast com Ordenação Total (Total Order Multicast)
Utiliza **Relógios Lógicos de Lamport** para garantir que todas as mensagens sejam entregues na mesma ordem em todos os processos.
- **Teoria:** As mensagens carregam um timestamp lógico. A entrega só ocorre quando a mensagem está no topo da fila de prioridade local e foi reconhecida (ACK) por todos os processos do grupo.
- **Mecanismo:** Fila de prioridade (`heapq`) e contador de ACKs.

### 2. Exclusão Mútua Distribuída (Algoritmo de Ricart-Agrawala)
Implementação do algoritmo distribuído onde um processo precisa da permissão de todos os outros para acessar um recurso crítico.
- **Teoria:** Baseada em relógios lógicos. Quando um processo quer acessar o recurso, envia um pedido com timestamp a todos. Se houver conflito, o processo com menor timestamp ganha prioridade (desempate pelo ID).
- **Vantagem:** Evita ponto único de falha (diferente do algoritmo centralizado).

### 3. Eleição de Líder (Algoritmo do Valentão / Bully)
Algoritmo para eleger um coordenador quando o atual falha ou o sistema inicia.
- **Teoria:** Assume-se que os processos têm identificadores únicos. O processo com o **maior identificador** sempre vence a eleição.
- **Fluxo:** Um processo envia mensagem de eleição para todos com ID maior. Se ninguém responder, ele se torna o líder.

---

## Tecnologias Utilizadas

- **Linguagem:** Python 3.9
- **API:** Flask
- **Containerização:** Docker
- **Orquestração:** Kubernetes (StatefulSet)
- **Ferramentas:** Minikube (Cluster Local), cURL (Testes de API)

---

## Executando Localmente (VS Code)

Para testes rápidos sem necessidade de subir um cluster Kubernetes.

1. **Instale as dependências:**
    ```bash
     pip install -r requirements.txt
    ````

2.  **Inicie os 3 processos em terminais separados:**

    *Terminal 1:*

    ```bash
      python app.py 0   # Roda em localhost: 5000
    ```

    *Terminal 2:*

    ```bash
      python app.py 1   # Roda em localhost: 5001
    ```

    *Terminal 3:*

    ```bash
      python app.py 2 # Roda em localhost:5002
    ```

-----

## Executando no Kubernetes (Google Cloud Shell / Minikube)

1.  **Inicie o Minikube:**

    ```bash
      minikube start
    ```

2.  **Configure o Docker e construa a imagem:**

    ```bash
      eval $(minikube docker-env)
      docker build -t distributed-app: latest .
    ```

3.  **Faça o Deploy:**

    ```bash
      kubectl apply -f k8s/deployment.yaml
    ```

4.  **Verifique os Pods:**

    ```bash
      kubectl get pods -w   # Aguarde app-0, app-1 e app-2 estarem "Running"
    ```
-----

## Testando a API (Exemplos de Uso)

Você pode usar o `curl` (ou Postman) para interagir com o sistema.

### Teste de Multicast (Ordenação Total)

Envia uma mensagem para o Processo 0, que será replicada para 1 e 2.

```bash
  # Local
  curl -X POST -H "Content-Type: application/json" -d '{"msg": "Ola SD"}' http://localhost:5000/multicast/send
  
  # Kubernetes (executando de dentro do pod)
  kubectl exec app-0 -- curl -X POST -H "Content-Type: application/json" -d '{"msg": "Ola K8s"}' http://localhost:5000/multicast/send
```

### Teste de Exclusão Mútua

Solicita acesso à Região Crítica para o Processo 0.

```bash
  # Local
  curl -X POST http://localhost:5000/mutex/request
  
  # Kubernetes
  kubectl exec app-0 -- curl -X POST http://localhost:5000/mutex/request
```

### Teste de Eleição (Bully)

Força o Processo 0 (menor ID) a iniciar uma eleição. O esperado é que o Processo 2 (maior ID) vença.

```bash
  # Local
  curl -X POST http://localhost:5000/election/start
  
  # Kubernetes
  kubectl exec app-0 -- curl -X POST http://localhost:5000/election/start
```

-----

## Referências

  * Tanenbaum, A. S., & Van Steen, M. (2025). *Distributed Systems* (4ª Ed.).
  * Slides da disciplina de Sistemas Distribuídos - Capítulo 5: Coordenação.
