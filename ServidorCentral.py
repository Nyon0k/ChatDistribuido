#-*- encoding: utf-8

import json, socket, threading, select, sys

''' 
Servidor Central do Chat Distribuído
'''

class ServidorCentral:
    # Parâmetros da classe
    
    # HashMap (dicionário) para armazenar informações dos usuários online (lista de usuários)
    usuariosOnline = {}       # Estrutura: {username: {Endereco: 'IP', Porta: 'porta' } } 
    
    # HashMap (dicionário) para armazenar usuarios ativos (não fantasmas, aqueles que sairam sem deslogar)
    usuariosAtivos = {}       # Estrutura inversa: {endereco: username}
    
    # Lock para evitar condições de corrida nos dicionários acima
    lock = threading.Lock()   
    
    # Lista que armazenam as threads de cada usuario do sistema
    threads_usuarios = []     
        
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
        print("Porta em escuta: " + str(self.PORTA))
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
            4. kill <user>: Desloga um usuario online no servidor \n \
            5. exit: Encerra o servidor. (!) Se houver usuários online, são todos deslogados")
    
    # Método usado para deslogar um usuario no Servidor a partir de seu username e evitar fantasmas #
    def killUser(self, comando):
        # Captura nome de usuario na linha de comando
        usuario = comando[5:]
        # Caso nada tenha sido digitado na linha de comando, então dê input
        if len(usuario) == 0:   usuario = input("Digite o nome do usuario: ")
        # Se o usuario estiver online, então deslogue ele        
        infoUsuario = ServidorCentral.usuariosOnline.get(usuario)
        if infoUsuario:
            self.deslogarUsuario(usuario, (infoUsuario["Endereco"],infoUsuario["Porta"]))
        else:
            print("Usuário " + '@'+usuario + " não online")
                
    # Método Shutdown do Servidor, para encerrar as threads e o socket de aceita conexões em PORTSC #
    def quit(self):
        for thread_usuario in ServidorCentral.threads_usuarios: # aguarda todas as threads terminarem
            thread_usuario.join()
            print("Thread " + str(thread_usuario) + " Encerrada")
        self.sock.close()
        
    # Método (start) principal do Servidor ( inicia o processamento dele ) #
    # // Chama o aceitarConexoes (acima), que designa threads para atender cada requisição de cada conexão feita
    # // E lida (handler) com os comandos da entrada padrão (stdin)
    def start(self): 
        print("Digite 'comandos' para saber os comandos do Servidor")
        while True:
            leitura, escrita, excecao = select.select(self.entradas, [], [])
            for entrada in leitura:
                # Entrada vindo do socket
                if entrada == self.sock:
                    clisock, endereco = self.aceitarConexoes()
                    print("Aguardando requisições de " + str(endereco))
                    usuario_onthread = threading.Thread(target = self.atenderRequisicoes, args = (clisock, endereco))
                    usuario_onthread.start()
                    ServidorCentral.threads_usuarios.append(usuario_onthread) 
                # Entrada vindo da linha de comando
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
                    elif comandoEntrada == '':
                        pass
                    elif comandoEntrada.split()[0] == "kill":
                        self.killUser(comandoEntrada)                        
                    elif comandoEntrada == "exit":
                        self.quit()
                        sys.exit()

    # Método executado pelas threads para atender (handler) as requisições de cada cliente #
    # // Entrada: O socket do cliente, no qual as threads executam o receive para receber dados simultaneamente e o endereco deles
    def atenderRequisicoes(self, clisock, endereco):
        while True:
            # Verifica se os clientes enviam dados
            tamMsgBytes = clisock.recv(2)                                   # Recebe os 2 primeiros bytes, que determinam o tamMensagem   
            if not tamMsgBytes:                                             # Se não receber, então 
                usuario = ServidorCentral.usuariosAtivos.get(endereco[0])   # verifique se o usuario está ativo
                if usuario: self.deslogarUsuario(usuario, endereco)         # caso esteja, deslogue
                clisock.close()                                             # feche o socket
                # faltou tirar a thread da lista de threads
                return                                                      # feche a thread
            
            # Caso contrário, isto é, o servidor receba
            tamMsgInt = int.from_bytes(tamMsgBytes, "big")   # Converte para inteiro BigEndian
            
            # linha de baixo comentada, pois da erro receber receber dados por chunks de alguns clientes 
            # dados = self.ChunksRecebidosToMsg(tamMsgInt, clisock) 
            
            # Recebe os dados dos clientes
            bytesRecebidos = clisock.recv(tamMsgInt + 1024)                 # Recebe o tamanho da Mensagem + 1KB de auxílio           
            dados = bytesRecebidos.decode("utf-8")              

            # Tenta fazer o handler das requisições
            try:                                                            
                dadosJSON = json.loads(dados)                               # Carrega a mensagem num dicionário (HashMap)
                operacao = dadosJSON["operacao"]                            # Extrai a chave de operação e verifica que tipo de operacao é
                
                if operacao == "login":                     
                    username = dadosJSON["username"]
                    status, mensagem = self.registrarUsuarioON(username, endereco, dadosJSON["porta"])
                elif operacao == "logoff":
                    username = dadosJSON["username"]
                    status, mensagem = self.deslogarUsuario(username, endereco)   
                elif operacao == "get_lista":
                    status, mensagem = self.getUsuariosOnline()
                else: # Se o cliente tiver tratamento de erro quanto a operacao a ser enviada, essa condição nunca roda
                    print("Comando inválido recebido de ", clisock)
                    
                # Método único para enviar a resposta de cada conexão
                self.enviarResposta(clisock, operacao, status, mensagem) # Envia as respostas de cada requisição
            
            # Caso dê algum erro
            except:
                usuario = ServidorCentral.usuariosAtivos.get(endereco[0])
                if usuario:                                 # Verifica se o usuario está ativo no Servidor Central
                   print("Erro no recebimento de dados de " + usuario + " no endereco " + endereco[0] + " na porta " + str(endereco[1])  )
                   self.deslogarUsuario(usuario,endereco)   # desloga ele
                # Printa os dados que foram recebidos
                print("# ------ Dados recebidos com erro ------ #")
                print(dados)
                print("# -------------------------------------- #")
                clisock.close()                             # fecha a conexão
                return                                      # mata a thread 
            
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
            
            ServidorCentral.usuariosAtivos[endereco[0]] = username
            
            ServidorCentral.lock.release()
            # Fim da condição de corrida
            return (200, "Login com sucesso")
        return(400, "Username em Uso")
                    
    # Método que desregistra um usuário online devido ao evento (requisição) de logoff #
    # // Entrada: Username a ser deslogado, Socket e Endereco desse cliente
    # // Saída: Tupla contendo o (status, mensagem) da operação 
    def deslogarUsuario(self, username, endereco):
        if ServidorCentral.usuariosOnline.get(username):
            # Condição de corrida
            ServidorCentral.lock.acquire()
            
            del ServidorCentral.usuariosOnline[username]
            del ServidorCentral.usuariosAtivos[endereco[0]]
            print("@" + username + " desconectado")
                    
            ServidorCentral.lock.release()
            # Fim da condição de corrida
            return (200, "Logoff com sucesso")
        return (400, "Erro no Logoff")
    
    # Método que retorna a lista de usuarios online #
    def getUsuariosOnline(self):
        clientes = ServidorCentral.usuariosOnline # vai sempre funcionar
        return (200, clientes)
    
    # Método único de envio de respostas para as requisições feitas do usuário #
    # // Entrada: Socket do cliente, operacao realizada, status da operação e mensagem
    def enviarResposta(self, clisock, operacao, status, mensagem):
        resposta_usuario = {
            "operacao": operacao, 
            "status": status,
        }
        if operacao != "get_lista": resposta_usuario["mensagem"] = mensagem
        else: resposta_usuario["clientes"] = mensagem
        respostaJSON = json.dumps(resposta_usuario)
        
        resposta = self.msgToBytes(respostaJSON)
        clisock.sendall(resposta)
    
    # Métodos auxiliares #

    # Método para converter a msg em bytes #
    # // Entrada: Uma string Msg a ser convertida em bytes
    # // Saída: 2 bytes (formato BigEndian) no inicio indicando o tamanho de Msg (+) concatenado com (+) a mensagem em bytes
    def msgToBytes(self, msg):
        tamanhoMsg = len(msg)   
        tamMsgBytes = tamanhoMsg.to_bytes(2, "big")         # Tamanho da mensagem convertido em 2 bytes BigEndian
        #msg2Bytes = bytes(msg, "utf-8")
        msgInBytes = msg.encode("utf-8")                    # String Mensagem em bytes
        return tamMsgBytes + msgInBytes                     # Concatena dois Bytes pelo operador + da classe Bytes

    # Método usado para receber chunks e converter em mensagem (string) #
    # // Entrada: O tamanho da Msg a ser recebida e o socket pelo qual será recebida
    # // Saída: Uma string msg decodificada dos bytes recebidos em pieces (chunks)
    def ChunksRecebidosToMsg(self, TamMsg, socket):
        minBuffer = 10                                      # buff mínimo de 10 bytes p/ garantir que seja todo preenchido
        chunksRecebidos = socket.recv(TamMsg)               # Recebe o buffer do tamanho da mensagem
        msg = chunksRecebidos.decode("utf-8")               # Decodifica os bytes dessa informação em String 
        while len(msg) < TamMsg:                            # Verifica se o tamanho da String é menor que o tamanho da mensagem
            chunksRecebidos = socket.recv(minBuffer)        # Caso seja, recebe a mensagem em partes de 10 bytes cada
            #print("Recebidos : " + str(len(msg)))
            msg += chunksRecebidos.decode("utf-8")          # Vai decodificando e inserindo na string msg recebida
                   
        return msg                                          # retorna a mensagem 
    
# Função principal do Servidor #
def main():
    HOSTSC = ''                                             # Setar HOST ServidorCentral
    PORTASC = 9000                                          # Setar PORTA ServidorCentral
    nConexoes = 3
    servidor = ServidorCentral(HOSTSC, PORTASC, nConexoes)
    servidor.start()
    
if __name__ == "__main__":
    main()
