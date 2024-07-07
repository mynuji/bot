import sys
import os
import feedparser
import telepot
import json
import random
import string
from os.path import expanduser
from urllib import parse
from apscheduler.schedulers.background import BackgroundScheduler
from telepot.delegate import per_chat_id, create_open, pave_event_space
from bs4 import BeautifulSoup as bs
import requests


CONFIG_FILE = 'setting.json'
USER_AGENT = { 'User-Agent': 'Mozilla/5.0 (Linux; Android 12; SM-G975F) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/114.0.5735.130 Mobile Safari/537.36 OPR/76.0.4027.73219' }


class DelugeAgent:

    def __init__(self, sender):
        self.STATUS_SEED = 'Seeding'
        self.STATUS_IDLE = 'Idle'
        self.STATUS_DOWN = 'Downloading'
        self.STATUS_ERR = 'Error'  # Need Verification
        self.weightList = {}
        self.sender = sender

    def download(self, item):
        os.system("deluge-console add " + item)

    def getCurrentList(self):
        return os.popen('deluge-console info').read()

    def getDirList(self):
        #return os.popen('ls -l /home/igi/bot/torrent').read()
        return os.popen('ls -l ' + DOWNLOAD_PATH).read()

    def printElement(self, e):
        outString = 'NAME: ' + e['title'] + \
            '\n' + 'STATUS: ' + e['status'] + '\n'
        outString += 'PROGRESS: ' + e['progress'] + '\n'
        outString += '\n'
        return outString


    def parseList(self, result):
        if not result:
            return
        outList = []
        for entry in result.split('\n \n'):
            title = entry[entry.index('Name:') + 6:entry.index('ID:') - 1]
            status = entry[entry.index('State:'):].split(' ')[1]
            ID = entry[entry.index('ID:') + 4:entry.index('State:') - 1]
            if status == self.STATUS_DOWN:
                progress = entry[entry.index(
                    'Progress:') + 10:entry.index('% [') + 1]
            else:
                progress = '0.00%'
            element = {'title': title, 'status': status,
                       'ID': ID, 'progress': progress}
            outList.append(element)
        return outList

    def isOld(self, ID, progress):
        """weightList = {ID:[%,w],..}"""
        if ID in self.weightList:
            if self.weightList[ID][0] == progress:
                self.weightList[ID][1] += 1
            else:
                self.weightList[ID][0] = progress
                self.weightList[ID][1] = 1
            if self.weightList[ID][1] > 3:
                return True
        else:
            self.weightList[ID] = [progress, 1]
            return False
        return False

    def check_torrents(self):
        currentList = self.getCurrentList()
        outList = self.parseList(currentList)
        if not bool(outList):
            self.sender.sendMessage('The torrent List is empty')
            scheduler.remove_all_jobs()
            self.weightList.clear()
            return
        for e in outList:
            if (e['status'] == self.STATUS_SEED): 
               self.sender.sendMessage(
                  'Download completed: {0}'.format(e['title']))
               self.removeFromList(e['ID'])
            elif e['status'] == self.STATUS_ERR:
               self.sender.sendMessage(
                    'Download canceled (Error): {0}\n'.format(e['title']))
               self.removeFromList(e['ID'])
            else:
               if self.isOld(e['ID'], e['progress']):
                   self.sender.sendMessage(
                       'Download canceled (pending): {0}\n'.format(e['title']))
                   self.removeFromList(e['ID'])
        return

    def removeFromList(self, ID):
        if ID in self.weightList:
            del self.weightList[ID]
        os.system("deluge-console del " + ID)


