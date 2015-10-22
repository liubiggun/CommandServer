"""
twisted框架的小车命令服务器，协议使用LineOnlyReceiver，一个TCP端口监听客户端传来的命令，
本进程作为主进程，子进程是图片传输进程。本进程的管道与子进程的标准输入输出相连接，以达到控
制子进程的目的。
子进程会立即连接客户端接收的端口，所以客户端应保证该端口处于监听状态

此处限制了guess用户数量，设子进程最多可以有n个，则guess用户最大个数设置为n，guess用户可以
获得图像但不能控制小车（未实现，当前使用TCP传播图片，只能满足一个客户端的图片请求，用组播
可实现...）
"""

from twisted.internet import defer,threads
from twisted.internet.protocol import Protocol,ServerFactory,ProcessProtocol
from twisted.protocols.basic import LineOnlyReceiver,FileSender
import sys
import Command
import logging
import logging.config
from CaptureFromCAM import CvCapture

logging.config.fileConfig('mainlog.conf')  
logger = logging.getLogger('main')

lineprint = '\n' + '-' * 60 + '\n'

def crucialprint(str):
    print(lineprint + str + lineprint[:-1])

class CmdProtocol(LineOnlyReceiver):
    """
    本应用的命令行协议，登陆后才可进行操作
    """
    delimiter = Command.EndStr 

    Users = {"master":"master.123456",'guess':'guess.111111'} 
    hasmaster = False                                           #静态标记，是否已经拥有master，当客户端需要以master登陆时查询
    guessmax = 3                                                #静态标记，guess用户的最大个数
    guessnum = 0                                                #静态标记，当前guess用户的个数

    def __init__(self):
        self.user = None
        self.deferred = None  

        #与子进程通信类，获取图像时将使用它来与子进程通信,在用户验证时会初始化
        self.subprocessProtocol = None
        
    def connectionMade(self):
        """
        连接建立时进行的初始化
        """
        crucialprint('{0.host}:{0.port} connecting. Whether I have master:{1}'.format(
            self.transport.getPeer(),CmdProtocol.hasmaster))

        self.transport.write("Welcome,friend!Now check pin:")                                #请客户端登陆
        

    def lineReceived(self, line):
        """
        收到一条命令时
        """
        print('Receive from {0}({1.host}:{1.port}) : {2}'.format(self.user,self.transport.getPeer(),line))  #打印接收到的信息

        if self.user is not None:                                                            #是否已经验证身份
            if self.factory.service.parseCmd(line):                                          #解析命令成功
                self.exeCmd()                
            else:
                self.transport.write("I don't undertand your order.")

        else:                                                                                #未登陆，进行登录
            self.authenticate(line)

    def exeCmd(self):
        """
        执行命令
        """
        def controlCar():
            """
            控制小车
            """
            if self.user == 'master':   #用户是master才可以发送给下位机
                d = self.factory.service.runService("ExecuteCmds")
                #注册Command命令在工作者线程池中处理完毕后调用的回调
                
                d.addCallbacks(lambda returnStr: self.transport.write("Return:%s" % returnStr) if returnStr else 
                                self.transport.write("My legs had something wrong = =!"),
                                lambda returnStr: sys.stdout.write('Arduino is no response.\n'))
            else:
                self.transport.write('No permission!')

        def controlImg():
            """
            控制图像传输
            """  
            dataparts = self.factory.service.cmdHandler.dataParts                      #['客户端接收图像端口';'flag']
            if dataparts[1] == '?':                                                    #数据为?说明查询当前传输图像子进程状态
                self.transport.write(self.subprocessProtocol.flag)

            elif dataparts[1] in ['^','&','*']:                                        #数据为^说明启动子进程
                if self.subprocessProtocol.flag == '$':                                #当前没有传输子进程才可以启动
                    mode = str(['^','&','*'].index(dataparts[1]))
                    self.subprocessProtocol = ImgProtocol(self.transport.getPeer().host,dataparts[0],self.user,mode)
                    self.factory.service.runService("SpawnImgSender",self.subprocessProtocol,
                                    self.transport.getPeer().host,dataparts[0],mode)
                else:
                    self.transport.write('Spawn process Exist!')  
                                    
            elif dataparts[1] == '$':                                                  #数据为$说明结束子进程
                if self.subprocessProtocol.flag != '$':                                #如果子进程还存在
                    self.factory.service.runService("StopImgSender",self.subprocessProtocol)  #人为控制子进程退出
                else:
                    self.transport.write('No spawn process!')

            elif dataparts[1] in ['0','1','2']:                                        #数据为0 1 2说明改变获取图像flag
                if self.subprocessProtocol.flag != '$':
                    if self.subprocessProtocol.flag != dataparts[1]:                   #不同才需要更改模式
                        crucialprint('Change mode of spawn process which connect to {0.host}:{0.port} to : {1}'.format(
                            self.transport.getPeer(),dataparts[1]))              
                        self.factory.service.runService("ConfigImgSender",self.subprocessProtocol,dataparts[1])
                    else:
                        self.transport.write('Nothing change!')
                else:
                    self.transport.write('No spawn process!')
        
        #执行命令逻辑
        if self.factory.service.cmdHandler.typeNum == '\x7f':                          #如果是获取图像命令
            controlImg()                                                                                            
        else:                                                                          #如果是控制命令
            controlCar()

    def authenticate(self, line):
        """
        登陆验证
        """
        def checkUser(line):
            """
            验证密码，这里简单的验证是否为'master.123456','guess.111111'，第一个是用户名
            第二个是密码
            """             
            if line == CmdProtocol.Users['master']:            #如果登陆的是master
                if CmdProtocol.hasmaster:                      #若当前已经有master登陆，不允许登陆
                    return '2masters'
                else :
                    return "master"
            elif line == CmdProtocol.Users['guess']:
                if CmdProtocol.guessnum == CmdProtocol.guessmax:    #若当前guess用户数量已达到上限，不允许登陆
                    return 'guessmax'
                else:
                    return 'guess'
            else:
                return None
       
        def setUser(user):
            """
            设置获取此连接的user
            """         
            if user == 'master':   
                CmdProtocol.hasmaster = True                                           #设置hasmaster标记
                self.transport.write("Waiting your order,master")
            elif user == 'guess':
                CmdProtocol.guessnum+=1                                                #guess数量自增1
                self.transport.write('Friend,you can fetch images from me.')                            
            else:
                self.transport.write('is Anything I can help you?%s' % self.user)
            crucialprint('{0}({1.host}:{1.port}) has logged in.'.format(user,self.transport.getPeer()))
            self.user = user                                                           #客户端使用user登陆
            self.subprocessProtocol = ImgProtocol(None,None,None,'$') 

        rs = checkUser(line)                                                           #验证登陆信息
        if rs is not None:
            if rs == '2masters':                                                       #已经有master登录
                self.transport.write("I have my dear master!")
            elif rs == 'guessmax':                                                     #guess登录已经超过3个
                self.transport.write("Sorry I can't help you.")
            else:                                                                      #登录成功,触发greeting回调
                setUser(rs)                                                                           
        else:                                                                          #错误登录信息
            self.transport.write("Invaild pin!Please input again!")

    def connectionLost(self,reason):
        """
        丢失连接
        """
        crucialprint('I lost connection from {0.host}:{0.port}.User:{1}'.format(self.transport.getPeer(),self.user))
        
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.cancel()                                                           #服务取消

        if self.subprocessProtocol and self.subprocessProtocol.flag != '$':
            self.subprocessProtocol.orderExit()                                         #命令子进程退出

        if CmdProtocol.hasmaster and self.user == 'master':       #若本次连接登陆的是master，退出时清空hasmaster标记
            CmdProtocol.hasmaster = False


