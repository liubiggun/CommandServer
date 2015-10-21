"""
命令解析与命令发送给下位机模块，控制小车只能有一个客户端，其他客户端只能获取图像

当前命令有：
命令格式
头             栈长度     命令字   数据          校验和      结束字节   意义
0x66  0xaa     0x01      0x01     "0"            0x##      0xfc      获取超声波测距的结果，数据：超声波模块索引
0x66  0xaa     0x08      0x02     "+100-100"     0x##      0xfc      设置电机速度，数据：两个电机速度(0~255)，+-表示正反转

0x66  0xaa     0x07      0x7f     "65536;0"      0x##      0xfc      控制获取图像数据，第一个参数是客户端要接收数据的TCP端口
数字字符串长度不足5则补零，^打开双目图像传输，&打开其中一个摄像头的图像传输(id:1)*打开另一个(id:0), ^ & *这三个是打开传输命令
$关闭图像传输，0是获取双目数据，1是左边摄像头，2则右边，？查询状态，服务器返回客户端0 1 2 或 $

"""

import struct
import SerialHandle

Head0 = 0x66
Head1 = 0xaa
EndStr = chr(0xfc)    #每一条命令的截止字节
class Command:
    """
    命令类。comport：串口设备，这里需要在管理连接协议时判断用户户为master时才可以发送命令给下位机
    """  
         
    def __init__(self,comport):  
        self.dataLen = None        #栈长度
        self.typeNum = None        #命令字
        self.dataVal = None        #数据
        self.dataParts = []        #数据中若有;号，说明分为几个部分，在协议中需要用到，如图像命令的"65536;0"
        self.cmdLine = None        #完成的命令行
        self.serHandle = SerialHandle.SerialHandle(comport)
  
    def GetType(self,line):
        """
        获取命令的类型，检查检验和(栈长度+命令字+数据)
        @param line: 命令行

        return: 返回是否解析为已知命令
        """
        self.dataParts = []
        if line[0:2] != b'\x66\xaa':#检查命令头
            self.typeNum = '\x00'
            return False

        self.dataLen = line[2]
        self.typeNum = line[3]        
        self.dataVal = line[4:-1]       

        if ord(self.dataLen) != len(self.dataVal):#检查栈长度是否正确
            self.typeNum = '\x00'
            return False

        def char_checksum(data,littleEndian=True):
            """
            计算校验和(数据字符串中每个字符转换成有符号字节进行求和，运算过程中按有符号字节存储，结果返回相应的无符号字节表示)

            @param data: 字节串
            @param byteorder: 大/小端
            """
            length = len(data)
            checksum = 0
            for i in range(0, length):
                if(littleEndian):
                    x = struct.unpack('<b',data[i:i + 1])
                else:
                    x = struct.unpack('>b',data[i:i + 1])

                #C语言计算会截断，这里模拟截断过程
        
                checksum += x[0]
        
                if checksum > 0x7F: #上溢出
                    checksum = (checksum & 0x7F) - 0x80 #取补码就是对应的负数值(或者checksum-256钟摆原理)
        
                if checksum < -0x80: # 下溢出
                    checksum &= 0x7F #(或者checksum+256钟摆原理)
    
            return checksum & 0xff 

        if ord(line[-1]) != char_checksum(line[2:-1]):#检查检验和
            self.typeNum = '\x00'
            return False

        if self.dataVal.find(';') > -1:#按;号划分数据
            self.dataParts.extend(self.dataVal.split(';'))

        if self.typeNum == '\x7f':#验证图像命令数据的格式
            if (1024 < int(self.dataParts[0]) < 65535) and self.dataParts[1] in ['^','&','*','$','?','0','1','2']:
                return True
            else:
                self.typeNum = '\x00'
                return False
            
        self.cmdLine = line + EndStr  #服务器接收得到的line将取出EndByte，发向串口时应该加上

        return True

    def Execute(self):
        """
        执行命令，并返回下位机的执行后应答，若返回''，则向客户端发送'I don't undertand your order'
        """
        Cmds = {'\x00':self.VaildCmd,'\x01':self.Send2Controler,'\x02':self.Send2Controler}      
       
        return Cmds[self.typeNum]()

    def VaildCmd(self):
        """
        无效命令
        """
        return ''

    def Send2Controler(self):
        """
        向下位机发送串口控制命令
        """  
        self.serHandle.SendCmd(self.cmdLine)  
        return self.serHandle.CheckReturn() 

    