class TransmissionAgent:

    wgetCmd = "wget"

    def __init__(self, sender):
        self.STATUS_SEED = 'Seeding'
        self.STATUS_ERR = 'Error'  # Need Verification
        self.weightList = {}
        self.sender = sender
        cmd = 'transmission-remote '
        if TRANSMISSION_ID_PW:
            cmd = cmd + '-n ' + TRANSMISSION_ID_PW + ' '
        else:
            cmd = cmd + '-n ' + 'transmission:transmission' + ' '
        self.transmissionCmd = cmd

    def download(self, magnet):
        if TRANSMISSION_PORT:
            pcmd = '-p ' + TRANSMISSION_PORT + ' '
        else:
            pcmd = ''
        if DOWNLOAD_PATH:
            wcmd = '-w ' + DOWNLOAD_PATH + ' '
        else:
            wcmd = ''
        print("다운로드 : " + self.transmissionCmd + pcmd + wcmd + '-a ' + magnet)
        os.system(self.transmissionCmd + pcmd + wcmd + '-a ' + magnet)


    def torrent_file_download(self, host, path, name):
        output = '-O "' + TORRENT_FILE_PATH + name +'.torrent"'
        retry = ' --tries=5'
        s = self.wgetCmd + " " + output + " '" + host+path + "'"+ retry
        print(s)
        os.system(s)

    def getDirList(self):
        return os.popen('ls -l '+ DOWNLOAD_PATH).read()

    def getCurrentList(self):
        l = os.popen(self.transmissionCmd + '-l').read()
        rowList = l.split('\n')
        if len(rowList) < 4:
            return
        else:
            return l

    def parseDirList(self, result):
        if not result:
            return
        outList = []

        print(result)
        resultlist = result.split('\n')
        i=0
        for entry in resultlist:
          i=i+1
          if i==1:
            continue
          entrylist = entry.split(' ')

          e = ''.join(entrylist[9:])
#          j=0
#          for e in entrylist:
#            j=j+1
#            if j<10:
#              continue
          print('e: ' + e)
          outList.append(e)  
        return outList

    def printDirElement(self, e):
        outString = 'NAME: ' + e['title'] + \
            '\n' + 'STATUS: ' + e['status'] + '\n'
        outString += 'PROGRESS: ' + e['progress'] + '\n'
        outString += '\n'
        return outString

    def printElement(self, e):
        outString = 'NAME: ' + e['title'] + \
            '\n' + 'STATUS: ' + e['status'] + '\n'
        outString += 'PROGRESS: ' + e['progress'] + '\n'
        outString += '\n'
        return outString

    def parseList(self, result):
        if not result:
            return
        outList = []
        resultlist = result.split('\n')
        titlelist = resultlist[0]
        resultlist = resultlist[1:-2]
        for entry in resultlist:
            title = entry[titlelist.index('Name'):].strip()
            status = entry[titlelist.index(
                'Status'):titlelist.index('Name') - 1].strip()
            progress = entry[titlelist.index(
                'Done'):titlelist.index('Done') + 4].strip()
            id_ = entry[titlelist.index(
                'ID'):titlelist.index('Done') - 1].strip()
            if id_[-1:] == '*':
                id_ = id_[:-1]
            element = {'title': title, 'status': status,
                       'ID': id_, 'progress': progress}
            outList.append(element)
        return outList

    def removeFromList(self, ID):
        if ID in self.weightList:
            del self.weightList[ID]
        os.system(self.transmissionCmd + '-t ' + ID + ' -r')

    def isOld(self, ID, progress):
        """weightList = {ID:[%,w],..}"""
        if ID in self.weightList:
            if self.weightList[ID][0] == progress:
                self.weightList[ID][1] += 1
            else:
                self.weightList[ID][0] = progress
                self.weightList[ID][1] = 1
            if self.weightList[ID][1] > 3:
                return True
        else:
            self.weightList[ID] = [progress, 1]
            return False
        return False

    def check_torrents(self):
        currentList = self.getCurrentList()
        outList = self.parseList(currentList)
        if not bool(outList):
            self.sender.sendMessage('The torrent List is empty')
            scheduler.remove_all_jobs()
            self.weightList.clear()
            return
        for e in outList:
            if e['status'] == self.STATUS_SEED:
                self.sender.sendMessage(
                    'Download completed: {0}'.format(e['title']))
                self.removeFromList(e['ID'])
            elif e['status'] == self.STATUS_ERR:
                self.sender.sendMessage(
                    'Download canceled (Error): {0}\n'.format(e['title']))
                self.removeFromList(e['ID'])
            else:
                if self.isOld(e['ID'], e['progress']):
                    self.sender.sendMessage(
                        'Download canceled (pending): {0}\n'.format(e['title']))
                    self.removeFromList(e['ID'])
        return


class Torrenter(telepot.helper.ChatHandler):
    YES = '<OK>'
    NO = '<NO>'
    MENU0 = 'HOME'
    MENU1 = '토렌트 검색'
