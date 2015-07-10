import serial

class SerialHandle:
    """
    串口处理类
    """

    def __init__(self,port):
        """
        构造函数
        """
        self.ser = serial.Serial(
        port,              # number of device, numbering starts at
        # zero. if everything fails, the user
        # can specify a device string, note
        # that this isn't portable anymore
        # if no port is specified an unconfigured
        # an closed serial port object is created
        baudrate=115200,        # baud rate
        bytesize=EIGHTBITS,     # number of databits
        parity=PARITY_NONE,     # enable parity checking
        stopbits=STOPBITS_ONE,  # number of stopbits
        timeout=15,             # set a timeout value, None for waiting forever
        xonxoff=0,              # enable software flow control
        rtscts=0,               # enable RTS/CTS flow control
        interCharTimeout=None   # Inter-character timeout, None to disable
        )

    def SendCmd(self,line):
        """
        发送命令行给下位机
        """
        if self.ser.isOpen():
            self.ser.write(line)

    def CheckReturn(self):
        """
        检查下位机返回数据
        """
        while self.ser.inWaiting()==0:
            pass
        rs=self.ser.readline(1,'\r\n')
        #获取满足协议的结果


        return rs

        