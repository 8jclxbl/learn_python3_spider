#In[1]
import requests
import json
import re
from bs4 import BeautifulSoup

#In[2]
url = 'http://bang.dangdang.com/books/'
def getPartion(url):
    resp = requests.get(url).text
    soup = BeautifulSoup(resp,'lxml')
    titles = soup.find('div',{'class':'sub'})
    titleItems = titles.find('ul').findAll('li')
    titleDict = {}
    for i in titleItems:
        titleDict[i.text] = i.find('a').get('href')
    return titleDict

#In[4]
timeInteval = {
    '24h':'24hours',
    '7d':'recent7',
    '30d':'recent30',
}
#榜单统计前500，一页20items，共计25页
def subffixTimeIntv(ti,page):
    return '01.00.00.00.00.00-{0}-0-0-1-{1}'.format(ti,page)

#In[5]
tempUrl = 'http://bang.dangdang.com/books/bestsellers'
def getPageItems(baseUrl,page,ti):

    if baseUrl[-1] == '/':
        currentUrl = baseUrl + subffixTimeIntv(timeInteval[ti],page)
    else:
        currentUrl = baseUrl + '/' + subffixTimeIntv(timeInteval[ti],page)

    pageResp = requests.get(currentUrl).text
    pageSoup = BeautifulSoup(pageResp,'lxml')

    pageDict = {}
    topList = pageSoup.find('ul',{'class':'bang_list'})
    items = topList.findAll('li')

    for i in items:
        itemDict = {}
        
        nameDiv = i.find('div',{'class':'name'})
        itemDict['name'] = nameDiv.text
        itemDict['url'] = nameDiv.a.get('href')
        priceDiv = i.find('div',{'class':'price'})
        itemDict['priceNow'] = priceDiv.p.find('span',{'class':'price_n'}).text
        pageDict[i.div.text] = itemDict

    return pageDict

#In[6]
def pageInfoGen(baseUrl,ti,totalPage = 25):
    for i in range(1,totalPage+1):
        yield getPageItems(baseUrl,i,ti)

def getAllPages(baseUrl,ti):
    total = {}
    #curPage = 0
    try:
        for i in pageInfoGen(baseUrl,ti):
            #curPage += 1
            #print(curPage)
            total.update(i)
    except AttributeError:
        return {}
    return total


#In[7]
partion = getPartion(url)
print(partion)

#In[8]
allData = {}
for k,v in partion.items():
    print(k)
    allData[k] = getAllPages(v,'7d')

jsonData = json.dumps(allData)
with open('dangdangTop500All.json','w',encoding='UTF-8') as f:
    f.write(jsonData)