class ImgProtocol(ProcessProtocol):
    """
    与子进程ImgSender的通信协议
    """
    exitMode=['Normal exit', 'Socket error', 'Send error', 'Capture error']

    def __init__(self, host, port, user, flag):
        self.host = host
        self.port = port
        self.user = user
        self.flag = flag
        self.exitstatus = 'Normal exit'

    def connectionMade(self):
        """
        子进程与本进程建立通信时的初始化
        """   
        crucialprint('Spawn process for {0}:{1} (user:{2}) has started!'.format(self.host,self.port,self.user))

    def changeMode(self, flag):
        """
        命令子进程改变传输模式
        """           
        self.flag = flag
        self.transport.write('mode:{0}\n'.format(flag))

    def orderExit(self):
        """
        命令子进程退出
        """
        self.transport.signalProcess('KILL')     

    def outReceived(self, data):
        """
        接收到子进程的标准输出，根据其输出，改变子进程退出状态
        """
        crucialprint('Spawn process send: {0}'.format(data))
        if data in ImgProtocol.exitMode:
            self.exitstatus = data

    def errReceived(self, data):
        """
        接收到子进程的标准错误输出
        """              

    def processEnded(self, reason):
        """
        子进程结束时
        """
        crucialprint('Spawn process for {0}:{1} (user:{2}) has exited : {3}!'.format(self.host, self.port,
                                                                                     self.user, self.exitstatus))
        self.flag = '$'#标志位结束标志

             
