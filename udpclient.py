from datetime import datetime
import os
import pandas
import random
import socket
import struct
import sys
import time

StudentID=2715
bitmask=0x5A3C
count=30
WINDOWSIZE=400
string="Hello, I'm Xu Tao, a student from class Computer Science 24-1, student ID 241002715."

# 报文各个字段依次为：
# seq(4B), ack(4B), id(2B), data_length(2B), ACK(1bit), SYN(1bit), FIN(1bit), 保留位5bit, 服务器系统时间时、分、秒分别占1B, 共计16B
headformat="!IIHHBBBB"

def packMessage(seq,ack,id,ACK,SYN,FIN,data=b''):
    return struct.pack(headformat, seq, ack, id, len(data), (ACK << 7) | (SYN << 6) | (FIN << 5),0,0,0)+data

def unpackMessage(head):
    seq,ack,id,length,flag,hour,minute,second=struct.unpack(headformat, head)
    ACK,SYN,FIN=flag>>7&1,flag>>6&1,flag>>5&1
    return (seq,ack,id,length,ACK,SYN,FIN,hour,minute,second)

curTimeoutInterval=0.3
curEstimatedRTT=0.2
curDevRTT=0.025
def refreshTimeoutInterval(sampleRTT):
    global curEstimatedRTT,curDevRTT,curTimeoutInterval
    curEstimatedRTT=0.875*curEstimatedRTT+0.125*sampleRTT
    curDevRTT=0.75*curDevRTT+0.25*abs(sampleRTT-curEstimatedRTT)
    curTimeoutInterval=curEstimatedRTT+4*curDevRTT
    return curTimeoutInterval

# log recording
def log(content):
    try:
        with open("run_log.txt","a",encoding="utf-8") as run_log:
            timestamp=datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")
            run_log.write("【"+timestamp+"】Client-"+str(os.getpid())+": "+content+"\n")
    except:
        print("日志记录失败")

# 读取命令行参数
if(len(sys.argv)!=3):
    print("命令行参数个数错误")
    sys.exit(1)
try:
    serverIP=sys.argv[1]
    serverPort=int(sys.argv[2])
except:
    print("读命令行参数失败")
    sys.exit(1)

sock=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
try:
    sock.connect((serverIP, serverPort))
    log("正在建立连接")
except:
    print(f"连接服务器失败")
    log("建立连接失败")
    sock.close()
    sys.exit(1)

curseq=0
# 三次握手其一
try:
    log(f"发送三次握手其一，SYN=1,seq={curseq}")
    sock.sendall(packMessage(curseq,0,StudentID^bitmask,0,1,0,b''))
except:
    print("三次握手其一失败")
    log("发送三次握手其一失败")
    sock.close()
    sys.exit(1)
# 三次握手其二
sock.settimeout(curTimeoutInterval)
try:
    agree_message=sock.recv(16)
    if(len(agree_message)<16):
        raise RuntimeError
    seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(agree_message)
    log(f"接收三次握手其二，SYN={SYN}，ACK={ACK}，seq={seq}，ack={ack}")
    if(SYN!=1 or ACK!=1 or ack!=curseq+1):
        raise RuntimeError
except:
    print("三次握手其二失败")
    log("接收三次握手其二失败")
    sock.close()
    sys.exit(1)
# 三次握手其三
curseq=ack
curack=seq+1
try:
    log(f"发送三次握手其三，ACK=1，seq={curseq}，ack={curack}")
    sock.sendall(packMessage(curseq,curack,0,1,0,0,b''))
except:
    print("三次握手其三失败")
    log("发送三次握手其三失败")
    sock.close()
    sys.exit(1)

# 数据传输
dataCollection=[]
dataLength=[]
sendingCount=0
for i in range(count):
    length=random.randint(40,80)
    dataCollection.append(string[:length].encode())
    dataLength.append(length)
