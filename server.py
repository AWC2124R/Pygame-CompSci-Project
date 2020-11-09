import socket
import hashlib
from _thread import *

s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server, port = '10.56.216.85', 5555

pos = ["0:-100,-100", "1:-100,-100"]
ID_usage, currentID = [], "0"


def threaded_client(connection):
    global pos, currentID, ID_usage

    if currentID in ID_usage: currentID = "0" if currentID == "1" else "1"
    connection.send(str.encode(currentID))
    ID_usage.append(currentID)

    while True:
        try:
            data = connection.recv(2048)
            reply = data.decode('utf-8')

            if not data:
                pos = ["0:-100,-100", "1:-100,-100"]
                ID_usage.remove(currentID)

                connection.send(str.encode("Goodbye"))
                break
            else:
                print("Received: " + reply)
                if reply == "REQUEST_USER_DATABASE":
                    reply = ""

                    user_database_file = open("User_Database.txt", 'r')
                    while True:
                        user_data = user_database_file.readline().strip().split()
                        if not user_data: break
                        reply += user_data[0] + " " + user_data[1] + " " + user_data[2] + " "
                    user_database_file.close()
                elif reply[:17] == "ADD_USER_DATABASE":
                    username, password = reply.split()[1], reply.split()[2]
                    encoded_text = hashlib.md5(password.encode("utf-8"))
                    encoded_password = encoded_text.hexdigest()

                    user_database_file = open("User_Database.txt", 'a')
                    user_database_file.write(username + " " + encoded_password + " 0\n")
                    user_database_file.close()
                elif reply[:21] == "UPDATE_SCORE_POSITIVE":
                    username = reply.split()[1]
                    user_database = []

                    user_database_file = open("User_Database.txt", 'r')
                    while True:
                        user_data = user_database_file.readline().strip().split()
                        if not user_data: break
                        user_database.append(user_data)
                    user_database_file.close()

                    for i in range(len(user_database)):
                        if user_database[i][0] == username:
                            user_database[i][2] = str(int(user_database[i][2]) + 10)

                    user_database_file = open("User_Database.txt", 'w')
                    for i in range(len(user_database)):
                        user_database_file.write(user_database[i][0] + " " + user_database[i][1] + " " + user_database[i][2] + "\n")
                    user_database_file.close()
                elif reply[:21] == "UPDATE_SCORE_NEGATIVE":
                    username = reply.split()[1]
                    user_database = []

                    user_database_file = open("User_Database.txt", 'r')
                    while True:
                        user_data = user_database_file.readline().strip().split()
                        if not user_data: break
                        user_database.append(user_data)
                    user_database_file.close()

                    for i in range(len(user_database)):
                        if user_database[i][0] == username:
                            if int(user_database[i][2]) <= 10:
                                user_database[i][2] = "0"
                            else:
                                user_database[i][2] = str(int(user_database[i][2]) - 10)
                            break

                    user_database_file = open("User_Database.txt", 'w')
                    for i in range(len(user_database)):
                        user_database_file.write(user_database[i][0] + " " + user_database[i][1] + " " + user_database[i][2] + "\n")
                    user_database_file.close()
                else:
                    arr = reply.split(":")
                    id_ = int(arr[0])
                    pos[id_] = reply

                    reply = pos[1 if id_ == 0 else 0][:]
                    print("Sending: " + reply)
            connection.sendall(str.encode(reply))
        except:
            break

    print("Connection Closed")
    connection.close()

try:

    s.bind((server, port))
except socket.error as e:
    print(str(e))

s.listen(2)
print("Waiting for a connection")

while True:
    conn, addr = s.accept()
    print("Connected to: ", addr)
    start_new_thread(threaded_client, (conn,))