class CmdFactory(ServerFactory):
    protocol = CmdProtocol                                                         

    def __init__(self, service):
        self.service = service

class CmdService(object):
    """
    命令服务
    1.获取客户端发来的命令后执行命令，但是命令执行不一定立刻执行完毕，所以ExecuteCmds方法返回defered，
    此处命令使用deferToThread，因为方法要等待下位机返回操作完成应答，不使用可能造成阻塞，只提供第一个
    登陆进来的用户进行控制
    2.获取客户端发来的获取图像请求并spawn出子进程以UDP端口发送图片，可提供多个用户获取

    @port:      监听的端口
    @pypath:    python路径
    @comport:   下位机连接的串口设备
    @reator:    twisted.internet.reator
    """     

    def __init__(self, port, pypath, comport, reactor):
        self.port = port                                                  #服务监听的端口
        self.cmdHandler = Command.Command(comport)                        #命令处理类
        self.pypath = pypath
        self.reactor = reactor         

    def parseCmd(self,cmdline):
        """
        进行服务前需先调用本方法去解析命令，返回是否解析为已知命令
        """
        return self.cmdHandler.GetType(cmdline)

    def runService(self, xform_name, *args, **karg):
        """
        服务
        """
        thunk = getattr(self, 'xform_%s' % (xform_name,), None)

        if thunk is None: # 没有这个服务
            return None

        return thunk(*args, **karg)
        #try:
        #    return thunk(*args, **karg)
        #except:
        #    return None
    
    def xform_SpawnImgSender(self, imgprotocol, host, port, mode):
        """
        启动图像服务进程，spawn一个子进程专门处理发送图像给客户端host的port端口
        """        
        self.reactor.spawnProcess(imgprotocol, self.pypath, 
                                  [self.pypath, 'ImgSender.py', host, port, mode])    #启动子进程并建立与子进程的通信

    def xform_StopImgSender(self, imgprotocol):
        """
        关闭ImgSender子进程
        """
        imgprotocol.orderExit()

    def xform_ConfigImgSender(self, imgprotocol, flag):
        """
        设置图像传输服务，flag指明图像类型（0是获取双目数据，1是左边摄像头，2则右边）
        """
        imgprotocol.changeMode(flag)

    def xform_ExecuteCmds(self):
        """
        线程池执行命令服务，返回一个defer，命令服务返回下位机传来的数据
        """
        return threads.deferToThread(self.cmdHandler.Execute)


def RunServer(portnum):
    if len(sys.argv) == 1:
        if sys.platform[:3] == 'win':
            pypath = 'C:/Python27/python.exe'
            comport = 'COM4'
        else:
            pypath = 'python'
            comport = '/dev/ttyUSB0'
    else:
        pypath = sys.argv[1]
        comport = sys.argv[2]

    from twisted.internet import reactor
    
    service = CmdService(portnum, pypath, comport, reactor)
    factory = CmdFactory(service)
        
    port = reactor.listenTCP(portnum, factory)                          #开始监听端口
    
    print 'Start listenning on %s.\n\n' % (port.getHost(),)

    reactor.run()


if __name__ == '__main__':   
    RunServer(36888)
    

        