#    MENU3 = '검색'
    MENU1_1 = '[?] 검색할 문자열을 입력하세요'
    MENU1_2 = '[?] 다운로드할 항목을 선택하세요.'
    MENU2 = '다운로드 리스트'
    MENU3 = '파일/폴더 삭제'
    MENU4 = '토렌트 주소 변경'
    MENU4_1 = '[!] 주소를 설정했습니다.'
    STATUS_SEED = 'Seeding'
    STATUS_IDLE = 'Idle'

#    SEARCH_PARAM='/search/index?category=0&keywords='
#    downloadUrl = DOWNLOADURL
    GREETING = "[?] 메뉴를 선택하세요."
    global scheduler
    global DOWNLOAD_PATH
    global TORRENT_FILE_PATH
    global HOSTURL
    global SEARCH_PARAM

    mode = ''
    navi = []

    def __init__(self, *args, **kwargs):
        super(Torrenter, self).__init__(*args, **kwargs)
        self.agent = self.createAgent(AGENT_TYPE)

    def createAgent(self, agentType):
        if agentType == 'deluge':
            return DelugeAgent(self.sender)
        if agentType == 'transmission':
            return TransmissionAgent(self.sender)
        raise ('invalid torrent client')

    def open(self, initial_msg, seed):
        self.menu()

    def menu(self):
        mode = ''
        show_keyboard = {'keyboard': [
            [self.MENU1], [self.MENU2], [self.MENU3], [self.MENU4], [self.MENU0]]}

        self.sender.sendMessage(self.GREETING, reply_markup=show_keyboard)

    def yes_or_no(self, comment):
        show_keyboard = {'keyboard': [[self.YES, self.NO], [self.MENU0]]}
        self.sender.sendMessage(comment, reply_markup=show_keyboard)

    def tor_get_keyword(self):
        self.mode = self.MENU1_1
        self.sender.sendMessage('[?] 검색할 문자열을 입력하세요...')

    def put_menu_button(self, l):
        menulist = [self.MENU0]
        l.append(menulist)
        return l

    def isDiskEnough(self):
        stat = os.statvfs(DOWNLOAD_PATH)
        freesize = (stat.f_bavail*stat.f_bsize)/(10**9)
        if (freesize < 6):
            self.sender.sendMessage('Error: The Disk size is under 6GB: {}GB'.format(freesize))
            return False
        return True

    def tor_search(self, keyword):
        self.mode = ''
        self.sender.sendMessage('[!] 토렌토 서버를 검색하고 있습니다..')
        searchUrl = HOSTURL+SEARCH_PARAM
        print("searchUrl = " + searchUrl)

        page = requests.get(url=searchUrl + parse.quote(keyword), headers=USER_AGENT)

        print(page.text)
        soup = bs(page.text, "html.parser")
        elements = soup.select('li.tit a')

        outList = []
        self.navi = []
        self.navi.clear()

        for (i, element) in enumerate(elements):
            title = str(i+1)+"."+element.text.strip()
            href = element['href']

            print("----------------------------------")
            print(title, href)
            print("----------------------------------")
            if i==0:
              self.navi = {i:href}
            else:
              self.navi[i] = href

            templist = []
            templist.append(title)
            outList.append(templist)

#        """
#        links = soup.find_all("a")
#        """



#        i=0
#        for index, element in enumerate(elements):
#          for a in element.find_all('a'):
#            try:
#              title = a.attrs['title']
#              href = a.attrs['href']
#            except:
#              continue
#
##            print(title + " " + href)
#
#            title2 = str(i+1) + ". " + title
#            if i==0:
#              self.navi = {i:href}
#            else:
#              self.navi[i] = href
#
#            i = i+1

            
#            templist = []
#            templist.append(title2)
#            outList.append(templist)

        show_keyboard = {'keyboard': self.put_menu_button(outList)}
        self.sender.sendMessage('[!] 다운로드할 항목을 선택하세요..',
                                reply_markup=show_keyboard)
        self.mode = self.MENU1_2

    def tor_download(self, selected):
        self.mode = ''
        if not self.isDiskEnough():
            self.menu()
            return
        index = int(selected.split('.',1)[0]) - 1
        href = self.navi[index]
        name = selected.split('.',1)[1]

