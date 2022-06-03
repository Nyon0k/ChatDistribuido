# -*- enconding: utf-8

import socket, json, sys, select, threading
import Peer, RichTextOnTerminal

'''
Classe Usuario: 
1. Faz a Comunicação com Servidor Central
2. Faz a Interface da aplicação (chat distribuído) com usuário final
3. Faz a Comunicação entre os pares (p2p)
'''

class Usuario:
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
        
        self.usuariosConectados = {} # Hashmap cuja chave é um username e o valor é uma lista: [socket, cor]
            
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.cor = RichTextOnTerminal.RichTextOnTerminal()  # instância rich text (deixa o texto mais rico)
        self.entradas = [sys.stdin] # Inclui o stdin na lista de entradas que aguardam I/O do socket
    
    # Funcionalidade 1. Comunicação com Servidor Central #
    
    # Faz a conexão da aplicação do usuário final com Servidor Central #
    def conectarServCentral(self):
        return self.sock.connect((self.hostsc, self.portasc))
    
    # Faz a requisição de login no Servidor Central sob o nickname (username) definido #
    def requisitarLogin(self):
        requisicao_servidor = {
            "operacao": "login",
            "username": self.username,
            "porta": self.porta
        }
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sock.sendall(bytesEnviados)
        self.receberResposta()
        
    # Faz a requisição de logoff no Servidor Central sob o username atual, permitindo trocá-lo #
    def requisitarLogoff(self):
        requisicao_servidor = {
            "operacao": "logoff",
            "username": self.username
        }
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sock.sendall(bytesEnviados)
        self.receberResposta()
    
    # Faz a requisição da lista de usuários online (disponíveis) para iniciar uma conversa #
    def requisitarLista(self):
        requisicao_servidor = {"operacao": "get_lista"}
        requisicaoJSON = json.dumps(requisicao_servidor)
        bytesEnviados = bytes(requisicaoJSON, "utf-8")
        self.sock.sendall(bytesEnviados)
        self.receberResposta()
    
    # Método único que recebe e imprime a resposta (p/ usuário final) de cada requisição acima # 
    def receberResposta(self):
        bytesRecebidos = self.sock.recv(1024)
        dados = str(bytesRecebidos, "utf-8")
        dadosJSON = json.loads(dados)
        operacao = dadosJSON["operacao"]
        status = dadosJSON["status"]
        resposta = ""
        if status == 200:
            resposta += self.cor.tciano() + self.cor.tnegrito() + self.cor.tsublinhado()
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
            print(self.cor.tciano() + self.cor.tnegrito() + self.cor.tsublinhado() + "Usuários online: "+ self.cor.end())
            for cliente in clientes:
                print('\t' + self.cor.tciano() + '@' + cliente + self.cor.end())
                
    # Funcionalidade 2. Interface com usuário final #   
    
    # Permite o usuário setar seu username (nickname) #
    def definirUsername(self):
        if self.usuariosOnline.get(self.username):
            print("Logoff sob o antigo username sendo efetuado primeiro...")
            self.requisitarLogoff()
            print('\n')
        self.username = input("Entre com um username no chat: ")
        print(self.cor.tciano() + self.cor.tnegrito() + self.cor.tsublinhado() + "(Novo) Username definido!"+self.cor.end())
       
    # Imprime o Menu de comandos #
    def exibirMenu(self):
        return("Comandos aceitos:\n \
            1. @menu: Exibe o menu de comandos\n \
            2. @nick: Define um USERNAME para se conectar\n \
            3. @exit: Encerra aplicação. Se houver conexões, seja com ServidorCentral ou Peers, são todas encerradas\n \
            4. @login: Faz requisição de login sob o nickname de entrada da aplicação\n \
            5. @logoff: Faz logoff sob esse nickname, permitindo o usuario final escolher outro\n \
            6. @get_lista: Requisita e recebe a lista de usuários online\n \
            7. @conecta <USERNAME>: Envia uma requisição para se conectar com USERNAME\n \
            8. @conectados: Imprime a informação dos peers conectados ao chat \n \
            9. @info <USERNAME>: Imprime a informação de um peer especifico conectado ao chat.\n\t\t(!) Se não for passado <USERNAME> imprime do próprio\n")
       
    # Método que imprime as informações de um usuário específico online. Caso não seja informado tal usuário, 
    # imprime as informação de conexão do USERNAME do usuário final no Servidor Central #
    # // Entrada: Comando digitado na interface
    # // Saída: Um booleano 1 ou -1 em caso de sucesso ou insucesso
    def info(self, comando):
        try:
            username = comando.split()[1]
            info = self.usuariosOnline.get(username)
            if info:
                print(self.cor.tverde() + self.cor.tsublinhado() + self.cor.tnegrito() + "Informações de: " + self.cor.end() + '@' + username)
                print(self.cor.tverde() + "Endereco: "  + self.cor.end() + info["Endereco"] + '\n' + self.cor.tverde() + "Porta: " + self.cor.end() + info["Porta"])
                return 1
            else:
                print(self.cor.tnegrito() + self.cor.tvermelho() + "Peer não consta no Servidor.\n\t(!) Requisite a lista para atualizá-la" + self.cor.end())
                return -1
        except IndexError:
            print(self.cor.tverde() + self.cor.tsublinhado() + self.cor.tnegrito() + "Informações suas: " + self.cor.end() + '@' + self.username)
            print(self.cor.tverde() + "Host: "  + self.cor.end() + self.host+ '\n' + self.cor.tverde() + "Porta: " + self.cor.end() + str(self.porta) + '\n' +
                  self.cor.tverde() + "Número de chats possivel: " + self.cor.end() + str(self.nConexoes) ) 
            return 1       

    # Método (start) que inicia a aplicação (interface com usuário) #
    def start(self):
        print(self.cor.tciano() + self.cor.tnegrito() + self.cor.tsublinhado() + " Bem vindo ao Chat Distribuído !" + self.cor.end() )
        self.definirUsername()
        self.conectarServCentral()
        
        print("Digite '@menu' para saber os comandos")
        
        self.peer = Peer.PeerToPeer(self.host, self.porta, self.nConexoes)  # Cria uma instância da classe peer (para lidar com essas comunicações)
        self.entradas.append(self.peer.sock) # Inclui o socket do peer na lista de entradas selecionadas enquanto aguarda I/O
        
        while True:
            leitura, escrita, excecao = select.select(self.entradas, [], [])
            for entrada in leitura:
                if entrada == self.peer.sock:
                    novoSockPeer, endereco = self.peer.aceitarConexoes()
                    peerThread = threading.Thread(target = self.peer.receberMensagem, args = (novoSockPeer, endereco))
                    peerThread.start()
                elif entrada == sys.stdin:
                    comando = input()
                    if comando == "@menu":
                        print(self.cor.tciano() + self.cor.tnegrito() + self.cor.tsublinhado() + "MENU DE COMANDOS\n" + self.cor.end() + self.exibirMenu())
                    elif comando == "@nick":
                        self.definirUsername()
                    elif comando == "@exit":    # Falta implementar mas acho que é o mesmo caso do exit no Servidor Central. Talvez algo tenha que ser 
                        # feito quanto as threads
                        pass
                    elif comando == "@login":
                        self.requisitarLogin()
                    elif comando == "@logoff":
                        self.requisitarLogoff()
                    elif comando == "@get_lista":
                        self.requisitarLista()
                    elif comando == "": # Esse comando vazio é para prevenir um erro quanto ao split
                        pass
                    elif comando[0] == "@":
                        try:
                            username = comando.split()[0][1:] 
                            mensagem = comando.split()[1]
                            self.enviarMensagem(username, mensagem)
                        except IndexError:
                            print(self.cor.tnegrito() + self.cor.tvermelho() + "Passe uma mensagem" + self.cor.end())
                    #elif comando == "@conectados":
                     #   self.conectados()
                    elif comando.split()[0] == "@info":
                        if self.info(comando) < 0: continue
                    else:
                        print(self.cor.tnegrito() + self.cor.tvermelho() + "COMANDO DE ENTRADA INVÁLIDO !" + self.cor.end())

    def enviarMensagem(self, username, mensagem):
        findUserON = self.usuariosOnline.get(username)
        if not findUserON:
            print(self.cor.tnegrito() + self.cor.tvermelho() + "Usuário não logado. Requisite a lista para atualizá-la" + self.cor.end())
        else:
            findPeer = self.usuariosConectados.get(username)
            enderecoPeer = findUserON["Endereco"]
            portaPeer = int(findUserON["Porta"])
            if not findPeer:
                self.sockAtivo = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
                self.sockAtivo.connect((enderecoPeer,portaPeer))
                corUser = self.cor.corAleatoria() 
                self.usuariosConectados[username] = [self.sockAtivo, corUser ]
                # resgatar a cor de um usuario
                # corUser = self.usuariosConectados.get(username)[1]
                # print(corUser() + + self.cor.end())
                print("Conectado com @ " + self.cor.corUser() + username + self.cor.end() + ': '+ enderecoPeer)
            else:
                pass
                #sockAtivo = self.usuariosConectados.get(username)[0] # socket
                
            
            
            
# ToDo - Tratar erro, caso o HOSTSC,PORTASC sejam invalidos. Bloquear o usuário final de avançar
def main():
    host = ''     # Endereço IP do Usuário Final 
    porta = input("Digite a PORTA para se manter em escuta: ")    # Aceita conexões nessa porta
    nConexoes = 3   # nConexoes aceitas = nº conversas
    
    HOSTSC = input("Digite o HOST do Servidor Central: ") 
    PORTASC = input("Digite a PORTA do Servidor Central: ")  # Conecta-se no Servidor Central na porta dele 
    app = Usuario(host, int(porta), nConexoes, HOSTSC, int(PORTASC))
    
    app.start()
    
if __name__ == "__main__":
    main()
