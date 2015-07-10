import struct
import SerialHandle

"""
命令格式
头              栈长度       命令字        数据          校验和
0x66 0xaa       0x08         0x01         "+100-100"    0xfc
"""
Head0=0x66
Head1=0xaa
EndByte=0xfc    #每一条命令的截止字节

def GetType(line):
    """
    获取命令的类型，检查检验和(栈长度+命令字+数据)
    @param line: 命令行

    return: (typeNum,dataLen,dataVal):(命令类型，数据长度，数据)
    """
    if line[0:2]!=b'\x66\xaa':#检查命令头
        return ['\xff',0,None]

    typeNum=line[3]
    dataLen=line[2]
    dataVal=line[4:-1]       

    if dataLen!=len(dataVal):#检查栈长度是否正确
        return ['\xff',0,None]

    if line[-1]!=self.char_checksum(typeNum+typeNum+dataVal):#检查检验和
        return ['\xff',0,None]

    return (typeNum,dataLen,dataVal)

def char_checksum(self,data,littleEndian=True):
    """
    实际计算校验和时，解释为无符号整数还是带符号整数，结果必然是一样的。因为基于补码方式存储，计算加法时都是按位加，然后该进位的就进位。
    只是最终的结果，如果是带符号整数，最高位会被解释符号位

    char_checksum 按字节计算补码校验和。每个字节被翻译为带符号整数
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
        
        checksum += x
        
        if checksum > 0x7F: #上溢出
            checksum = (checksum & 0x7F) - 0x80 #取补码就是对应的负数值(或者checksum-256钟摆原理)
        
        if checksum < -0x80: # 下溢出
            checksum &= 0x7F #(或者checksum+256钟摆原理)
        
        #print(checksum)
    
    return checksum   

def uchar_checksum(self,data,littleEndian=True):
    """
    char_checksum 按字节计算补码校验和。每个字节被翻译为无符号整数
    @param data: 字节串
    @param byteorder: 大/小端
    """
    length = len(data)
    checksum = 0
    for i in range(0, length):
        if(littleEndian):
            x=struct.unpack('<B',data[i:i+1])
        else:
            x=struct.unpack('>B',data[i:i+1])

        checksum += x
        checksum &= 0xFF # 强制截断
        
    return checksum            
         

class Command:
    """
    命令类
    """       

    def __init__(self,line):
        """
        
        """
        self.line=line+chr(EndByte)  #服务器接收得到的line将取出EndByte，发向串口时应该加上
        (self.typeNum,self.dataLen,self.dataVal)=GetType(line)
        self.serHandle=SerialHandle.SerialHandle(3)
  

    def Execute(self):
        """
        执行命令
        """
        Cmds={'\xff':self.VaildCmd,'\x00':self.GetDist,'\x01':self.MotorCtl}      

        #发送命令行给下位机
        if self.typeNum != '\xff':
            self.serHandle.SendCmd(self.line)
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
    

    
