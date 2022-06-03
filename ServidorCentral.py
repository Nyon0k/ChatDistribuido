#-*- encoding: utf-8

import json, socket, threading, select, sys

''' 
Servidor Central do chat distribuído
'''

class ServidorCentral:
    # Parâmetros da classe
    usuariosOnline = {}       # HashMap (dicionário) que armazena info dos usuários online
    lock = threading.Lock()   # Lock para evitar condições de corrida no dicionário acima
    
    # Construtor da classe #
    # // Entrada: Um HOST e PORTA para aguardar conexões e o número de Conexões possíveis
    def __init__(self, HOST, PORTA, nConexoes):
        self.HOST = HOST
        self.PORTA = PORTA
        self.nConexoes = nConexoes
        
        # Inclui (stdin - Entrada padrão) na lista de entradas a ser selecionada enquanto
        self.entradas = [sys.stdin] # aguarda o processamento I/O (entrada e saída dos sockets)
        self.aguardarConexoes()
        
    # Método que inicia o socket para aguardar conexões #
    def aguardarConexoes(self):
        self.sock = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.sock.bind((self.HOST, self.PORTA))
        print("Servidor Central aguardando conexões...")
        self.sock.listen(self.nConexoes)
        self.sock.setblocking(False)
        self.entradas.append(self.sock) # 

    # Método que aceita as conexões #
    def aceitarConexoes(self):
        cliSock, endereco = self.sock.accept()
        print("Conectado com: ", endereco)
        return (cliSock, endereco)
        
    # Método que exibe os comandos do servidor #
    def exibirComandos(self):
        print("Comandos aceitos: \n \
            1. info: Informações sobre o servidor \n \
            2. get_lista: Lista usuários online \n \
            3. comandos: Exibir comandos \n \
            4. exit: Encerra o servidor. (!) Se houver usuários online, são todos deslogados")
        
    # Método (start) principal do Servidor ( inicia o processamento dele ) #
    # // Chama o aceitarConexoes (acima), que designa threads para atender cada requisição de cada conexão feita
    # // E lida (handler) com os comandos da entrada padrão (stdin)
    def start(self): 
        print("Digite 'comandos' para saber os comandos do Servidor")
        while True:
            leitura, escrita, excecao = select.select(self.entradas, [], [])
            for entrada in leitura:
                if entrada == self.sock:
                    clisock, endereco = self.aceitarConexoes()
                    print("Aguardando requisições de " + str(endereco))
                    usuario_onthread = threading.Thread(target = self.atenderRequisicoes, args = (clisock, endereco))
                    usuario_onthread.start()
                elif entrada == sys.stdin:
                    comandoEntrada = input()
                    if comandoEntrada == "info":
                        print("Host: " + str(self.HOST) + '\n' + "Porta: " + str(self.PORTA) + '\n' + "Nº conexões possíveis: " + str(self.nConexoes))
                    elif comandoEntrada == "get_lista":
                        if not ServidorCentral.usuariosOnline: print("Nenhum usuário online")
                        for usuario in ServidorCentral.usuariosOnline:
                            print(usuario)
                    elif comandoEntrada == "comandos":
                        self.exibirComandos()
                    elif comandoEntrada == "exit":
                        # Precisa implementar o deslogamento de todos os usuários online, que provavelmente tem haver com o encerramento de threads (join)
                        # Ele desliga o servidor, mas as threads ativas continuam rodando. Tem que resolver isso
                        self.sock.close()
                        exit(1)

    # Método executado pelas threads para atender (handler) as requisições de cada cliente #
    # // Entrada: O socket do cliente, no qual as threads executam o receive para receber dados simultaneamente e o endereco deles
    def atenderRequisicoes(self, clisock, endereco):
        while True:
            bytesRecebidos = clisock.recv(1024)
            dados = str(bytesRecebidos, "utf-8")
            dadosJSON = json.loads(dados)
            operacao_usuario = dadosJSON["operacao"]
            if operacao_usuario == "login":
                username_usuario = dadosJSON["username"]
                status, mensagem = self.registrarUsuarioON(username_usuario, endereco, dadosJSON["porta"])
            elif operacao_usuario == "logoff":
                username_usuario = dadosJSON["username"]
                status, mensagem = self.deslogarUsuario(username_usuario)
            elif operacao_usuario == "get_lista":
                status, mensagem = self.getUsuariosOnline()
            else: # Se o cliente tiver tratamento de erro quanto as requisições, essa condição nunca roda
                print("Comando inválido recebido de ", clisock)
            
            self.enviarResposta(clisock, operacao_usuario, status, mensagem) # Envia as respostas de cada requisição
           
    # Abaixo os Event Handlers para cada operação requisitada #
    
    # Método que registra um usuário online devido ao evento (requisição) de login #
    # // Entrada: Username, endereco e porta do usuario
    # // Saída: Tupla contendo o (status, mensagem) da operacao (evento) requisitado
    def registrarUsuarioON(self, username, endereco, porta):
        if not ServidorCentral.usuariosOnline.get(username):
            # Condição de corrida
            ServidorCentral.lock.acquire()
            ServidorCentral.usuariosOnline[username] = {
                "Endereco": endereco[0], "Porta": str(porta)
                }
            print("@" + username + " conectado")
            ServidorCentral.lock.release()
            # Fim da condição de corrida
            return (200, "Login com sucesso")
        return(400, "Username em Uso")
                    
    # Método que desregistra um usuário online devido ao evento (requisição) de logoff #
    # // Entrada: Username a ser deslogado
    # // Saída: Tupla contendo o (status, mensagem) da operação 
    def deslogarUsuario(self, username):
        if ServidorCentral.usuariosOnline.get(username):
            # Condição de corrida
            ServidorCentral.lock.acquire()
            del ServidorCentral.usuariosOnline[username]
            print("@" + username + " desconectado")
            ServidorCentral.lock.release()
            # Fim da condição de corrida
            return (200, "Logoff com sucesso")
        return (400, "Erro no Logoff")
    
    # Método que #
    def getUsuariosOnline(self):
        clientes = ServidorCentral.usuariosOnline # vai sempre funcionar
        return (200, clientes)
    
    # Método #
    def enviarResposta(self, clisock, operacao, status, mensagem):
        resposta_usuario = {
            "operacao": operacao, 
            "status": status,
        }
        if operacao != "get_lista": resposta_usuario["mensagem"] = mensagem
        else: resposta_usuario["clientes"] = mensagem
        respostaJSON = json.dumps(resposta_usuario)
        respostaBytes = bytes(respostaJSON, "utf-8")
        clisock.sendall(respostaBytes)
    
# Função principal do Servidor #
def main():
    HOSTSC = '192.168.0.66'
    PORTASC = 9000
    nConexoes = 3
    servidor = ServidorCentral(HOSTSC, PORTASC, nConexoes)
    servidor.start()
    
if __name__ == "__main__":
    main()
