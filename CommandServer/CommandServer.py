from twisted.internet import defer,threads
from twisted.internet.protocol import Protocol,ServerFactory
from twisted.protocols.basic import LineOnlyReceiver
import sys
import Command


class CmdProtocol(LineOnlyReceiver):
    """
    本应用的命令行协议
    """
    delimiter=Command.EndStr 
    def __init__(self):
        self.deferred=None
        self.greetDeferred=None
        self.check=False#是否已经验证身份   
    
    def connectionMade(self):
        """
        连接建立时进行的初始化
        """
        self.greetDeferred = self.factory.service.getUser(self.transport)
        self.greetDeferred.addCallback(lambda user : self.transport.write("Waiting your order,master %s!:\n" % user))

    def lineReceived(self, line):
        """
        收到一条命令时
        """
        if self.check:
            d = self.factory.service.Command("ExecuteCmds",line)
            d.addCallback(lambda returnStr: self.transport.write("Return:%s" % returnStr))#Command命令在工作者线程池中处理完毕后调用
        else:#密码验证
            user=self.factory.service.checkUser(line)
            if user is not None:
                if self.greetDeferred is not None:
                    d, self.greetDeferred = self.greetDeferred, None
                    d.callback(user)
                self.check=True
            else:
                self.transport.write("Invaild pin!\n")
        
    def connectionLost(self,reason):
        """
        丢失连接
        """
        if self.deferred is not None:
            deferred, self.deferred = self.deferred, None
            deferred.cancel() # cancel the deferred if it hasn't fired  服务取消
             
class CmdFactory(ServerFactory):

    protocol = CmdProtocol

    def __init__(self, service):
        self.service = service

class CmdService(object):
    """
    命令服务，获取客户端发来的命令后执行命令，但是命令执行不一定立刻执行完毕，所以ExecuteCmds方法返回defered
    """
    CMD = None
    Users = { "guest":"111111","lyh":"123456"}    

    def __init__(self, port):
        self.port = port  
        self.user = None
        self.transport=None 
        self.cmdHandler=Command.Command(sys.argv[1])

    def checkUser(self,line):
        """
        验证密码
        """
        return "lyh"
       
    def setUser(self,user):
        """
        设置获取此服务的user
        """    
        self.user=user
        return user
        
    def getUser(self,transport):
        """
        验证密码
        """   
        transport.write("Welcome,master!Now check pin:\n")  
                       
        def canceler(d):
            print 'Canceling login.'
            factory.deferred = None
            connector.disconnect()

        deferred = defer.Deferred(canceler)
        deferred.addCallback(self.setUser)

        return deferred  

    def Command(self, xform_name, cmdline):
        """
        服务
        """
        thunk = getattr(self, 'xform_%s' % (xform_name,), None)

        if thunk is None: # 没有这个服务
            return None

        return thunk(cmdline)
        #try:
        #    return thunk(cmdline)
        #except:
        #    return None 

    def xform_FetchImage(self,cmdline):
        """
        获取图像服务
        """


    def xform_ExecuteCmds(self,cmdline):
        """
        执行命令服务
        """
        self.cmdHandler.GetType(cmdline)
        
        return threads.deferToThread(self.cmdHandler.Execute)

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
    

        
