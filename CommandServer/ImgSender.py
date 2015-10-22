﻿"""
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
        self.mutex = thread.allocate_lock()                               #锁

        self.socket = socket.socket(socket.AF_INET,socket.SOCK_STREAM)    #连接要接收图像的客户端的端口
        self.startGetOrder()
        
    def startGetOrder(self):
        """
        启动一个线程获取主进程的order
        """
        def getOrder():#生产者
            while 1:
                rs = input()
                with self.mutex:
                    tellfather('receive from father process:{0}'.format(rs))
                    self.order = rs
        thread.start_new_thread(getOrder,())

    def startSendFrame(self,show=False):
        """
        获取视频帧,show:是否弹出窗体显示,flag:获取模式，0 双目 1 左边 2 右边
        """
        waittime = int(round(1000 // self.fps * 0.9))           #帧数控制时间，*0.9是为了大概减少一些时间，
                                                                #因为获取图像时有些操作也消耗了时间
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),90]       #视频编码参数

        def fetched(rs1,rs0):                                   #判断获取图像是否成功
            if self.mode == '0':
                return rs1 & rs0
            elif self.mode == '1':
                return rs1
            elif self.mode == '2':
                return rs0

        def changemode(mode):                              #转换模式
            """
            这里双目时，令大小为320*240，单目时令大小为640*480
            '0' ==> 1（开） 0（开）
            '1' ==> 1（开） 0（关）
            '2' ==> 1（关） 0（开）
            """
            self.clean()
            self.mode=mode
            if self.mode=='0':
                self.width,self.height=320,240
                self.openCAM(1)  
                self.openCAM(0)               
            elif self.mode=='1':
                self.width,self.height=640,480
                self.openCAM(1)
            elif self.mode=='2':
                self.width,self.height=640,480
                self.openCAM(0)
            with self.mutex:
                logger.info('change mode to {}'.format(self.mode))

        def sendframe(frame):                                                   #发送一帧图像
            try:
                result, imgencode = cv2.imencode('.jpg', frame, encode_param)   #编码图像
                data = numpy.array(imgencode)
                stringData = data.tostring()                                    #转换为二进制字符串发送
                stringLenData = str(len(stringData)).ljust(16)
                self.socket.send(stringLenData)                                 #先发送16字节的长度用来给接收端识别图片大小
                self.socket.send(stringData)                                    #再发送图像数据
                if stringData < 1024:
                    return False
                else:
                    return True
            except Exception:
                return False


        #连接客户端的接收图片的端口
        try:
            self.socket.connect((self.host,self.port))
            tellfather('I connect successfully to {0}:{1}'.format(self.host,self.port))
        except socket.error: 
            if PCwith360wifiDebug:
                try:
                    #电脑测试客户端接收图片的ip是127.0.0.1，而本地命令行服务器获取得到的是360无线WIFI的IP
                    #两个属于不同的网卡设备，即需要连接到正确的正在监听self.port端口的ip地址：127.0.0.1
                    self.socket.connect(('127.0.0.1',self.port))        
                except socket.error:   
                    tellfather('Socket error')
                    return                       
            else:
                tellfather('Socket error')
                return

        #第一帧
        rs1 = rs2 = False
        frame1 = frame0 = None
        try:           
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
            elif self.mode == '2':                
                self.width,self.height = 640,480
                self.openCAM(0)
                rs0,frame0 = self.capture0.read()                
            else:
                self.mode = '2'
                self.width,self.height = 640,480
                self.openCAM(0)
                rs0,frame0 = self.capture0.read()                  
        except Exception:
                tellfather('Capture error') 
         
        
        #该函数执行于子进程时，使用ifsucceeded函数就死在这了，不懂什么情况
        #所以只能不调用函数了
        #succeeded = fetched(rs1,rs0)
        #tellfather('run here {0}'.format(initsucceeded))
        if self.mode == '0':
            succeeded = rs1 & rs0
        elif self.mode == '1':
            succeeded = rs1
        elif self.mode == '2':
            succeeded = rs0

        if succeeded:
            tellfather("Now I'm sending images to {0}:{1}.format(self.host,self.port)")
        else:
            tellfather("Sorry,I can't fetch image.")

        #该进程实际工作
        #while fetched(rs1,rs0):
        while succeeded:                                                        
            with self.mutex:
                if self.order != None:                                  
                    order, self.order = self.order, None                    #消费self.order
                                                                            #执行命令
                    if order == 'stop':                                     #退出命令
                        tellfather('Normal exit')                     #告诉父进程本子进程正常退出
                        break    
                    elif order[:4] == 'mode':                               #改变模式命令 
                        try:
                            changemode(order[5])                            #改变模式
                        except Exception:
                            tellfather('Capture error')
                            break

                    
            #发送图像，获取下一帧图像，帧数控制(waitKey等待时间)
            if self.mode == '0':
                if not sendframe(frame1): tellfather('Send error');break
                cv2.waitKey(waittime/2)
                if not sendframe(frame0): tellfather('Send error');break
                if show:
                    cv2.imshow('CAM1',frame1)
                    cv2.imshow('CAM0',frame0)

                rs1,frame1 = self.capture1.read()
                rs0,frame0 = self.capture0.read()
                succeeded = rs1 & rs0
                cv2.waitKey(waittime/2)
            elif self.mode == '1':
                if not sendframe(frame1): tellfather('Send error');break
                if show:
                    cv2.imshow('CAM1',frame1)

                rs1,frame1 = self.capture1.read()
                succeeded = rs1
                cv2.waitKey(waittime)
            elif self.mode == '2':
                if not sendframe(frame0): tellfather('Send error');break
                if show:
                    cv2.imshow('CAM0',frame0)

                rs0,frame0 = self.capture0.read()
                succeeded = rs0
                cv2.waitKey(waittime)

        else:#获取下一帧得到的图像为空则跳出循环，执行到这里，执行break才是正常退出，否则退出异常
            tellfather('Capture error')          #获取图像失败，告诉父进程
        
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
    host = sys.argv[1] if len(sys.argv)==4 else '172.28.32.1'
    port = sys.argv[2] if len(sys.argv)==4 else '36889'
    mode = sys.argv[3] if len(sys.argv)==4 else '2'   

    imgsender = ImgSender(host,port,mode)
    imgsender.startSendFrame(False)
    
if __name__ == '__main__':    
    run()
    
    
    