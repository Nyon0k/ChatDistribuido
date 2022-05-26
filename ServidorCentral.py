import socket
import json
import select
import threading, sys

class ServidorCentral:
	def __init__(self, HOST, PORTA, nConexoes):
	    self.host = HOST
		self.porta = PORTA
		self.nConexoes = nConexoes
		self.entradas = [sys.stdin]
		self.conexoes = {}

	def iniciaServidor(self):
		#cria o socket
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM) #Internet(IPv4 + TCP)
		#vincula a localizacao do servidor
		sock.bind((self.host, self.porta))
		#coloca-se em modo de espera por conexoes
		sock.listen(self.nConexoes)
		return sock

	def aceitaConexao(self, sock):
		#estabelece conexao com o proximo cliente
		cliente_sock, endereco = sock.accept()
		return cliente_sock, endereco
		
	def atendeRequisicoes(self, cliSock, endereco):
		while True:
			data = cliSock.recv(1024)
			if not data:
				print(str(endereco)+'-> encerrou')
				lock.acquire()
				del conexoes[cliSock]
				lock.release()
				cliSock.close()
				return
			respostaCliente = bytes(data, 'utf-8')
			cliSock.send(respostaCliente)

servidor = ServidorCentral('', 5001, 2)
sock = servidor.iniciaServidor()
lock = threading.Lock()
while True:
	leitura, escrita, excecao = select.select(servidor.entradas, [], [])
	#tratar todas as entradas prontas
	for pronto in leitura:
		if pronto == sock: #pedido novo de conexao
			cliente_sock, endereco = servidor.aceitaConexao(sock)
			print('Conectado com: ' + str(endereco))
			#cria novo processo para atender o cliente
			cliente = threading.Thread(target = servidor.atendeRequisicoes, args = (cliente_sock, endereco))
			cliente.start()
			clientes.append(cliente) #armazena a referencia da thread para usar com join()
		elif pronto == sys.stdin: #entrada padrao
			cmd = input()
			if cmd == 'fim': #solicitacao de finalizacao do servidor
				for c in clientes: #aguarda todos os processos terminarem
					c.join()
				sock.close()
				sys.exit()
			elif cmd == 'hist':
                		print(str(servidor.conexoes.values()))