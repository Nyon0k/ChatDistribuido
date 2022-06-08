#-*- encoding: utf-8 -*-

import socket, json

def teste_ReqLogin(HOSTSC, PORTSC, socket):
    requisicao_servidor = {
        "operacao": "login",
        "username": "USUARIO TESTE",
        "porta": 25641
    }
    requisicaoJSON = json.dumps(requisicao_servidor)
    tamRequisicao = len(requisicaoJSON)
    tamReqBytes = tamRequisicao.to_bytes(2, "big")
    
    socket.sendall(tamReqBytes)
    bytesEnviados = bytes(requisicaoJSON, "utf-8")
    socket.sendall(bytesEnviados)
    
    first2Bytes = socket.recv(2)
    tamResposta = int.from_bytes(first2Bytes, "big")
    
    bytesRecebidos = socket.recv(tamResposta + 1024)
    dados = str(bytesRecebidos, "utf-8")
    print(dados)
    

def teste_ReqLista(HOSTSC, PORTSC, socket):
    requisicao_servidor = {
        "operacao": "get_lista"
    }
    requisicaoJSON = json.dumps(requisicao_servidor)
    tamRequisicao = len(requisicaoJSON)
    tamReqBytes = tamRequisicao.to_bytes(2, "big")
    
    
    socket.sendall(tamReqBytes)
    bytesEnviados = bytes(requisicaoJSON, "utf-8")
    socket.sendall(bytesEnviados)
    
    first2Bytes = socket.recv(2)
    tamResposta = int.from_bytes(first2Bytes, "big")
    
    bytesRecebidos = socket.recv(tamResposta + 1024)
    dados = str(bytesRecebidos, "utf-8")
    print(dados)
    
# Método para fazer logoff num usuário em determinado Server
def fazLogoff(HOSTSC, PORTSC, socket, username):
    requisicao_servidor = {
        "operacao": "logoff",
        "username": username
    }
    requisicaoJSON = json.dumps(requisicao_servidor)
    tamRequisicao = len(requisicaoJSON)
    tamReqBytes = tamRequisicao.to_bytes(2, "big")
    
    socket.sendall(tamReqBytes)
    bytesEnviados = bytes(requisicaoJSON, "utf-8")
    socket.sendall(bytesEnviados)
        
    first2Bytes = socket.recv(2)
    tamResposta = int.from_bytes(first2Bytes, "big")
    
    bytesRecebidos = socket.recv(tamResposta + 1024)
    dados = str(bytesRecebidos, "utf-8")
    print(dados)


def main():
    HOSTSC = input("IP SC: ")
    PORTSC = input("PORTSC: ")
    username = ""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((HOSTSC,int(PORTSC)))
    print("# TESTE LOGIN #")
    teste_ReqLogin(HOSTSC,PORTSC,sock)
    print("# TESTE GET_LISTA # ")
    teste_ReqLista(HOSTSC,PORTSC,sock)
    print("# TESTE LOGOFF #")
    fazLogoff(HOSTSC, PORTSC, sock, username)
main()
