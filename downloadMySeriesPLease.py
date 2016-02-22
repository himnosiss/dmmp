#!/usr/bin/python2.7
'''
Created on Apr 25, 2013

@author: bogdan.bala
'''
import Queue
import sys
import threading
import urllib2
import os
import traceback
import time


class DownloadMyMovies():
    def __init__(self, url, fromEpisode, toEpisode, threads=1, path=None, debug=True):
        self.url = url

        if path is None:
            self.__path = os.getenv("HOME") + "/Videos/"
        else:
            if path.endswith("/"):
                self.__path = path
            else:
                self.__path = path + "/"
   
        #Create path if does not exist
        dir = os.path.dirname(self.__path)
        if not os.path.exists(dir):
                os.makedirs(dir)
        print "Saving to path: ", self.__path
        
        self.__fromEpisode = fromEpisode
        self.__toEpisode = toEpisode
        self.__episodes = self.__getAllEpisodes()
        self.__threads = threads
        self.__runningThreads = []
        self.__debug = True
        

    '''
    Gets all the episodes for this series
    '''
    def __getAllEpisodes(self):
        result = urllib2.urlopen(self.url)
        links2 = []
        i = 0
        for line in result:
            if(-1<line.find("<div id='content'")):
                break
        
        
        for line in result:
            if(-1<line.find("Episoade")):
                break
                
        for line in result:
            if -1 < line.find("<a href='"):
                if 0 < len(line[line.find("<a href="):line.find("</a>")]):
                        i = i + 1
                        if(self.__fromEpisode <= i and i <= self.__toEpisode):                    
                            links2.append(line[line.find("<a href="):line.find("</a>")])
        
        
        links = []
        print "You selected to download the following episodes:"
        for link in links2:
            currentLink=link[link.find("<a href=") + 9:link.find("class='link'>")-2]
            links.append(currentLink)
        print currentLink
        print "Is that correct?"
    
        while True:
            var = raw_input("yes or no: ")
            if "yes" == var:
                break
            elif "no" == var:
                print "Operation canceled"
                exit(0)
        return links
    
    def startDownload(self):
        myQueue = Queue.Queue(self.__threads)
        for ep in self.__episodes:
            th = AsyncDownload(ep, myQueue, self.__path, self.__debug)
            myQueue.put(th)
            th.start()


