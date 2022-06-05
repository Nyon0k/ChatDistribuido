# -*- enconding: utf-8

import socket, json, sys, select, threading, random
import RichTextOnTerminal

'''
Usuario final do chat distribuído - A classe têm três funcionalidades:
1. Comunicação com Servidor Central, enviando requisições e recebendo respostas
2. Interfaceamento com usuário final, através do processamento de comandos de entrada
3. Comunicação P2P com outros usuários finais disponíveis (online) no Servidor Central
'''

class Usuario:
    # Parâmetros da classe
    
    # HashMap (dict) para armazenar informações dos peers conectados
    # Estrutura do dict: {username : { "socket": SOCKET, "cor": COR} }
    peersConectados = {} # username é uma chave e o valor associado é outro dict com chaves SOCKET e COR
    lock = threading.Lock()   # Lock para evitar condições de corrida no dicionário acima (peersConectados)
    Logado = False  # Variável booleana que guarda o estado do usuario quanto ao login no SC. Online = True, Off = False
    
    # Construtor da Classe
    # // Entrada: Um host,porta,nConexoes para aceitar peers e HOSTSC,PORTASC do Servidor Central (para requisições)
    def __init__(self, host, porta, nConexoes, HOSTSC, PORTASC):
        self.host = host
        self.porta = porta
        self.nConexoes = nConexoes
        
        self.hostsc = HOSTSC
        self.portasc = PORTASC
        
        self.username = ""  # nickname (ou username) ativo no Servidor Central
        
        self.usuariosOnline = {} # HashMap (dicionário) que armazena a lista de usuários online (resposta do SC)
        
        # socket que faz a comunicação com Servidor Central, para enviar e receber requisições através dele
        self.sockServidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  
        # socket que se mantêm em modo passivo, atuando como servidor de peers (outros usuarios que queiram se conectar)
        self.sockPassivo_p2p = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    
        self.cor = RichTextOnTerminal.RichTextOnTerminal()  # instância rich text (deixa o texto mais rico)
        self.entradas = [sys.stdin] # Inclui o stdin na lista de entradas que aguardam I/O do socket
    
    # ---------------------------------- Funcionalidade 1. Comunicação com Servidor Central ---------------------------------- #
    
    # Faz a conexão da aplicação do usuário final com Servidor Central #
    def conectarServCentral(self):
        return self.sockServidor.connect((self.hostsc, self.portasc))
    
    # Faz a requisição de login no Servidor Central sob o nickname (username) definido #
    def requisitarLogin(self):
        requisicao_servidor = {
            "operacao": "login",
            "username": self.username,
            "porta": self.porta
        }
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sockServidor.sendall(bytesEnviados)
        self.receberResposta()
        
    # Faz a requisição de logoff no Servidor Central sob o username atual, permitindo trocá-lo #
    def requisitarLogoff(self):
        requisicao_servidor = {
            "operacao": "logoff",
            "username": self.username
        }
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sockServidor.sendall(bytesEnviados)
        self.receberResposta()
    
    # Faz a requisição da lista de usuários online (disponíveis) para iniciar uma conversa #
    def requisitarLista(self):
        requisicao_servidor = {"operacao": "get_lista"}
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sockServidor.sendall(bytesEnviados)
        self.receberResposta()
    
    # Método único que recebe e imprime a resposta (p/ usuário final) de cada requisição acima # 
    def receberResposta(self):
        bytesRecebidos = self.sockServidor.recv(1024)
        dados = str(bytesRecebidos, "utf-8")
        dadosJSON = json.loads(dados)
        operacao = dadosJSON["operacao"]
        status = dadosJSON["status"]
        resposta = ""
        if status == 200:
            resposta += self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado()
            if operacao == "login":
                Usuario.Logado = True
            elif operacao == "logoff":
                Usuario.Logado = False
        else:
            resposta += self.cor.tvermelho() + self.cor.tnegrito() + self.cor.tsublinhado()
        if operacao != "get_lista":
            mensagem = dadosJSON["mensagem"]
            resposta += mensagem + self.cor.end()
            print(self.cor.tverde() + "Operação: " + self.cor.end() + operacao + '\n' + self.cor.tverde() + "Status: " + self.cor.end() + str(status) + '\n' 
            + self.cor.tverde() + "Mensagem: " + self.cor.end() + resposta)
        else:
            clientes = dadosJSON["clientes"]
            self.usuariosOnline = clientes
            print(self.cor.tverde() + self.cor.tsublinhado() + "Usuários online: "+ self.cor.end())
            for cliente in clientes:
                print('\t' + self.cor.tciano() + '@' + cliente + self.cor.end())
                
    # ---------------------------------- Funcionalidade 2. Interface com usuário final ---------------------------------- #   
    
     # Método (start) que inicia a aplicação (interface com usuário) #
    def start(self):
        print(self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado() + " Bem vindo ao Chat Distribuído !" + self.cor.end() )
        self.definirUsername('')    # chama com parâmetro vazio, pois nenhum username é passado na linha de comando
        self.conectarServCentral()
        
        print("Digite " + self.cor.tazul() + "@menu" + self.cor.end() + " para saber os comandos")
        
        self.aguardaConexoes_p2p() # Coloca o sockPassivo em modo de escuta para aguardar conexões dos pares (peers)
        self.entradas.append(self.sockPassivo_p2p) # Inclui o sockPassivo do peer na lista de entradas selecionadas enquanto aguarda I/O
        
        clientes_p2p = []
        while True:
            leitura, escrita, excecao = select.select(self.entradas, [], [])
            for entrada in leitura:
                if entrada == self.sockPassivo_p2p:
                    novoSock_p2p, endereco = self.aceitarConexoes_p2p()
                    peerThread = threading.Thread(target = self.receberMensagem_p2p, args = (novoSock_p2p, endereco))
                    peerThread.start()
                    clientes_p2p.append(peerThread)
                elif entrada == sys.stdin:
                    comando = input()
                    if comando == "@menu":
                        print(self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado() + "MENU DE COMANDOS\n" + self.cor.end() + self.exibirMenu())
                    elif comando.split()[0] == "@nick":
                        self.definirUsername(comando)
                    elif comando == "@exit":
                        for c in clientes_p2p:   ##aguarda todas as threads terminarem
                            c.join()
                            print("Thread "+str(c)+" Encerrada")
                        self.sockPassivo_p2p.close()
                        exit(1)
                        # ToDO: Implementar o encerramento da aplicação. A classe Usuario tem threads executando somente o receberMensagem_p2p
                        # que são postas em execução quando: 
                        # 1. A lista de entradas do select recebe processamento do sockPassivo_p2p. Disso, 1 thread é dada ao peer que se conecta
                        # 2. Na 1º vez que um usuario manda mensagem para outro, ele roda o conecta_p2p que cria 1 thread para executar receberMensagem_p2p
                        # Algo tem que ser feito algo para encerrar corretamente essas threads
                    elif comando == "@login":
                        self.requisitarLogin()
                    elif comando == "@logoff":
                        self.requisitarLogoff()
                    elif comando == "@get_lista":
                        self.requisitarLista()
                    elif comando == "": # Esse comando vazio é para prevenir um erro quanto ao split
                        pass
                    elif comando == "@conectados":
                        # ToDo : Implementar para imprimir informações de todos os peers conectados ao chat#
                        # Informações que valem ser impressas: IP, PORTA, ... 
                        print(Usuario.peersConectados) 
                        print(Usuario.peersConectados.keys()) 
                    elif comando.split()[0] == "@info":
                        if self.info(comando) < 0: continue
                    elif comando[0] == "@":
                        if self.conecta_p2p(comando) < 0: continue
                    else:
                        print(self.cor.tnegrito() + self.cor.tvermelho() + "COMANDO DE ENTRADA INVÁLIDO !" + self.cor.end())
    
    # Imprime o Menu de comandos #
    def exibirMenu(self):
        return(self.cor.tsublinhado() + "Comandos aceitos:\n" + self.cor.end() + 
            self.cor.tazul() + " 1. @menu: " + self.cor.end() + "Exibe o menu de comandos.\n"+
            self.cor.tazul() + " 2. @nick <Nickname>: " + self.cor.end() + "Define um Nickname para entrar online. \n" + 
            "\t(!) Se não for passado <Nickname>, chama um input\n" +
            self.cor.tazul() + " 3. @exit: " + self.cor.end() + "Encerra aplicação.\n\t(!) Se houver conexões (com ServidorCentral ou P2P) encerra.\n"+
            self.cor.tazul() + " 4. @login: " + self.cor.end() + "Faz requisição de login sob o Nickname de entrada da aplicação.\n"+
            self.cor.tazul() + " 5. @logoff: " + self.cor.end() + " Faz logoff no Nickname, permitindo o usuario escolher outro.\n"+
            self.cor.tazul() + " 6. @get_lista: " + self.cor.end() + "Requisita e recebe a lista de usuários online.\n"+
            self.cor.tazul() + " 7. @conectados: " + self.cor.end() + "Imprime informação dos peers conectados ao chat. \n"+
            self.cor.tazul() + " 8. @info <Username>: " + self.cor.end() + "Imprime info de um usuario especifico online.\n " +
            "\t(!) Se não for passado <Username> imprime do próprio <Nickname>.\n\n" + 
            self.cor.tsublinhado() + "Para enviar mensagem: \n" + self.cor.end() +  self.cor.tazul() + 
            "\t@get_lista" + self.cor.end() + ": Para atualizar a lista e ter os peers online" + self.cor.tazul() +
            "\n\t@peer MSG" + self.cor.end() + ", onde peer é o usuário destinatário da mensagem")
        
    # Permite o usuário setar seu (novo) username (nickname) #
    # // Entrada: Comando digitado na interface
    def definirUsername(self, comando):
        if Usuario.Logado:  # Se o usuario está online, faça logoff antes de setar outro nickname
            print("Logoff sob o antigo username sendo efetuado primeiro...")
            self.requisitarLogoff()
            print('\n')
        try:
            usernameCMD = comando.split()[1]    # username passado na linha de comando
            self.username = usernameCMD
        except IndexError: # Se der exceção, então usuario não passou user na linha de comando, dê input
            self.username = input("Entre com um username no chat: ")
        
        print(self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado() + "Username definido!"+self.cor.end())
        print("Bem vindo, @" + self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado() + self.username + self.cor.end())
        print("Faça " + self.cor.tazul()  +  "@login" + self.cor.end() + " para se registrar no Servidor Central")
                    
    # Método que imprime as informações de um usuário específico online. Caso não seja informado tal usuário, 
    # imprime as informação de conexão do USERNAME do usuário final no Servidor Central #
    # // Entrada: Comando digitado na interface
    # // Saída: Um booleano 1 ou -1 em caso de sucesso ou insucesso
    def info(self, comando):
        try:
            username = comando.split()[1]
            info = self.usuariosOnline.get(username)
            if info:
                print(self.cor.tazul() + self.cor.tsublinhado() + self.cor.tnegrito() + "Informações de: " + self.cor.end() + '@' + username)
                print(self.cor.tazul() + "Endereco: "  + self.cor.end() + info["Endereco"] + '\n' + 
                      self.cor.tazul() + "Porta: " + self.cor.end() + info["Porta"])
                return 1
            else:
                print(self.cor.tnegrito() + self.cor.tvermelho() + "Usuário: " + self.cor.tazul() + '@' + username + self.cor.end() + 
                      self.cor.tvermelho() + " não online. Requisite a lista de usuários, para atualizá-la" + self.cor.end())
                return -1
        except IndexError:
            chatsAbertos = len(Usuario.peersConectados)
            print(self.cor.tazul() + self.cor.tsublinhado() + self.cor.tnegrito() + "Informações suas: " + self.cor.end() + '@' + self.username)
            print(self.cor.tazul() + "Host: "  + self.cor.end() + self.host+ '\n' + self.cor.tazul() + "Porta: " + self.cor.end() + str(self.porta) + '\n' +
                  self.cor.tazul() + "Chats abertos: " + self.cor.end() + str(chatsAbertos) ) 
            return 1       

    # Método que imprime as informações de todos os peers conectados ao usuario final da aplicação. #
    # // Entrada: ToChoose
    # // Saída: ToChoose
    def conectados(self):
        pass #ToDo

   # ---------------------------------- Funcionalidade 3. Comunicação P2P ----------------------------------- #   

    # Método que aguarda conexões P2P, colocando ele em modo passivo para receber conexões #
    def aguardaConexoes_p2p(self):
        self.sockPassivo_p2p.bind((self.host, self.porta))
        print(self.cor.tazul() + self.cor.tnegrito() + self.cor.tsublinhado() + "Aplicação aguardando peers..." + self.cor.end())
        self.sockPassivo_p2p.setblocking(False)
        self.sockPassivo_p2p.listen(self.nConexoes)

    # Método que aceita as conexões do modo de escuta (passivo) #
    def aceitarConexoes_p2p(self):
        peerSock, endereco = self.sockPassivo_p2p.accept()
        print("Conectado com: ", endereco)
        return (peerSock, endereco)

    # Método executado pelas threads para receber e imprimir as mensagens dos peers, na interface do usuário final #
    # // Entrada: peerSock cuja thread executará o receive e o endereco desse peer
    def receberMensagem_p2p(self, peerSock, endereco):
        while True:
            bytesRecebidos = peerSock.recv(1024)
            dados = str(bytesRecebidos, "utf-8")
            # ToDo : Receber os bytes que informam o tamanho da Mensagem do peer
            dadosDict = json.loads(dados) # JSON to Dict (Hashmap)
            username = dadosDict["username"]
            mensagem = dadosDict["mensagem"]
            findPeer = Usuario.peersConectados.get(username) # Verifica se já existe uma conexão entre usuario e o peer que enviou msg
            if not findPeer:    # se não existe, registra essa conexão em peersConectados
                nAleatorioToCor = random.randint(0,3)
                corUser = self.cor.selecionaCor(nAleatorioToCor)
                # Condição de corrida
                Usuario.lock.acquire()
                Usuario.peersConectados[username] = {"socket": peerSock, "cor": corUser }
                Usuario.lock.release()
                # Fim da Condição de corrida
            corUser = Usuario.peersConectados.get(username)["cor"]
            print(self.cor.tvermelho() + self.cor.tnegrito() + "@" + corUser() + username + self.cor.end() + ": " + mensagem)
            
    # Método que faz as conexões P2P de forma ativa # 
    # // Entrada: Comando digitado na interface
    def conecta_p2p(self, comando): 
        if not Usuario.Logado: # Se o usuario não estiver online
            print("Fazendo login sob esse username: " + self.cor.tazul() + '@' + self.username + self.cor.end() + " primeiro...")
            self.requisitarLogin() # força ele logar
            if not Usuario.Logado:  return -1 # deu erro no login          
            
        # Captura o peername (username de quem deseja-se conectar) e a mensagem
        try:
            username = comando.split()[0][1:] 
            mensagem = comando[len(username) + 1:]
        except IndexError:
            print(self.cor.tnegrito() + self.cor.tvermelho() + "Informe a mensagem após o <Peername>" + self.cor.end())
            return -1
        
        findUserON = self.usuariosOnline.get(username)  # Verifica se tal username está online
        if not findUserON: # Se não, então não estabelece conexão
            print(self.cor.tnegrito() + self.cor.tvermelho() + "Usuário: " + self.cor.tazul() + '@' + username + self.cor.end() + 
                      self.cor.tvermelho() + " não online. Requisite a lista de usuários, para atualizá-la" + self.cor.end())
            return -1
        
        # Se sim, então faça:
        enderecoPeer = findUserON["Endereco"]   
        portaPeer = int(findUserON["Porta"])
        
        findPeer = Usuario.peersConectados.get(username)    # Verifica se já existe conexão estabelecida
        if not findPeer: # Se não, então registre ela em peerConectados
            sockAtivo_p2p = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            sockAtivo_p2p.connect((enderecoPeer, portaPeer))
           
            nAleatorioToCor = random.randint(0,3) # seleciona um nº aleatorio para decidir uma cor para cada usuario conectado
            corUser = self.cor.selecionaCor(nAleatorioToCor)
            Usuario.peersConectados[username] = {
                "socket": sockAtivo_p2p, 
                "cor": corUser 
            }
            print("Conectado com @" + corUser() + username + self.cor.end() + ': '+ enderecoPeer)
            
            # Assim que ele registra a conexão ativa na 1º vez, designa uma thread para receberMensagem nesse socket 
            peerThread = threading.Thread(target = self.receberMensagem_p2p, args = (sockAtivo_p2p, enderecoPeer))
            peerThread.start()
         
        # Envia a mensagem para esse username
        self.enviarMensagem(username, mensagem )    
        return 1
    
    # Método que envia mensagens para os peers, no formato JSON decidido #
    # // Entrada: Username e Mensagem
    def enviarMensagem(self, username, mensagem):
        socket = Usuario.peersConectados.get(username)["socket"]
        dictToJSON = {
            "username" : self.username,
            "mensagem" : mensagem
        }
        JSONToString = json.dumps(dictToJSON)
        # tamMensagem = len(mensagem)
        StringToBytes = bytes(JSONToString, "utf-8")
        # ToDo: Enviar o tamMensagem em 2 bytes para o peer
        socket.sendall(StringToBytes)
            
# ToDo - Tratar erro, caso o HOSTSC,PORTASC sejam invalidos. Bloquear o usuário final de avançar
def main():
    host = input("Digite o seu IP: ")                             # Endereço IP do Usuário Final 
    porta = input("Digite a PORTA para se manter em escuta: ")    # Aceita conexões nessa porta
    nConexoes = 3                                                 # nConexoes aceitas = nº conversas
    
    HOSTSC = input("Digite o HOST do Servidor Central: ") 
    PORTASC = input("Digite a PORTA do Servidor Central: ")       # Conecta-se no Servidor Central na porta dele 
    
    app = Usuario(host, int(porta), nConexoes, HOSTSC, int(PORTASC))
    app.start()
    
if __name__ == "__main__":
    main()