#        print('본문:'+HOSTURL + href)

        page = requests.get(url=HOSTURL + href, headers=USER_AGENT)
        soup = bs(page.text, "html.parser")

        tables = soup.select("table.notice_table")
        for table in tables:
          trs = table.find_all('tr')
          flag = False
          for tr in trs:
            print(tr)
            if not flag:
              th = tr.find('th')
              if th is None:
                break
              print(th)

              if '.srt' in th.text:
#                print('skip')
                break
              print('다운로드할 내용: '+th.text)
              
              flag = True
              continue
            else:
              links = tr.findAll('a')
              if not links:
                continue
              print(links)
              
              href=None
              for link in links:
                href = link.attrs['href']
                if "magnet:" in href:
                  break
                if '/topic/download/' in href:
                  break
                break
              if href is None:
                continue
              print('링크: ' + href)
              break 
          if flag == False:
#            print("skip")
            continue
          else:
            break


        print("-----------------------")
        print("href: " + href)

        if "/topic/download/" in href:
          self.agent.torrent_file_download(HOSTURL, href, name.strip())
        if "magnet:" in href:
          self.agent.download(href)

        self.sender.sendMessage('[!] '+ name.strip() + '파일 다운로드를 시작합니다')

        self.navi.clear()
        self.menu()


        """
        links = soup.select("a.bbs_btn1")
        flag = False
        for a in links:
          try:
            href= a.attrs['href']
            print('다운로드: '+href)
          except:
            continue
          
          if "/topic/download/" in href:
            self.agent.torrent_file_download(self.hostUrl, href, name.strip())
            self.sender.sendMessage('[!] '+ name.strip() + '파일 다운로드를 시작합니다')
            self.navi.clear()
            flag = True
            break

        if not flag:
          links = soup.select("a.bbs_btn2")
          for a in links:
            try:
              href = a.attrs['href']
              text = a.text
              print('다운로드: '+href+ "  "+text)
            except:
              continue
            if "magnet:" in href:
              self.agent.download(href)
              self.sender.sendMessage('[!] '+ name.strip() + '파일 다운로드를 시작합니다')
              self.navi.clear()
        self.menu()
        """

    def dir_show_list(self):
        self.mode = ''
        self.sender.sendMessage('[!] 삭제할 파일/폴더를 선택하세요.')
        result = self.agent.getDirList()
        if not result:
          self.sender.sendMessage('[X] 삭제할 파일/폴더가 없습니다.')
          self.menu()
          return
        outList = self.agent.parseDirList(result)
        for e in outList:
          print(e)
          self.sender.sendMessage(self.agent.printDirElement(e))

    def tor_show_list(self):
        self.mode = ''
        self.sender.sendMessage('[!] 다운로드 리스트를 출력합니다..')
        result = self.agent.getCurrentList()
        if not result:
            self.sender.sendMessage('[X] 다운로드 리스트가 없습니다.')
            self.menu()
            return
        outList = self.agent.parseList(result)
        for e in outList:
            print("status: "+e['status'])
            print("progress: "+e['progress'])
            print("ID: "+e['ID'])

            print(self.agent.printElement(e))
            self.sender.sendMessage(self.agent.printElement(e))
            if (e['status'] == self.STATUS_SEED) or (e['status'] == self.STATUS_IDLE) :
              if e['progress'] == "100%":
                self.agent.removeFromList(e['ID'])

    def tor_url_num(self):
        self.mode = self.MENU4_1
        self.sender.sendMessage('[!] '+HOSTURL+'의 숫자를 입력하세요.')

    def tor_url_set(self, keyword):
        global HOSTURL
        global START_URL
        self.mode = ''
        config['common']['start_url'] = keyword
        saveConfig(CONFIG_FILE, config)
        host_fmt = config['common']['url_fmt']
        START_URL = config['common']['start_url']
        HOSTURL = host_fmt.format(START_URL)
        self.sender.sendMessage('[!] 토렌트 주소'+HOSTURL+'를 재등록하였습니다.')
        self.menu()

    def handle_command(self, command):
        if command == self.MENU0:
            self.menu()
        elif command == self.MENU1:
            self.tor_get_keyword()
        elif command == self.MENU3:
            self.dir_show_list()
        elif command == self.MENU2:
            self.tor_show_list()
        elif command == self.MENU4:
            self.tor_url_num()
        elif self.mode == self.MENU1_1:  # Get Keyword
            self.tor_search(command)
        elif self.mode == self.MENU1_2:  # Download Torrent
            self.tor_download(command)
        elif self.mode == self.MENU4_1:
            self.tor_url_set(command)

    def handle_smifile(self, file_id, file_name):
        try:
            self.sender.sendMessage('Saving subtitle file..')
            bot.download_file(file_id, DOWNLOAD_PATH + file_name)
        except Exception as inst:
            self.sender.sendMessage('ERORR: {0}'.format(inst))
            return
        self.sender.sendMessage('[!] 완료')

    def handle_seedfile(self, file_id, file_name):
        try:
            self.sender.sendMessage('[!] 토렌트 파일을 저장합니다..')
            generated_file_path = DOWNLOAD_PATH + "/" + \
                "".join(random.sample(string.ascii_letters, 8)) + ".torrent"
            bot.download_file(file_id, generated_file_path)
            self.agent.download(generated_file_path)
            os.system("rm " + generated_file_path)
            if not scheduler.get_jobs():
                scheduler.add_job(self.agent.check_torrents,
                                  'interval', minutes=1)
        except Exception as inst:
            self.sender.sendMessage('ERORR: {0}'.format(inst))
            return
        self.sender.sendMessage('[!] 다운로드를 시작합니다. ')

    def on_chat_message(self, msg):
        content_type, chat_type, chat_id = telepot.glance(msg)
        # Check ID
        if not chat_id in VALID_USERS:
            print("Permission Denied: "+str(chat_id))
            self.sender.sendMessage('[X] 사용 권한이 없습니다.'+str(chat_id))
            return

        if content_type == 'text':
            self.handle_command(msg['text'])
            return

        if content_type == 'document':
            file_name = msg['document']['file_name']
            if file_name[-3:] == 'smi':
                file_id = msg['document']['file_id']
                self.handle_smifile(file_id, file_name)
                return
            if file_name[-7:] == 'torrent':
                file_id = msg['document']['file_id']
                self.handle_seedfile(file_id, file_name)
                return
            self.sender.sendMessage('Invalid File')
            return

        self.sender.sendMessage('Invalid File')

    def on_close(self, exception):
        pass


