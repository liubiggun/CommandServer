import cv2
import os

def CulExeTime(label='',trace=True):
    """
    一个计时函数装饰器
    函数装饰器，此处为了在封闭作用域内保存参数，并返回嵌套的实际的函数装饰器类
    """
    class CulExeTimer(object):
        """
        包装器类（函数装饰器类）
        """
        def __init__(self,func):
            """
            构造函数在 @decorator 时调用，使得func=CulExeTime(label,trace)(func)
            => 形成了封闭作用域并保持了label和trace的值 且 func=CulExeTimer(func)
            构造时存储原func函数，并定义所需要的额外属性
            """
            self.func=func
            self.thistime=0
            self.totaltime=0

        def __call__(self,*args,**kargs):
            """
            重载__call__操作符函数使得CulExeTimer的实例（func）在外部执行
            func(*args,**kargs)时调用此方法，从而可以使用实例中的属性进行比
            原func函数更丰富的操作           
            """
            start=time.clock()
            rs=self.func(*args,**kargs)
            self.thistime=time.clock()-start
            self.totaltime+=self.thistime
            if trace:
                print('{0} {1}:Elapsed:{2:.5f}, Total:{3:.5f}'.format(
                    label,self.func.__name__,self.thistime,self.totaltime))
            return rs

        def __get__(self,instance,owner):
            """
            利用描述符，它可以保存装饰器的状态（self）及最初的类实例
            （instance），即调用instance.f(...)时，执行f._get__(self,instance,owner),
            self为f（已经变成CulExeTimer类的实例的f），instance即为最初的类实例
            owner为主体类
            """
            #保存self和instance，并触发self.__call__，将instance有效传递        
            return lambda *args,**kargs:self(instance,*args,**kargs)
    return CulExeTimer

class CvCapture:
    """
    一个用opencv库获取双目摄像头图像并显示的类
    size:设置摄像头图像的宽高
    """
    def __init__(self,size=(320,240),fps=10):
        self.capture1 = None                    #要显示时才初始化为cv2.VideoCapture
        self.capture0 = None

        self.width = size[0]
        self.height = size[1]
        self.fps = fps       

    def setFPS(self,value):
        """
        设置帧数
        """
        #self.capture1.set(cv2.cv.CV_CAP_PROP_FPS,value)
        #self.capture0.set(cv2.cv.CV_CAP_PROP_FPS,value)
        self.fps = value

    def getFPS(self):
        #fps1=self.capture1.get(cv2.cv.CV_CAP_PROP_FPS)
        #fps0=self.capture0.get(cv2.cv.CV_CAP_PROP_FPS)
        print(self.fps)
        return self.fps

    #@CulExeTime()
    def openCAM(self,devid):
        """
        打开摄像头,devid是摄像头id，大小设为self.size的大小
        """
        if devid==1:
            self.capture1 = cv2.VideoCapture(1)
            self.capture1.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,self.width)
            self.capture1.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,self.height)
            return self.capture1
        elif devid==0:
            self.capture0 = cv2.VideoCapture(0)
            self.capture0.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,self.width)
            self.capture0.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,self.height)            
            return self.capture0

    def closeCAM(self,devid):
        """
        关闭摄像头，devid是摄像头id
        """
        if devid==1:
            self.capture1 and self.capture1.release()
        elif devid==0:
            self.capture0 and self.capture0.release()

    def encodeJPG(self,frame):
        """
        将一幅图片编码成JPG图片，返回编码后数据的(长度，二进制字符串数据)
        """      
        encode_param = [int(cv2.IMWRITE_JPEG_QUALITY),95]       #视频编码参数
        result, imgencode = cv2.imencode('.jpg', frame, encode_param)       #编码图像
        data = numpy.array(imgencode)
        stringData = data.tostring()                                        #转换为二进制字符串发送
        return (len(stringData),stringData)

    def oneShow(self,devid):
        """
        只显示一个摄像头的图片
        """
        waittime = 1000 // self.fps
        capture = self.openCAM(devid)
        if capture.isOpened():
            rs,frame = capture.read()
            while rs:
                cv2.imshow('CAM'+str(devid),frame)
                rs,frame = capture.read()
                if cv2.waitKey(waittime) == 27:
                    self.clean()
                    break   
            else:
                self.clean()

    def overlapShow(self):
        """
        交叉显示两个摄像头的图片（解决USB带宽不足时导致的一个摄像头不能用的一个workaround）
        但是发现cv2.VideoCapture类初始化太耗时间，此法不妥
        """
        cv2.namedWindow('CAM1')
        cv2.namedWindow('CAM0')
        #waittime = 1000 // self.fps // 2                                    #等待时间
        waittime=1

        id=1    #记录当前打开的摄像头
        capture = self.openCAM(id)
        rs,frame = capture.read()
        while rs:
            cv2.imshow('CAM'+str(id),frame)
            self.closeCAM(id)                                               #关闭当前的摄像头
            id=0 if id==1 else 1                                            #打开另一个摄像头
            capture = self.openCAM(id)
            rs,frame = capture.read()

            if cv2.waitKey(waittime) == 27:
                    self.clean()
                    break
        else:
            self.clean()
    
    def easyShow(self):
        """
        开始简单地获取并显示摄像头图片，esc退出循环
        """
        waittime = 1000 // self.fps
        self.openCAM(1)
        self.openCAM(0)
        if self.capture1.isOpened() & self.capture0.isOpened():
            rs1,frame1 = self.capture1.read()
            rs0,frame0 = self.capture0.read()
            while rs1 & rs0:
    
                cv2.imshow('show1',frame1)
                cv2.imshow('show0',frame0)

                rs1,frame1 = self.capture1.read()
                rs0,frame0 = self.capture0.read()
                
                if cv2.waitKey(waittime) == 27:
                    self.clean()
                    break 
            else:
                self.clean()  

    def clean(self):
        """
        退出前的清理工作
        """
        self.capture1 and self.capture1.release()
        self.capture0 and self.capture0.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    cap = CvCapture(size=(640,480),fps=30)
    cap.easyShow()
