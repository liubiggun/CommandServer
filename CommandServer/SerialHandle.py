import serial

class SerialHandle:
    """
    串口处理类
    """

    def __init__(self,port):
        """
        构造函数

        @param port: 串口号
        """
        self.ser = serial.Serial(
        port,              # number of device, numbering starts at
        # zero. if everything fails, the user
        # can specify a device string, note
        # that this isn't portable anymore
        # if no port is specified an unconfigured
        # an closed serial port object is created
        baudrate=115200,        # baud rate
        timeout=5,             # set a timeout value, None for waiting forever
        )

    def SendCmd(self,line):
        """
        发送命令行给下位机
        """
        if self.ser.isOpen():
            self.ser.write(line)  
            print "Send to arduino : {0} (len:{1})\n".format(line,len(line))       

    def CheckReturn(self):
        """
        线程中等待下位机返回数据，返回若是''空字符串，说明下位机没有正确响应命令
        """              
        rs=self.ser.readline()

        return rs

        