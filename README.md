# Algoritmos de Coordenação em Sistemas Distribuídos
## Sincronização e Eleição


**Autor(a):** Luisa M. G. Mathias

**Disciplina:** Sistemas Distribuídos (DCA3704)

**Curso:** Engenharia da Computação

**Instituição:** Universidade Federal do Rio Grande do Norte (UFRN)

O sistema consiste em uma aplicação Python orquestrada via **Kubernetes**, projetada para rodar no **Google Cloud Shell**.


## Algoritmos Implementados

1.  **Multicast com Ordenação Total (Total Order):**
    * Utiliza *Relógios Lógicos de Lamport* e *Filas de Prioridade* para garantir que todos os nós processem mensagens na mesma ordem.
    * Consistência garantida via mecanismo de ACKs de todos os processos.

2.  **Exclusão Mútua Distribuída:**
    * Algoritmo de *Ricart-Agrawala*.
    * Garante acesso exclusivo a uma Região Crítica sem necessidade de um coordenador central (ponto único de falha).

3.  **Eleição de Líder:**
    * Algoritmo do *Valentão (Bully)*.
    * Elege o processo com maior ID como coordenador do sistema.

---

## Como Executar (Google Cloud Shell)

### 1. Inicializar o Ambiente
No terminal do Cloud Shell, inicie o Minikube:

```bash
minikube start
````

### 2. Configurar o Docker

Aponte o terminal para usar o Docker interno do Minikube (essencial para o Kubernetes enxergar a imagem):

```bash
eval $(minikube docker-env)
```

### 3. Construir a Aplicação

Crie a imagem Docker localmente:

```bash
docker build -t distributed-app:latest .
```

### 4. Deploy no Kubernetes

Aplique a configuração para criar os 3 pods (réplicas):

```bash
kubectl apply -f deployment.yaml
```

Aguarde até que todos estejam com status `Running`:

```bash
kubectl get pods -w   # Pressione Ctrl+C para sair
``` 

-----

## Roteiro de Testes (Demonstração)

Abra o Cloud Shell para executar os comandos a seguir.

### Teste 1: Multicast (Ordenação Total)

Envia uma mensagem para o Processo 0. Ela deve ser replicada para 1 e 2 e entregue ordenadamente.

```bash
kubectl exec app-0 -- curl -X POST -H "Content-Type: application/json" -d '{"msg": "Teste Cloud Shell"}' http://localhost:5000/multicast/send
```

**Verificação:** Confira os logs de qualquer pod para ver a mensagem de entrega:

```bash
kubectl logs app-0
kubectl logs app-1
kubectl logs app-2
```

### Teste 2: Exclusão Mútua (Ricart-Agrawala)

O Processo 0 solicita acesso à Região Crítica.

```bash
kubectl exec app-0 -- curl -X POST http://localhost:5000/mutex/request
```

**Resultado nos logs:** Você verá "ENTROU na Seção Crítica", uma pausa de 3 segundos e "SAIU da Seção Crítica".

### Teste 3: Eleição de Líder (Bully)

Força o Processo 0 (menor ID) a iniciar uma eleição. O esperado é que o Processo 2 (maior ID) vença.

```bash
kubectl exec app-0 -- curl -X POST http://localhost:5000/election/start
```

**Verificação:**

```bash
kubectl exec app-0 -- curl http://localhost:5000/status    # O campo "coordinator" deve ser 2
```

-----

## Tecnologias

  * **Python 3.9** (Flask, Threading, Heapq)
  * **Kubernetes** (StatefulSet, Headless Service)
  * **Minikube** (Ambiente local de K8s)
  * **Docker**

## Referências

  * Tanenbaum, A. S., & Van Steen, M. (2025). *Distributed Systems* (4ª Ed.).
  * Slides da disciplina de Sistemas Distribuídos - Capítulo 5: Coordenação.
