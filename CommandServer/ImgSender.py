"""
CommandServer spawn出来的子进程，用来发送摄像头图片给客户端
"""

from twisted.internet import defer,threads
from twisted.internet.protocol import Protocol,DatagramProtocol
from twisted.protocols.basic import FileSender
from twisted.internet.stdio import StandardIO
from CaptureFromCAM import CvCapture
import sys
import time

class ImgSendProtocol(DatagramProtocol):
    """
    发送UDP数据包协议
    """
    def __init__(self,host,port):
        self.host=host
        self.port=port

    def startProtocol(self):
        self.transport.connect(self.host, self.port)             #固定连接的UDP，现在只能发送数据包给指定的地址

        self.transport.write("hello") # no need for address

    def datagramReceived(self, data, (host, port)):
        print "received %r from %s:%d" % (data, host, port)

    # Possibly invoked if there is no server listening on the
    # address to which we are sending.
    def connectionRefused(self):
        print "No one listening"              


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

def run():                                               
    host=sys.argv[1]
    port=sys.argv[2]
    print('Now spawn process is sending Images to {0}:{1}!'.format(host,port))

    from twisted.internet import reactor
    reactor.listenUDP(0, ImgSendProtocol(host,port))
    time.sleep(5)
    reactor.run()
    
if __name__ == '__main__':    
    run()
    
    
    