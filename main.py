import os
import json
import time
import random

import requests
from bs4 import BeautifulSoup as bs

import config


class Decipher:
    """Class for decrypting song urls

    Note:
        This class was reverse engineered from vk.com js code
        that's why so many strange logic and method names
    """

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
    """Class for parsing songs from vk.com

    Note:
        Current limitations: downloading 100 songs max

    Attributes:
        vk_id (int): your vk.com id
        email (str): email or phone for vk.com
        password (str): password for vk.com
        offset (int): number fo songs to download form top (max 100)

    Todo:
        write granular exceptions in self.run
    """

    def __init__(self, vk_id, email, password, offset=0):
        self.vk_id = vk_id
        self.email = email
        self.offset = offset
        self.password = password
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10.12; rv:50.0) Gecko/20100101 Firefox/50.0',
        }
        self.payload = {
            'email': f'{self.email}',
            'pass': self.password,
        }
        self.s = requests.session()
        self.s.headers.update(self.headers)
        self.decipher = Decipher(vk_id=self.vk_id)

    def __repr__(self):
        return f"Parser({self.vk_id}, {self.email}, {self.password}, offset={self.offset})"

    def login(self):
        """Login to vk.com"""
        page = self.s.get('https://m.vk.com/login')
        soup = bs(page.text, 'lxml')
        url = soup.find('form')['action']
        self.s.post(
            url,
            data=self.payload,
            headers={
                'Referer': f'https://m.vk.com/login?role=fast&to=&s=1&m=1&email={self.email}',
            },
        )

    def _prepare(self, raw_text):
        """Cleaning json after vkontakte API

        VK.com returns json with html so we need to clean up html before parsing json

        Args:
            raw_text (str): text returned after request to vk.com API

        Returns:
            json: cleaned data in json format
        """
        # r = data.text.split('<!>')[5]
        json_data = json.loads(raw_text.split('<!>')[5][7:])
        return json_data

    def _load_playlist(self):
        """Loads songs from user's playlist

        Note:
            max 100 songs
            when setting offset to 1 it won't show a first song BUT will show much larger results (100 vs 2000)
        """
        return self.s.post(
            'https://vk.com/al_audio.php',
            data={
                'al': 1,
                'act': 'load_section',
                'owner_id': self.vk_id,
                'type': 'playlist',
                'playlist_id': '-1',
                'offset': 0,
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        )

    def _unmask_id(self, raw_song):
        """Unmasks song ID to vk.com format

        Args:
            raw_song (dict): song dict obtained from self._load_playlist

        Returns:
            str: unmasked_id which is unmasked string ready for vk.com API usage
        """
        track_id_strange = raw_song[13].split('/')[2]
        track_id_strange2 = raw_song[13].split('//')[1].split('/')[0]
        if track_id_strange == track_id_strange2:
            track_id_strange2 = raw_song[13].split('//')[2]
        unmasked_id = f"{self.vk_id}_{raw_song[0]}_{track_id_strange}_{track_id_strange2}"
        return unmasked_id

    def _parse_json_to_list(self, json_data):
        """Parsing json data to list of dictionaries

        Args:
            json_data (json): cleaned json data returned from self._prepare

        Returns:
            list: result_list which is list of dictionaries
        """
        result_list = []
        for raw_song in json_data['list']:
            song = {}
            song['track_id'] = raw_song[0]
            song['user_id'] = raw_song[1]
            song['title'] = raw_song[3]
            song['author'] = raw_song[4]
            song['unmasked_id'] = self._unmask_id(raw_song)
            result_list.append(song)
        return result_list

    def _load_song(self, unmasked_id):
        """Loads individual song details

        We need this in order to obtain crypted urls of songs,
        which later we will unmask via self.decipher.unmask_url

        Note:
            you can speed up via providing multiple ids separated by comma

        Args:
            unmasked_id (str): song ID which we obtained from self._unmask_id
        """
        return self.s.post(
            'https://vk.com/al_audio.php',
            data={
                'al': 1,
                'act': 'reload_audio',
                'ids': unmasked_id,
            },
            headers={
                'Content-Type': 'application/x-www-form-urlencoded',
            },
        )

    def run(self):
        playlist_json = self._load_playlist()
        playlist_json_cleaned = self._prepare(playlist_json.text)
        playlist = self._parse_json_to_list(playlist_json_cleaned)
        # reversing playlist in order to load songs in uploaded order
        reversed_playlist = list(reversed(playlist[:self.offset]))

        count = 1
        for song in reversed_playlist:
            # rate limiting hacking
            time.sleep(random.randint(10, 20) / 10)
            print(f"{count} from {len(reversed_playlist)} | {song['title']}")
            count += 1

            while True:
                try:
                    song_detail = self._load_song(unmasked_id=song['unmasked_id'])
                    song_cleaned = self._prepare(song_detail.text)
                    break
                except Exception:
                    # in case when vkontakte blocks us we are waiting
                    print('waiting for vkontakte to unblock us :(')
                    time.sleep(random.randint(3, 7))
            try:
                song_crypted_url = song_cleaned[0][2]
                unmasked_url = self.decipher.unmask_url(song_crypted_url)
                # loading song via curl
                os.system(f"curl {unmasked_url} -o 'data/{song['author']} - {song['title']}.mp3'")
            except IndexError:
                print(f"song {song['title']} is banned :(")


parser = Parser(
    vk_id=config.VK_ID,
    email=config.EMAIL,
    password=config.PASSWORD,
    offset=config.OFFSET,
)
parser.login()
parser.run()
