import queue
import time
from datetime import datetime
import random
import socket
import struct
import sys
import threading

bitmask=0x5A3C
PROBABILITY=0.1

log_Lock=threading.Lock()
clients_Lock=threading.Lock()

# 报文各个字段依次为：
# seq(4B), ack(4B), id(2B), data_length(2B), ACK(1bit), SYN(1bit), FIN(1bit), 保留位5bit, 服务器系统时间时、分、秒分别占1B, 共计16B
headformat="!IIHHBBBB"

def packMessage(seq,ack,id,ACK,SYN,FIN,data):
    return struct.pack(headformat, seq, ack, id, len(data), (ACK << 7) | (SYN << 6) | (FIN << 5),datetime.now().hour,datetime.now().minute,datetime.now().second)+data

def unpackMessage(head):
    seq,ack,id,length,flag,hour,minute,second=struct.unpack(headformat, head)
    ACK,SYN,FIN=flag>>7&1,flag>>6&1,flag>>5&1
    return (seq,ack,id,length,ACK,SYN,FIN,hour,minute,second)

def log(address,content):
    try:
        with log_Lock:
            with open("run_log.txt","a",encoding="utf-8") as run_log:
                timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
                run_log.write("【"+timestamp+"】Server["+str(address)+"]: "+content+"\n")
    except:
        print("日志记录失败")

def cope(sock,address,msgqueue):
    curseq=0
    try:
        # 三次握手其一
        # request_message=client.recv(13)
        msg=msgqueue.get()
        if(len(msg)<16):
            raise RuntimeError
        seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(msg)
        if(ACK!=0 or SYN!=1 or id^bitmask<0 or id^bitmask>9999):
            raise RuntimeError
        log(address,f"接收三次握手其一，SYN=1,seq={seq}")
        # 三次握手其二
        curseq=ack
        curack=seq+1
        log(address,f"发送三次握手其二，SYN=1，ACK=1，seq={curseq}，ack={curack}")
        sock.sendto(packMessage(curseq, curack,0, 1, 1, 0, b''),address)
        # 三次握手其三
        msg=msgqueue.get()
        if(len(msg)<16):
            raise RuntimeError
        seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(msg)
        log(address,f"接收三次握手其三，SYN={SYN}，ACK={ACK}，seq={curseq}，ack={curack}")

        # 数据传输
        msg=msgqueue.get()
        if(len(msg)<16):
            raise RuntimeError
        seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(msg[:16])
        data=msg[16:].decode()
        expected_seq=0
        while(FIN==0):
            p=random.random()
            if(p>=PROBABILITY): # 不丢包
                log(address,f"接收数据报，seq={seq}，ack={ack}，len={length}，data={data}")
                if(expected_seq==seq):
                    expected_seq+=1
                curseq=ack
                curack=expected_seq
                sock.sendto(packMessage(curseq, curack,0, 1, 0, 0, b''),address)
                log(address,f"发送ACK，ACK=1")
            msg=msgqueue.get()
            seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(msg[:16])
            data=msg[16:].decode()
        # 四次挥手其一
        log(address,f"接收四次挥手其一，FIN={FIN}，seq={seq}")
        # 四次挥手其二
        curseq=ack
        curack=seq+1
        log(address,f"发送四次挥手其二，ACK=1，seq={curseq}，ack={curack}")
        sock.sendto(packMessage(curseq, curack,0, 1, 0, 0, b''),address)
        # 四次挥手其三
        log(address,f"发送四次挥手其三，FIN=1，ACK=1，seq={curseq}，ack={curack}")
        sock.sendto(packMessage(curseq, curack,0, 1, 0, 1, b''),address)
        # 四次挥手其四
        msg=msgqueue.get()
        seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(msg)
        log(address,f"接收四次挥手其四，ACK={ACK}，seq={seq}")
    except:
        print(f"与{address}通信时出错")
        log(address,f"与{address}通信时出错")

# 读取命令行参数
if(len(sys.argv)!=2):
    print("命令行参数个数错误")
    sys.exit(1)
try:
    serverPort=int(sys.argv[1])
except:
    print("读命令行参数失败")
    sys.exit(1)

# startover the server
try:
    sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    sock.bind(("0.0.0.0",serverPort))
except:
    print("启动服务失败")
    sock.close()
    sys.exit(1)

clients={}

while (True):
    try:
        msg,address=sock.recvfrom(65536)
        with clients_Lock:
            if(address not in clients):
                clients[address]=queue.Queue()
                thread=threading.Thread(target=cope,args=(sock,address,clients[address]))
                thread.start()
            clients[address].put(msg)
    except:
        print("连接错误")
        sock.close()
        exit(1)