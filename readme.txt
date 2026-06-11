# Task2 UDP socket Programming

## 运行环境
- Windows 11
- Python 3.12

## 依赖
- pandas

## 配置选项

### 运行

#### 服务器端

python udpserver.py <端口号>

例：

python udpserver.py 8888

C:\Users\storm\AppData\Local\Programs\Python\Python312\python.exe udpserver.py 8888

#### 客户端

python udpclient.py <服务端IP> <端口号>

例：

python udpclient.py 127.0.0.1 8888

C:\Users\storm\AppData\Local\Programs\Python\Python312\python.exe udpclient.py 127.0.0.1 8888

参数说明：
- 服务端IP：服务器所在IP地址
- 端口号：服务器监听的UDP端口

### 服务器端终止

netstat -ano | findstr 8888
taskkill /F /PID 29224

## 报文首部格式（16 字节）

| 字段		| 大小 	| 说明 						|
|---------------|-------|-----------------------------------------------|
| seq 		| 4B 	| 发送方序列号 					|
| ack 		| 4B 	| 确认号（累积确认） 				|
| id 		| 2B 	| StudentID 验证字段 				|
| data_length 	| 2B 	| 数据体长度 					|
| flags 	| 1B 	| bit7=ACK, bit6=SYN, bit5=FIN，后5位保留	|
| hour 		| 1B 	| 服务器当前时间（时） 				|
| minute 	| 1B 	| 服务器当前时间（分） 				|
| second 	| 1B 	| 服务器当前时间（秒） 				|
