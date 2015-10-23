#-*- coding: UTF-8 -*-
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
import logging
import logging.config

logging.config.fileConfig('spawnlog.conf')
logger = logging.getLogger('spawn') 


"""
使用无线网卡进行调试时注意：
电脑插上无线网卡后（此处使用了360wifi），电脑连接internet的网卡是wan，而无线网卡自然是wlen了，
似乎，360wifi它设置了wlen内的用户不能访问wan网卡，所以在写服务端和客户端时要特别注意ip地址要
指定的是wlen的子网内的ip，否则连接不上
"""
#是否在电脑上插上360wifi调试
PCwith360wifiDebug = False


def tellfather(str):
    """
    发送信息给父进程
    """
    sys.stdout.write(str)
    sys.stdout.flush()

def alertfather(str):
    """
    发送错误信息给父进程
    """
    sys.stderr.write(str)
    sys.stderr.flush()

class ImgSender(CvCapture):
    """
    发送图像类，在一个子进程调用它，并且该进程的标准输入输出被重定向到管道，与主进程的某个管道连接
    所以使用input和print与主进程进行通信
    这里的模式对应摄像头的打开与关闭是：     '0' ==> 1（开） 0（开）
                                          '1' ==> 1（开） 0（关）
                                          '2' ==> 1（关） 0（开）
    """
    def __init__(self,host,port,mode,size=(320,240),fps=10):
        CvCapture.__init__(self, size, fps)
        self.exit = False                                                 #是否停止获取图像
        self.host = host
        self.port = int(port)
        self.mode = mode                                                  
        self.order = None                                                 #当前父进程要本子进程执行的命令
        self.need2change = True  #提示是否要转换模式，若为True，将先转换模式
        self.mutex = thread.allocate_lock()                               #锁       

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)    #连接要接收图像的客户端的端口

    def getOrder(self):
        """
        获取主进程的order
        """         
        while 1:
            rs = raw_input()    #接收父进程发来的信息     !这里老是出问题，接收不到父进程发来的命令
            with self.mutex:
                self.order = rs

    def montage(self,frame1,frame0):
        """
        双目摄像头时，拼接两帧图像
        """
        #若图像数据全为0，说明获取的图像不正确，这时大小可能与另一张的不同，修改其大小与正常的相同，以便拼接
        #判断不为0的元素是否少于一定数量，少于则说明图的数据像基本都是0
        f1 = numpy.zeros((self.height,self.width,3)) if numpy.count_nonzero(frame1) < 666 else frame1
        f0 = numpy.zeros((self.height,self.width,3)) if numpy.count_nonzero(frame0) < 666 else frame0
        return numpy.hstack((f1,f0))

    def nextFrame(self):                              
        """
        获取下一帧,ismodechanged提示是否要转换模式，若为True，将先转换模式
        这里双目时，令大小为320*240，单目时令大小为640*480
        '0' ==> 1（开） 0（开）
        '1' ==> 1（开） 0（关）
        '2' ==> 1（关） 0（开）
        返回元组，(rs1,rs0,frame1,frame0)
        """             
        rs1 = rs0 = False
        frame1 = frame0 = None
        try:  
            if self.need2change:#需要模式转换 
                self.need2change = False                  #消费掉此次转换命令  
                self.clean() 
                if self.mode == '0':
                    self.width,self.height = 320,240
                    self.openCAM(1)
                    self.openCAM(0)        
                    rs1,frame1 = self.capture1.read()
                    rs0,frame0 = self.capture0.read()                         
                elif self.mode == '1':
                    self.width,self.height = 640,480
                    self.openCAM(1)      
                    rs1,frame1 = self.capture1.read()   
                    rs0,frame0 = True,None            #不获取也返回True，使得 rs1 & rs0 为True ，以便后续判断 
                elif self.mode == '2':               
                    self.width,self.height = 640,480
                    self.openCAM(0)
                    rs1,frame1 = True,None
                    rs0,frame0 = self.capture0.read()            
                else:
                    self.mode = '2'
                    self.width,self.height = 640,480                   
                    self.openCAM(0)
                    rs1,frame1 = True,None
                    rs0,frame0 = self.capture0.read() 
                alertfather('mode:{0};fps:{1}'.format(self.mode,self.fps))   #告知父进程，修改成功
            else:#直接读取下一帧
                if self.mode == '0':        
                    rs1,frame1 = self.capture1.read()
                    rs0,frame0 = self.capture0.read()                         
                elif self.mode == '1':    
                    rs1,frame1 = self.capture1.read()   
                    rs0,frame0 = True,None            #不获取也返回True，使得 rs1 & rs0 为True ，以便后续判断 
                elif self.mode == '2':   
                    rs1,frame1 = True,None
                    rs0,frame0 = self.capture0.read()                      
        except Exception:
                alertfather('Capture error')
            
        return (rs1,rs0,frame1,frame0)

    def sendframe(self,frame): 
        """
        发送一帧图像
        """                                                  
        try:
            result, imgencode = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY),90])   #编码图像
            data = numpy.array(imgencode)
            stringData = data.tostring()                                    #转换为二进制字符串发送
            stringLenData = str(len(stringData)).ljust(16)

            #等待客户端接收图片的端口发来可以传图片的信号
            self.socket.recv(1)
            self.socket.send(stringLenData)                                 #先发送16字节的长度用来给接收端识别图片大小
            self.socket.send(stringData)                                    #再发送图像数据              
        except Exception:
            return False
        else:
            return True

    def startSendFrame(self,show=False):
        """
        获取视频帧,show:是否弹出窗体显示,flag:获取模式，0 双目 1 左边 2 右边
        """  
        #self.getOrder()
        thread.start_new_thread(self.getOrder,())         #启动一个线程获取主进程的order      
        #连接客户端的接收图片的端口
        try:
            self.socket.connect((self.host,self.port))
            tellfather("I connect successfully.[serve to {0}:{1}.mode:{2}]\n".format(self.host,self.port,self.mode))
        except socket.error: 
            if PCwith360wifiDebug:
                try:
                    #电脑测试客户端接收图片的ip是127.0.0.1，而本地命令行服务器获取得到的是360无线WIFI的IP
                    #两个属于不同的网卡设备，即需要连接到正确的正在监听self.port端口的ip地址：127.0.0.1
                    self.socket.connect(('127.0.0.1',self.port))        
                except socket.error:   
                    alertfather('Socket error')
                    return                       
            else:
                alertfather('Socket error')
                return
        
        #初始默认fps
        self.fps = 15 if self.mode == '0' else 30
        #读取第一帧
        rs1,rs0,frame1,frame0 = self.nextFrame()

        if rs1 & rs0:
            tellfather("Now I'm sending images.[serve to {0}:{1}.mode:{2}]\n".format(self.host,self.port,self.mode))
        else:
            tellfather("Sorry,I can't fetch image.[serve to {0}:{1}.mode:{2}]\n".format(self.host,self.port,self.mode))

        #该进程实际工作
        while rs1 & rs0:  
            waittime = int(round(1000 // self.fps * 0.9))   #帧数控制时间，*0.9是为了大概减少一些时间，
                                                            #因为获取图像时有些操作也消耗了时间                                                      
                     
            #发送图像，获取下一帧图像，帧数控制(waitKey等待时间)
            if self.mode == '0':

                if not self.sendframe(self.montage(frame1,frame0)): alertfather('Send error');break
                if show:
                    cv2.imshow('CAM1',frame1)
                    cv2.imshow('CAM0',frame0)

            elif self.mode == '1':
                if not self.sendframe(frame1): alertfather('Send error');break
                if show:
                    cv2.imshow('CAM1',frame1)
                
            elif self.mode == '2':
                if not self.sendframe(frame0): alertfather('Send error');break
                if show:
                    cv2.imshow('CAM0',frame0)


            with self.mutex:
                if self.order != None:                                  
                    order, self.order = self.order, None                    #消费self.order
                                                                            #执行命令
                    if order == 'stop':                                     #退出命令
                        alertfather('Normal exit')                     #告诉父进程本子进程正常退出
                        break    
                    elif order[:4] == 'mode':                               #改变模式命令 'mode:0;fps:30'
                        try:
                            self.mode = order[5]                            #改变模式
                            self.fps = order.split(':')[-1]                 #改变fps
                            self.need2change = True                           
                        except Exception:
                            alertfather('Capture error')
                            break
            #帧数控制
            cv2.waitKey(waittime)
            #读取下一帧
            rs1,rs0,frame1,frame0 = self.nextFrame()

        else:#获取下一帧得到的图像为空则跳出循环，执行到这里，执行break才是正常退出，否则退出异常
            alertfather('Capture error')         #获取图像失败，告诉父进程
        
        self.clean()                             #循环结束后清理工作
        

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
    host = sys.argv[1] if len(sys.argv)==4 else '172.28.32.1'
    port = sys.argv[2] if len(sys.argv)==4 else '36889'
    mode = sys.argv[3] if len(sys.argv)==4 else '0'   

    imgsender = ImgSender(host,port,mode)
    imgsender.startSendFrame(False)
    
if __name__ == '__main__':    
    run()
    
    
    