from twisted.internet import defer,threads
from twisted.internet.protocol import Protocol,ServerFactory
from twisted.protocols.basic import LineOnlyReceiver,FileSender
import sys
import Command
from CaptureFromCAM import CvCapture


class CmdProtocol(LineOnlyReceiver):
    """
    本应用的命令行协议
    """
    delimiter=Command.EndStr 

    Users = {"master":"master.123456",'guess':'guess.111111'} 

    def __init__(self):
        self.user=None
        self.deferred=None
        self.greetDeferred=None 
    
    def connectionMade(self):
        """
        连接建立时进行的初始化
        """
        print('{0.host}:{0.port} connecting.Whether I have master:{1}'.format(
            self.transport.getPeer(),Command.Command.hasmaster))
        self.greetDeferred = self.getUser()
        self.greetDeferred.addCallback(lambda user : 
                                       self.transport.write("Waiting your order,master") if self.user=='master'
                                       else self.transport.write('is Anything I can help you?%s' % self.user))

    def lineReceived(self, line):
        """
        收到一条命令时
        """
        print('Receive from {0.host}:{0.port}:{1}'.format(self.transport.getPeer(),line))    #打印接收到的信息

        if self.user is not None:                                                            #是否已经验证身份 
            if self.factory.service.parseCmd(line):                                          #解析命令成功
                if self.factory.service.cmdHandler.typeNum=='\xff':                          #如果是获取图像                         
                    d = self.factory.service.Command("FetchImage")
                else:                                                                        #如果是控制命令
                    if self.user=='master':                                                  #用户是master才可以发送给下位机                     
                        d = self.factory.service.Command("ExecuteCmds")
                        #注册Command命令在工作者线程池中处理完毕后调用的回调
                        d.addCallback(lambda returnStr: self.transport.write("Return:%s" % returnStr) if returnStr else 
                                      self.transport.write("My legs had something wrong = =!"))
                    else:
                        self.transport.write('No permission!')
            else:
                self.transport.write("I don't undertand your order")

        else:                                                                                #登陆
            user=self.checkUser(line)
            if user is not None:
                if user=='2masters':
                    self.transport.write("Invaild pin!Please input again!")
                else:
                    if self.greetDeferred is not None:
                        d, self.greetDeferred = self.greetDeferred, None
                        d.callback(user)
            else:
                self.transport.write("Invaild pin!Please input again!")
        
    def connectionLost(self,reason):
        """
        丢失连接
        """
        print('I lost connection from {0.host}:{0.port}.User:{1}'.format(self.transport.getPeer(),self.user))
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.cancel() # cancel the deferred if it hasn't fired  服务取消

        if self.factory.hasmaster and self.user=='master':             #若本次连接登陆的是master，退出时清空hasmaster标记
            self.factory.hasmaster=False

    def checkUser(self,line):
        """
        验证密码
        """
        if line==self.Users['master']:              #如果登陆的是master
            if self.factory.hasmaster:           #若当前已经有master登陆，不允许登陆  
                return '2masters'
            else :
                return "master"
        elif line==self.Users['guess']:
            return 'guess'
       
    def setUser(self,user):
        """
        设置获取此连接的user
        """         
        if user=='master':   
               self.factory.hasmaster=True          #设置hasmaster标记

        self.user=user
        
    def getUser(self):
        """
        登陆时请客户端输入登陆信息
        """   
        self.transport.write("Welcome,master!Now check pin:")  
                       
        def canceler(d):
            print 'Canceling login.'
            factory.deferred = None
            connector.disconnect()

        deferred = defer.Deferred(canceler)
        deferred.addCallback(self.setUser)

        return deferred
             
class CmdFactory(ServerFactory):

    protocol = CmdProtocol
    hasmaster=False

    def __init__(self, service):
        self.service = service

class CmdService(object):
    """
    命令服务
    1.获取客户端发来的命令后执行命令，但是命令执行不一定立刻执行完毕，所以ExecuteCmds方法返回defered，
    此处命令使用deferToThread，因为方法要等待下位机返回操作完成应答，不使用可能造成阻塞，只提供第一个
    登陆进来的用户进行控制
    2.获取客户端发来的获取图像请求，可提供多个用户获取
    """      

    def __init__(self, port):
        self.port = port  
        self.transport=None 
        self.cmdHandler=Command.Command(sys.argv[1])   

    def parseCmd(self,cmdline):
        """
        进行服务前需先调用本方法去解析命令，返回是否解析为已知命令
        """
        return self.cmdHandler.GetType(cmdline)

    def Command(self, xform_name):
        """
        服务
        """
        thunk = getattr(self, 'xform_%s' % (xform_name,), None)

        if thunk is None: # 没有这个服务
            return None

        return thunk()
        #try:
        #    return thunk(cmdline)
        #except:
        #    return None 

    def xform_FetchImage(self):
        """
        获取图像服务
        """


    def xform_ExecuteCmds(self):
        """
        线程池执行命令服务，返回一个defer，命令服务返回下位机传来的数据
        """
        return threads.deferToThread(self.cmdHandler.Execute)

class ImgSender(FileSender):
    def __init__(self):
        """
        """
        self.cap=CvCapture(size=(320,240),fps=10)

    def makeFile(self):
        """
        生成要传输的文件
        """

    def beginFileTransfer(self, file, consumer, transform = None):
        """
        开始传输文件

        @type file: Any file-like object
        @param file: The file object to read data from

        @type consumer: Any implementor of IConsumer
        @param consumer: The object to write data to

        @param transform: A callable taking one string argument and returning
        the same.  All bytes read from the file are passed through this before
        being written to the consumer.

        @rtype: C{Deferred}
        @return: A deferred whose callback will be invoked when the file has
        been completely written to the consumer. The last byte written to the
        consumer is passed to the callback.
        """
        return super(ImgSender, self).beginFileTransfer(file, consumer, transform)

    def resumeProducing(self):
        return super(ImgSender, self).resumeProducing()

    def pauseProducing(self):
        return super(ImgSender, self).pauseProducing()

    def stopProducing(self):
        return super(ImgSender, self).stopProducing()

def RunServer(port):
    service = CmdService(port)
    factory = CmdFactory(service)
    
    from twisted.internet import reactor
    port = reactor.listenTCP(port, factory)

    print 'Serving Cmd on %s.' % (port.getHost(),)

    reactor.run()



if __name__ == '__main__':
    print 'Start'
    RunServer(36888)
    

        
