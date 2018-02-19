import json
import os
import time
import random

import requests
from bs4 import BeautifulSoup as bs


class Decipher:
    '''
        This class was reverse engineered from vkontakte js code
        that's why so many strange logic and method names )
    '''

    def __init__(self, vk_id):
        self.vk_id = vk_id
        self.r = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMN0PQRSTUVWXYZO123456789+/="

    def r(self, t, e):
        t = t.split("")
        i = None
        o = self.r + self.r
        a = len(t)
        while (a > 0):
            i = o.index(t[a])
            if (~i != 0):
                t[a] = o[(i - e):(i - e + 1)]
        return "".join(t)

    def s2(self, t, e):
        i = len(t)
        if (i > 0):
            o = self.s(t, e)
            a = 0
            t = list(t)
            while (a < i - 1):
                a += 1
                tmp = t[o[i - 1 - a]]
                t[o[i - 1 - a]] = t[a]
                t[a] = tmp

        return "".join(t)

    def i(self, t, e):
        return self.s2(t, int(e) ^ self.vk_id)

    def x(self, t, e):
        i = []
        e = ord(e[0])
        tmp = self.x.split("")
        for t in range(0, len(tmp)):
            i.append(chr(ord(t[0]) ^ e))

        return i.join("")

    def a(self, t):
        if (not t or len(t) % 4 == 1):
            return False
        o = 0
        s = ""
        i = None
        e = None
        for a in range(0, len(t)):
            i = t[a]
            i = self.r.index(i)
            if (~i != 0):
                e = 64 * e + i if o % 4 != 0 else i
                if (o % 4 != 0):
                    o += 1
                    s += ''.join(map(chr, [255 & e >> (-2 * o & 6)]))
                else:
                    o += 1
        return s

    def s(self, t, e):
        i = len(t)
        o = [0] * i
        if (i != 0):
            a = i
            e = abs(e)
            while (a > 0):
                a -= 1
                e = (i * (a + 1) ^ e + a) % i
                o[a] = e

        return o

    def unmask_url(self, url):
        if ("audio_api_unavailable" in url):
            e = url.split("?extra=")[1].split("#")
            o = "" if e[1] == "" else self.a(e[1])

            e = self.a(e[0])
            if (type(o) is not str):
                return url

            o = o.split(chr(9)) if o != "" else []

            s = None
            r = None
            n = len(o)
            while (n > 0):
                n -= 1
                r = o[n].split(chr(11))
                tmp = r[0]
                r[0] = e
                s = tmp

                method = getattr(self, s, None)
                if (not callable(method)):
                    return url
                e = method(r[0], r[1])

            if (e and e[0:4] == "http"):
                return e
        return url


class Parser:
    '''
    loading songs from vkontakte
    Current limitations: skipping first song, max playlist is 2k
    '''
    def __init__(self, vk_id, email, password, offset=0):
        self.vk_id = vk_id
        self.email = email
        # number of song to download
        self.offset = offset
        self.password = password
        self.headers = {
            "Referer":
            "https://m.vk.com/login?role=fast&to=&s=1&m=1&email={}".format(
                self.email),
            'User-Agent':
            'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0'
        }
        self.payload = {
            'email': '{}'.format(self.email),
            'pass': self.password
        }
        self.s = requests.session()
        self.decipher = Decipher(vk_id=self.vk_id)

    def login(self):
        '''
        login to vkontakte
        '''
        page = self.s.get('https://m.vk.com/login')
        soup = bs(page.content, 'lxml')
        url = soup.find('form')['action']
        self.s.post(url, data=self.payload, headers=self.headers)

    def _prepare(self, data):
        '''cleaning json after vkontakte'''
        r = data.text.split('<!>')[5]
        json_data = json.loads(data.text.split('<!>')[5][7:])
        return json_data

    def _load_playlist(self):
        '''
        loading first 2k playlist songs
        we also skipping first song :(
        here we can't get songs' download urls
        thus we are using self._load_song to get url
        '''
        return self.s.post(
            'https://vk.com/al_audio.php',
            data={
                'al': 1,
                'act': 'load_section',
                'owner_id': self.vk_id,
                'type': 'playlist',
                'playlist_id': '-1',
                'offset': 1
            },
            headers={
                'Content-Type':
                'application/x-www-form-urlencoded',
                'User-Agent':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0'
            })

    def _parse_json_to_dict(self, res):
        '''
        parsing list to dict
        '''
        return list(map(lambda x: {
            'track_id': x[0],
            'user_id': x[1],
            'src': x[2],
            'title': x[3],
            'author': x[4]},
            res['list'])
        )

    def _load_song(self, ids):
        '''
        loads individual song's details (download url)
        also we can speed up this
        and load multiple songs at the same time
        '''
        return self.s.post(
            'https://vk.com/al_audio.php',
            data={
                'al': 1,
                'act': 'reload_audio',
                'ids': '{}_{}'.format(self.vk_id, ids)
            },
            headers={
                'Content-Type':
                'application/x-www-form-urlencoded',
                'User-Agent':
                'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0'
            })

    def run(self):
        # loading last 2k songs (without)
        playlist_json = self._load_playlist()
        # fixing broken json structure
        playlist_json_cleaned = self._prepare(playlist_json)
        # creating list of dictionaries here
        playlist = self._parse_json_to_dict(playlist_json_cleaned)
        # reversing playlist in order to load songs in uploaded order
        reversed_playlist = list(reversed(playlist[:self.offset]))

        count = 1
        for song in reversed_playlist:
            # rate limiting fucking
            time.sleep(random.randint(10, 20) / 10)
            print("{count} from {length} | {title}".format(
                count=count, length=len(reversed_playlist), title=song['title']))
            count += 1
            
            while True:
                try:
                    song_detail = self._load_song(ids=song['track_id'])
                    song_cleaned = self._prepare(song_detail)
                    break
                except:
                    # in case when vkontakte blocks us we are enabling new fucking mode
                    print('waiting for vkontakte to unblock us :(')
                    time.sleep(random.randint(3, 7))
            try:
                song_crypted_url = song_cleaned[0][2]
                unmasked_url = self.decipher.unmask_url(song_crypted_url)
                # loading song via curl
                os.system("curl {} -o 'data/{} - {}.mp3'".format(
                    unmasked_url, song['author'], song['title']))
            except IndexError:
                print('song {} is banned :('.format(song['title']))


if __name__=='__main__':
    parser = Parser(
        vk_id=00000000,         # your id
        email="+380902192121",  # your phone
        password="securepass",  # vkontakte password
        offset=152)             # number of songs to load
    parser.login()
    parser.run()
