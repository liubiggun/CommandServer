import struct
import SerialHandle

"""
命令格式
头              栈长度       命令字        数据          校验和
0x66 0xaa       0x08         0x01         "+100-100"    0xfc
"""
Head0=0x66
Head1=0xaa
EndStr=chr(0xfc)    #每一条命令的截止字节         
         

class Command:
    """
    命令类
    """       

    def __init__(self,comport):
        """
        
        """   
        self.dataLen=None     
        self.typeNum=None      
        self.dataVal=None
        self.cmdLine=None
        self.serHandle=SerialHandle.SerialHandle(comport)
  
    def GetType(self,line):
        """
        获取命令的类型，检查检验和(栈长度+命令字+数据)
        @param line: 命令行

        return: (typeNum,dataLen,dataVal):(命令类型，数据长度，数据)
        """
        if line[0:2]!=b'\x66\xaa':#检查命令头
            return ['\x00',0,None]

        self.dataLen=line[2]
        self.typeNum=line[3]        
        self.dataVal=line[4:-1]       

        if ord(self.dataLen)!=len(self.dataVal):#检查栈长度是否正确
            return ['\x00',0,None]
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
    
            return checksum&0xff 

        if ord(line[-1])!=char_checksum(line[2:-1]):#检查检验和
            return ['\x00',0,None]

        self.cmdLine=line+EndStr  #服务器接收得到的line将取出EndByte，发向串口时应该加上   


    def Execute(self):
        """
        执行命令
        """
        Cmds={'\x00':self.VaildCmd,'\x01':self.GetDist,'\x02':self.MotorCtl}      

        #发送命令行给下位机
        if self.typeNum != '\x00':
            self.serHandle.SendCmd(self.cmdLine)
        #执行其他动作
        Cmds[self.typeNum]()
        return self.serHandle.CheckReturn()

    def VaildCmd(self):
        """
        无效命令
        """
        pass

    def GetDist(self):
        """
        向下位机发送串口控制命令，获取超声波测距的结果
        """       

    def MotorCtl(self):
        """
        向下位机发送串口控制命令，控制电机
        """      
    

    