def parseConfig(filename):
    path = os.path.dirname(os.path.realpath(__file__)) + '/' + filename
    with open(path, 'r', encoding='utf-8') as f:
        js = json.loads(f.read())
        f.close()
    return js

def saveConfig(filename, config):
    path = os.path.dirname(os.path.realpath(__file__)) + '/' + filename
    with open(path, 'w', encoding='utf-8') as f:
      json.dump(config, f, ensure_ascii=False, indent=4)
      f.close()

def getConfig(config):
    global TOKEN
    global AGENT_TYPE
    global VALID_USERS
    global DOWNLOAD_PATH
    global TORRENT_FILE_PATH
    global HOSTURL
    global SEARCH_PARAM
    TOKEN = config['common']['token']
    AGENT_TYPE = config['common']['agent_type']
    VALID_USERS = config['common']['valid_users']
    DOWNLOAD_PATH = config['common']['download_path']
    if DOWNLOAD_PATH[0] == '~':
        DOWNLOAD_PATH = expanduser('~') + DOWNLOAD_PATH[1:]
    TORRENT_FILE_PATH = config['common']['torrent_file_path']
    if TORRENT_FILE_PATH[0] == '~':
        TORRENT_FILE_PATH = expanduser('~') + TORRENT_FILE_PATH[1:]
    host_fmt = config['common']['url_fmt']
    START_URL = config['common']['start_url']
    HOSTURL = host_fmt.format(START_URL)

    SEARCH_PARAM = config['common']['param']
    if AGENT_TYPE == 'transmission':
        global TRANSMISSION_ID_PW
        global TRANSMISSION_PORT
        TRANSMISSION_ID_PW = config['transmission']['id_pw']
        TRANSMISSION_PORT = config['transmission']['port']


config = parseConfig(CONFIG_FILE)
if not bool(config):
    print("Err: Setting file is not found")
    exit()
getConfig(config)
scheduler = BackgroundScheduler()
scheduler.start()
bot = telepot.DelegatorBot(TOKEN, [
    pave_event_space()(
        per_chat_id(), create_open, Torrenter, timeout=120),
])
bot.message_loop(run_forever='Listening ...')
