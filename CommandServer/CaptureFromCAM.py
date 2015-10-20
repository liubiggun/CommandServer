import cv2
import os

class CvCapture:
    """
    一个用opencv库获取双目摄像头图像并保存的类
    size:设置摄像头图像的宽高
    """
    def __init__(self,size=(320,240),fps=10):
        self.capture1 = cv2.VideoCapture(1)
        self.capture0 = cv2.VideoCapture(0)

        self.size = size
        self.setWH(size[0],size[1])
        self.fps = fps       
        
        #self.window1 = 'show1'
        #self.window0 = 'show0'

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

    def setWH(self,width,height):
        """
        设置摄像头获取图像的宽高
        """
        self.capture1.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,width)
        self.capture1.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,height)

        self.capture0.set(cv2.cv.CV_CAP_PROP_FRAME_WIDTH,width)
        self.capture0.set(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT,height)

        self.size = (width,height)       
    
    def show(self):
        """
        开始捕捉图片，esc退出循环
        """
        #cv2.namedWindow(self.window1)
        #cv2.namedWindow(self.window0) 
        waittime = 1000 // self.fps
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

    def clean(self):
        """
        退出前的清理工作
        """
        self.capture1.release()
        self.capture0.release()
        cv2.destroyAllWindows()

if __name__ == '__main__':
    cap = CvCapture(size=(640,480),fps=30)
    cap.show()