sendTime={}
RTTCollection=[]
leftBorder=0
rightBorder=0
while(leftBorder<count):
    while(rightBorder<count and sum(dataLength[leftBorder:rightBorder+1])<=WINDOWSIZE):
        curdata=dataCollection[rightBorder]
        log(f"发送第{rightBorder+1}个数据报（共计{count}个），第{sum(dataLength[:rightBorder])+1}~{sum(dataLength[:rightBorder+1])}个字节已经发送，seq={rightBorder}，len={len(curdata)}")
        print(f"第{rightBorder+1}个（第{sum(dataLength[:rightBorder])+1}~{sum(dataLength[:rightBorder+1])}字节）client端已经发送")
        sock.sendall(packMessage(rightBorder,0,0,1,0,0,curdata))
        sendingCount+=1
        sendTime[rightBorder]=time.time()
        rightBorder+=1
    sock.settimeout(curTimeoutInterval)
    try:
        ack_message=sock.recv(16)
        if(len(ack_message)<16):
            raise RuntimeError
        seq,ack,id,length,ACK,SYN,FIN,hour,minute,second=unpackMessage(ack_message)
        if(ACK!=1):
            raise RuntimeError
        if(ack>leftBorder):
            for i in range(leftBorder,ack):
                RTT=time.time()-sendTime[i]
                RTTCollection.append(RTT)
                refreshTimeoutInterval(RTT)
                log(f"接收ACK，ack={ack}，RTT={RTT*1000}ms，第{sum(dataLength[:i])+1}~{sum(dataLength[:i+1])}个字节已经收到，服务器接收时间为{hour}:{minute}:{second}")
                print(f"第{i+1}个（第{sum(dataLength[:i])+1}~{sum(dataLength[:i+1])}字节）server端已经收到，RTT是{RTT*1000}ms")
            leftBorder=ack
    except:
        log(f"超时{curTimeoutInterval*1000}ms")
        for i in range(leftBorder,rightBorder):
            curdata = dataCollection[i]
            log(f"重传第{i+1}个数据报（共计{count}个），第{sum(dataLength[:i])+1}~{sum(dataLength[:i+1])}个字节已经发送，seq={i}，len={len(curdata)}")
            print(f"重传第{i+1}个（第{sum(dataLength[:i])+1}~{sum(dataLength[:i+1])}字节）数据包")
            sock.sendall(packMessage(i, 0, 0, 1, 0, 0, curdata))
            sendingCount+=1
            sendTime[i]=time.time()

# 四次挥手其一
curseq=ack
curack=seq+1
try:
    log(f"发送四次挥手其一，FIN=1，seq={curseq}")
    sock.sendall(packMessage(curseq,0,0,1,0,1,b''))
except:
    print("四次挥手其一失败")
    log("接收四次挥手其一失败")
    sock.close()
    sys.exit(1)
# 四次挥手其二
try:
    seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(sock.recv(16))
    log(f"接收四次挥手其二，ACK={ACK}，seq={seq}，ack={ack}")
    if(ACK!=1 or ack!=curseq+1):
        raise RuntimeError
except:
    print("四次挥手其二失败")
    log("接收四次挥手其二失败")
    sock.close()
    sys.exit(1)
# 四次挥手其三
try:
    seq,ack,id,length,ACK,SYN,FIN,_,_,_=unpackMessage(sock.recv(16))
    log(f"接收四次挥手其三，FIN={FIN}，ACK={ACK}，seq={seq}，ack={ack}")
    if(FIN!=1 or ACK!=1 or ack!=curseq+1):
        raise RuntimeError
except:
    print("四次挥手其三失败")
    log("接收四次挥手其三失败")
    sock.close()
    sys.exit(1)
# 四次挥手其四
try:
    curseq=ack
    curack=seq+1
    log(f"发送四次挥手其四，ACK=1，seq={curseq}")
    sock.sendall(packMessage(curseq,0,0,1,0,0,b''))
except:
    print("四次挥手其四失败")
    log("接收四次挥手其四失败")
    sock.close()
    sys.exit(1)

sock.close()
maxRTT=pandas.Series(RTTCollection).max()
minRTT=pandas.Series(RTTCollection).min()
meanRTT=pandas.Series(RTTCollection).mean()
stdRTT=pandas.Series(RTTCollection).std()
print(f"丢包率：{100-count*100/sendingCount}%")
print(f"整个过程的最大RTT为{maxRTT*1000}ms")
print(f"最小RTT为{minRTT*1000}ms")
print(f"平均RTT为{meanRTT*1000}ms")
print(f"RTT的标准差为{stdRTT*1000}ms")