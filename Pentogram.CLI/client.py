#By Commit 405 7 Madara225
#https://github.com/nordbearbotdev/Pentogram/
#client script

from termcolor import colored
from Crypto.Cipher import AES
import socket
import os

banner = '''

██████  ███████ ███    ██ ████████  ██████   ██████  ██████   █████  ███    ███     
██   ██ ██      ████   ██    ██    ██    ██ ██       ██   ██ ██   ██ ████  ████     
██████  █████   ██ ██  ██    ██    ██    ██ ██   ███ ██████  ███████ ██ ████ ██     
██      ██      ██  ██ ██    ██    ██    ██ ██    ██ ██   ██ ██   ██ ██  ██  ██     
██      ███████ ██   ████    ██     ██████   ██████  ██   ██ ██   ██ ██      ██     
                                                                                    
                                                                                    
                                                    *By Commit 404 & Madara225 
                                                follow: https://github.com/nordbearbot
                                                        https://t.me/Pepe-Devs
'''
print(banner)


SERVER_IP = input(colored("Введите IP сервера: ", "green"))
SERVER_PORT = int(input(colored("Введите порт сервера: ", "green")))

USER_NAME = input(colored("Пожалуйтса, введите имя пользователя: "))

os.system('clear')

print(colored("<1>ONLINE..", "green", attrs=['reverse', 'blink']))

name = USER_NAME + ">> "
encoded_name = name.encode()


def chat():
    s = socket.socket()
    s.connect((str(SERVER_IP), SERVER_PORT))

    
    while True:    
        magic = AES.new('bQeThVmYq3t6w9z$', AES.MODE_CFB, 'Это IV456!')
        In_msg = s.recv(8192)
        recv_data_1 = magic.decrypt(In_msg)
        recv_data_unenc = recv_data_1.decode()
        print("\n" + recv_data_unenc)
        Out_msg = input(colored("\nОтправить-> ", "red", attrs=['bold']))
        data = encoded_name + Out_msg.encode()
        send_data = magic.encrypt(data)
        s.send(send_data)

 

        if recv_data_unenc == 'пока!':
            os.system('clear')
            print(colored("<0>OFFLINE", "red", attrs=['bold']))
            s.close()
            break


def main():
    chat()
main()
