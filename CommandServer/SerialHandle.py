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
        timeout=15,             # set a timeout value, None for waiting forever
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

        