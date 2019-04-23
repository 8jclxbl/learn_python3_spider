import time 
import requests
from PIL import Image

from selenium import webdriver
from selenium.webdriver import ActionChains
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

import re
from io import BytesIO
import numpy as np

#获取当前页面的HTML的指定div的信息
def getInfoDivs(dirver, divName):
    bs = BeautifulSoup(dirver.page_source,'lxml')
    return  bs.findAll('div',{'class':divName})

#获取验证码图片的url
#利用正则表达式
def findImageUrl(bgDiv):
    info = re.findall('background-image:\surl\("(.*?)"\)',bgDiv.get('style'))
    return info[0]

#从div信息中抽取图像片段的偏移
def extractLocation(moveDivs):
    locationList = []
    for div in moveDivs:
        location = {}
        info = re.findall('background-position:\s(.*?)px\s(.*?)px',div.get('style'))
        location['x'] = int(info[0][0])
        location['y'] = int(info[0][1])
        locationList.append(location)
    return locationList

#requests获取图片，数据为二进制的stream
def getImageStream(imageUrl):
    stream = requests.get(imageUrl.replace('webp','jpg')).content
    return BytesIO(stream)

#根据前面从HTML中读取的位置信息和get到的图片数据，拼接成完整图片
def mergeImage(imageFile, locationList):
    yValues = set()
    #事实上，验证码滑窗图片的大小为320*116，这里的yValues取值为0和58
    for location in locationList:
        yValues.add(location['y'])

    if len(yValues) != 2:
        raise ValueError

    upMove = min(yValues)
    downMove = max(yValues)
    
    upList = []
    downList = []

    image = Image.open(imageFile)

    for location in locationList:
        if location['y'] == upMove:
            #返回图片的一个指定区域
            im = image.crop((abs(location['x']),abs(upMove),abs(location['x']) + 10, 2*abs(upMove)))
            upList.append(im)
        if location['y'] == downMove:
            im = image.crop((abs(location['x']),abs(downMove),abs(location['x']) + 10, abs(upMove)))
            downList.append(im)

    #图片的偏移步长为10
    newImage = Image.new('RGB',image.size)
    offset = 0
    for im in upList:
        newImage.paste(im,(offset,abs(downMove)))
        offset += 10
    offset = 0
    for im in downList:
        newImage.paste(im,(offset,abs(upMove)))
        offset += 10
    return newImage

#获取需要拖动到的距离
#原始代码是使用遍历两张图中的每个像素的方法，这里采用的是利用numpy转化为数组再相减
#设定阈值后得到要拖到的区域
#由于只可能水平移动，返回水平偏移量
def getDistance(bg,fullBg):
    bgData = np.array(bg)
    fullBgData = np.array(fullBg)

    residul = bgData - fullBgData
    resCh1 = residul[:,:,1]
    
    resCh1CutUp = np.where(resCh1 < 222,resCh1,0)
    resCh1CutDown = np.where(resCh1CutUp > 50,resCh1CutUp,0)
    index = np.argwhere(resCh1CutDown != 0)
    (luy,lux,dry,drx) = np.min(index[:,0]),np.min(index[:,1]),np.max(index[:,0]),np.max(index[:,1])

    return np.min(index[:,1])

#为了防止直接移动使得系统发现是脚本，构建一个路径
def getPath(distance,time = 2,timeStep = 0.1):
    steps = time/timeStep
    rate = round(distance * 6 /(steps ** 3),6)
    f = lambda x : rate * (steps/2.0 -x/3.0) * (x**2)
    #g = lambda x : rate * (steps - x) * x

    path = []
    cur = 0
    curPosition = 0
    lastPosition = 0

    while cur <= steps:
        curPosition = f(cur)
        move = curPosition - lastPosition
        lastPosition = curPosition
        path.append(round(move,10))
        cur += 1
    print(path)
    return path

#driver驱动来拖动按钮
def start_drag(driver, distance, timeTotal = 0.5, timeStep = 0.1):
    #等待指定元素定位成功
    knob = WAIT.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#gc-box > div > div.gt_slider > div.gt_slider_knob.gt_show")))
    #构建动作链
    #点击，移动指定距离，松开
    path = getPath(distance,timeTotal,timeStep)
    ActionChains(driver).click_and_hold(knob).perform()
    for x in path:
        ActionChains(driver).move_by_offset(xoffset=x, yoffset=0).perform()
    time.sleep(0.1)
    ActionChains(driver).release(knob).perform()


url = 'https://passport.bilibili.com/login'
driver = webdriver.Firefox()
WAIT = WebDriverWait(driver, 10)

driver.get(url)
slider = WAIT.until(EC.element_to_be_clickable(
    (By.CSS_SELECTOR,"#gc-box > div.gt_holder.gt_float > div.gt_slider > div.gt_slider_knob.gt_show")
))

bgDivs = getInfoDivs(driver,'gt_cut_bg_slice')
fullBgDivs = getInfoDivs(driver,'gt_cut_fullbg_slice')
bgUrl = findImageUrl(bgDivs[0])
fullBgUrl = findImageUrl(fullBgDivs[0])
bgLocationList = extractLocation(bgDivs)
fullBgLocationList = extractLocation(fullBgDivs)
bgImage = getImageStream(bgUrl)
fullBgImage = getImageStream(fullBgUrl)
bgProcessed = mergeImage(bgImage,bgLocationList)
fullBgProcessed = mergeImage(fullBgImage,fullBgLocationList)

distance = getDistance(bgProcessed,fullBgProcessed)
print(distance)
start_drag(driver,distance)