class AsyncDownload(threading.Thread):
    def __init__(self, epUrl, queue, path, debug):
        threading.Thread.__init__(self)
        self.__epUrl = epUrl
        self.__queue = queue
        self.__path = path
        self.__debug = debug
        if debug :
            self.__logger = open('log.txt', 'a')
            self.__logger.write("AsyncDownload"+epUrl+" Path="+path)
            print "AsyncDownload=", epUrl, " Path=", path
                                
    def run(self):
        self.__getEpisodeLink()
    
    '''
    Returs the episode link from sfast web site
    '''
    def __getEpisodeLink(self):
        try:
            #idSerial = self.__epUrl[self.__epUrl.find("-") + 1:self.__epUrl.find("-") + 9] #+10 sau pana la a 3-a -
            #
            start = self.__epUrl.find("-") + 1
            end = self.__epUrl.find("-", start+5)
            idSerial = self.__epUrl[start:end]
            result = urllib2.urlopen("http://990.ro/" + self.__epUrl)
            link = ""
            fileName = ""
            for line in result:
                if line.find("<a ") > -1 and line.find("player-serial-" + idSerial) > -1 : # changed in -sfast-dddd.html
                    link = line[line.find("href=")+6:line.find(".html") + 5]
                    fileName = self.__epUrl[0:-12] + ".mp4"
                    break
            
            if link != "":
                if self.__debug:
                    self.__logger.write("http://990.ro/" + link)
                print "DEBUG:", link
                self.__getFastUploadFileLink("http://990.ro/"+link, fileName)
            else:
                print "Can't find link to sfast. Aborting"
                exit(2)
        except Exception, e:
            print traceback.print_exception(sys.exc_info()[0], sys.exc_info()[1], sys.exc_info()[2], limit=None, file=sys.stdout)
            self.__queue.get(self)
    
    '''
    Returns the player page
    ''' 
    def __getFastUploadFileLink(self, fastLink, fileName):
        print "Episode link:", fastLink
        result = urllib2.urlopen(fastLink)
        for line in result:
            if self.__debug :
                self.__logger.write(line)
            if line.find("http://fastupload.ro/video/") > -1:
                link = line[line.find("http://fastupload.ro/video/"):line.find(".html") + 5]
                break
            if line.find("http://superweb.rol.ro/video/") > -1:
                link = line[line.find("http://superweb.rol.ro/video/"):line.find(".html") + 5]
                break
            if line.find("http://www.mastervid.com/watch.php") > -1:
                # http://www.mastervid.com/watch.php?v=8c6b78dc3dae46728e2448a649236d8c
                link = line[line.find("http://www.mastervid.com/watch.php"):line.find("<img src")-2]
                break

        print ">>>>:", link

        result = urllib2.urlopen(link)
        # f1=open('./testfile', 'w+')
        for line in result:
            print line
            #old
            if (line.find("'file': ") > -1 and (line.find(".mp4")>-1 or line.find(".flv")>-1) ) :
                link = line[line.find("http"):].strip()[:-2]
                print "video file link: ", link
                # trying to stop and select the first movie file
                break


        self.__downloadFile(link, fileName)

    
    '''
    Downloads .flv file locally
    '''
    def __downloadFile(self, url, file_name):
        print "file Name =", file_name
        if len(file_name) == 0:
            file_name = url.rfind("/")
        u = urllib2.urlopen(url)
        f = open(self.__path + file_name, 'wb')
        meta = u.info()
        # file_size = int(meta.getheaders("Content-Length")[0])
        file_size = int(u.headers["Content-Length"])
	print "File size=", file_size
        t0 = time.time()
        print time.strftime("%H:%M:%S - %x"), "Start downloading ", file_name, ": ", file_size / 1024 / 1024, "MB"
        print file_name, "0%"
        dl_now = 0
        block_sz = 65536
        epsilon = 1
        while True:
            buffer2 = u.read(block_sz)
            if not buffer2:
                break
            f.write(buffer2)
            dl_now = dl_now + block_sz
            percent = int(dl_now * 100 / file_size)
            if(percent > 0 and percent % epsilon == 0):
                ftime = ((time.time()-t0)/percent)*100+t0
                estimation = time.strftime("%H:%M:%S - %x",time.localtime(ftime))
                print file_name, percent, "%", " estimation: ", estimation
                epsilon = epsilon + 1
            
            
        f.close()
        self.__queue.get(self)
        print "Downloading ", file_name, " is complete!"




# MAIN

print "Welcome to movie downloader!"

if len(sys.argv) <= 1:
    print "You must provide an url to 990.ro series"
    print "Optional you can specify a range of episodes where 1 is the episode 1 is season 1 and"
    print "99 is the last episode from the last season otherwise all the episodes will be downloaded"
    print "Optional you can specify the number of threads (default is 2)"
    print "Optional you can specify a path where the files to be downloaded (default is getEnv('HOME')/Videos)"
    print "Optional you can specify if you want to enable debugging, True or (default) False"
    exit(1)


url = sys.argv[1]
 
if len(sys.argv) >= 3:
    fromEpisode = int(sys.argv[2])
else:
    fromEpisode = 1  

if len(sys.argv) >= 4:
    toEpisode = int(sys.argv[3])
else:
    toEpisode = 999

if len(sys.argv) >= 5:
    threads = int(sys.argv[4])
else:
    threads = 1

if len(sys.argv) >= 6:
    path = sys.argv[5]
else:
    path = None

if len(sys.argv) >= 7:
    debug = sys.argv[6]
else:
    debug = False
    
movies = DownloadMyMovies(url, fromEpisode, toEpisode, threads, path, debug)
movies.startDownload()

print "DONE!"
