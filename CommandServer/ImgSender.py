"""
CommandServer spawn出来的子进程，用来发送摄像头图片给客户端
"""

import socket
from CaptureFromCAM import CvCapture
import sys
import time
import thread
import cv2
import numpy



class ImgSender(CvCapture):
    """
    发送图像类，在一个子进程调用它，并且该进程的标准输入输出被重定向到管道，与主进程的某个管道连接
    所以使用input和print与主进程进行通信
    """
    def __init__(self,host,port,size=(320,240),fps=30):
        CvCapture.__init__(self, size, fps)
        self.exit = False                                                 #是否停止获取图像
        self.host = host
        self.port = int(port)
        self.mode = '0'                                                   #默认发送模式为0（双目）
        self.order = None                                                 #当前父进程要本子进程执行的命令
        self.mutex = thread.allocate_lock()                                 #锁

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)    #连接要接收图像的客户端的端口
        
    def startGetOrder(self):
        """
        启动一个线程获取主进程的order
        """
        def getOrder():#生产者
            while 1:
                rs = input()
                with self.mutex:
                    self.order = rs
        thread.start_new_thread(getOrder)

    def startSendFrame(self,show=False):
        """
        获取视频帧,show:是否弹出窗体显示,flag:获取模式，0 双目 1 左边 2 右边
        启动时需要两个摄像头能够打开
        """
        waittime = 1000 // self.fps
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),90]       #视频编码参数

        def ifsuceeded(rs1,rs0):                                #判断获取图像是否成功
            if self.mode == '0':
                return rs1 & rs0
            elif self.mode == '1':
                return rs1
            elif self.mode == '2':
                return rs0

        def sendframe(frame):                                                   #发送一帧图像
            result, imgencode = cv2.imencode('.jpg', frame, encode_param)       #编码图像
            data = numpy.array(imgencode)
            stringData = data.tostring()                                        #转换为二进制字符串发送
            stringLenData = str(len(stringData)).ljust(16)
            self.socket.send(stringLenData)                                     #先发送16字节的长度用来给接收端识别图片大小
            self.socket.send(stringData)                                        #再发送图像数据

        try:
            self.socket.connect((self.host,self.port))
        except socket.error:           
            sys.stdout.write('Socket error')
            return
        if self.capture1.isOpened() & self.capture0.isOpened():
            rs1,frame1 = self.capture1.read()
            rs0,frame0 = self.capture0.read()            

            order = None                                                    #查看子线程所获取的命令
            #该进程实际工作
            while ifsuceeded(rs1,rs0):
                if show:                                                    #显示
                    cv2.imshow('show1',frame1)
                    cv2.imshow('show0',frame0)                           
                
                with self.mutex:
                    if self.order != None:                                  
                        order, self.order = self.order, None                #清空self.order
                if order is not None:
                    if order == 'stop':                                     #退出命令
                        sys.stdout.write('Normal exit')                     #告诉父进程本子进程正常退出
                        break    
                    elif order[:3] == 'mode':                               #改变模式命令 
                        self.mode = order[6] 
                    
                #发送图像
                if self.mode == '0':
                    sendframe(frame1)
                    sendframe(frame0)
                elif self.mode == '1':
                    sendframe(frame1)
                elif self.mode == '2':
                    sendframe(frame0)

                #获取下一帧
                rs1,frame1 = self.capture1.read()
                rs0,frame0 = self.capture0.read()

                #帧数控制
                cv2.waitKey(waittime)
            else:#获取下一帧得到的图像为空则跳出循环，执行到这里，执行break才是正常退出，否则退出异常
                sys.stdout.write('Capture error')          #获取图像失败，告诉父进程
        sys.stdout.write('Capture error')                  #打开摄像头失败，告诉父进程
        self.clean()                                       #循环结束后清理工作

def testCVEncode():   
    
    capture = cv2.VideoCapture(0)
    ret, frame = capture.read()   
    encode_param=[int(cv2.IMWRITE_JPEG_QUALITY),90]

    while ret:
        result, imgencode = cv2.imencode('.jpg', frame, encode_param)   #编码
        data = numpy.array(imgencode)
        stringData = data.tostring()
        stringlen = str(len(stringData)).ljust(16)
                
        decimg=cv2.imdecode(data,1)                                     #解码
        cv2.imshow('CLIENT',decimg)

        ret, frame = capture.read()
        cv2.waitKey(10)
    sock.close()
    cv2.destroyAllWindows()


def run():                                               
    host = sys.argv[1] if len(sys.argv)==2 else '127.0.0.1'
    port = sys.argv[2] if len(sys.argv)==2 else '36888'
    #print('Now spawn process is sending Images to {0}:{1}!'.format(host,port))
    imgsender = ImgSender(host,port)
    imgsender.startSendFrame(False)
    
if __name__ == '__main__':    
    run()
    
    
    