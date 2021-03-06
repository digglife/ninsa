# -*- coding: utf-8 -*-
import requests
import re
import xml.etree.ElementTree as et
from bs4 import BeautifulSoup


BASE_URL = 'http://search1.nintendo.co.jp/search/softwareXml.php'

# Array in the order from http://www.nintendo.co.jp
HARDWARE_URL = ['wiiU_all', 'wiiU', 'wiiU_dl',
                'wii_all', 'wii', 'wiiWare', 'wiiVc',
                '3ds_all', '3ds', '3dsDl', '3dsVc',
                'ds_all', 'ds', 'dsiWare', 'wiiU_Vc']

HARDWARES = {
    'wiiu': [0, 1, 2, 14],
    'wii': [3, 4, 5, 6],
    '3ds': [7, 8, 9, 10],
    'ds': [11, 12, 13],
}
MEDIATYPES = {'pkg': 1, 'download': 2, 'vc': 3}

GENRES = ['action', 'adventure', 'sports', 'simulation',
          'shooting', 'rpg', 'study', 'training',
          'puzzle', 'table', 'music', 'race',
          'fight', 'communication', 'practical', 'other']


class NintendoSearcher:
    """NintendoSearcher Main Class:

    NintendoSearcher(keyword, hardware='3ds', mediatype='dl', option='nintendo',
        genre='action', price='500', startdate='201502',enddate='201601')

    """

    def __init__(self, query, hardware=None, mediatype=None, genre=None,
                 price=None, trial=False, campaign=False, nintendo=False,
                 startdate=None, enddate=None):

        self.query = query
        self.hardware = hardware
        self.mediatype = mediatype
        self.genre = genre
        self.price = price
        self.trial = trial
        self.campaign = campaign
        self.nintendo = nintendo
        self.startdate = startdate
        self.enddate = enddate
        self._page = 1
        self._total = 0

    def get_games(self):
        while self._page != 0:
            yield self._get_items()

    def _request(self):
        params = self._get_params()
        r = requests.get(BASE_URL, params=params)
        r.encoding = 'utf8'
        return r.text

    def _get_items(self):
        xml = self._request()
        root = et.fromstring(xml.encode('utf8'))
        self._total = int(root[0].text)
        if self._total == 0:
            return []
        titles = []
        for e in root[1]:
            title = {}
            for attrib in e:
                if attrib.tag == 'Detail':
                    title.update(self._parse_details(attrib.text))
                    continue
                title[attrib.tag] = attrib.text
            titles.append(title)
        count = titles[-1]['Row']
        self._page += 1
        if int(count) == self._total:
            self._page = 0
        return titles

    def _get_params(self):
        params = {}
        if self._get_hardid():
            hardid = self._get_hardid()
            for id in hardid:
                key = "hard[%d]" % id
                params[key] = HARDWARE_URL[id]
        params['keyword'] = self.query
        params['genre'] = self._get_genre()
        params['price'] = self._format_price(self.price)
        params['release[start]'] = self._date_to_index(self.startdate)
        params['release[end]'] = self._date_to_index(self.enddate)
        params['page'] = self._page
        if self.trial:
            params['trial'] = 1
        if self.campaign:
            params['incampaign'] = 1
        if self.nintendo:
            params['maker'] = 1
        return params

    def _get_hardid(self):

        if self.hardware is None and self.mediatype is None:
            return

        if self.hardware:
            hardwares = self.hardware.split(',')
            if not set(hardwares) <= set(HARDWARES.keys()):
                raise
        else:
            hardwares = HARDWARES.keys()

        if self.mediatype:
            mediatypes = self.mediatype.split(',')
            if not set(mediatypes) <= set(MEDIATYPES.keys()):
                raise
        else:
            mediatypes = MEDIATYPES.keys()

        hardid = []
        for mt in mediatypes:
            #['vc', 'pkg']
            for hw in hardwares:
                if mt == 'vc' and hw == 'ds':
                    continue
                hardid.append(HARDWARES[hw][MEDIATYPES[mt]])
        return hardid

    def _get_genre(self):
        if self.genre is None:
            return
        genres = self.genre.split(',')
        if not set(genres) <= set(GENRES):
            raise
        return [GENRES.index(x) for x in genres]

    @staticmethod
    def _format_price(price):
        if price is None:
            return
        price = int(price)

        if price <= 500:
            return "*_500"
        elif 500 < price <= 1000:
            return "*_1000"
        else:
            return

    @staticmethod
    def _date_to_index(date):
        # 2004-01 : 0
        # 2004-12 : 1
        # 2005-01 : 1
        # 2005-06 : 2
        # 2005-07 : 2
        # 2005-12 : 3
        # 2006-01 : 3
        # 2006-06 : 4
        # 2006-07 : 4
        # 2006-12 : 5
        # ......
        """
        Now only able to parse yyyymm defined on the webpage of Nintendo site.
        Need to figure out a way to handle nature months besides 1,6,7,12
        """
        if date is None:
            return
        index = 0
        m = re.match('^(\d{4})-?(\d{2})$', date)
        if m is None:
            return
        [year, month] = [int(i) for i in m.groups()]

        if year < 2004:
            return
        elif year == 2004:
            if month == 1:
                index = 0
            elif month == 12:
                index = 1
            else:
                return
        else:
            year_offset = year - 2005
            if month == 1:
                index = 1 + 2 * year_offset
            elif month == 6 or month == 7:
                index = 2 + 2 * year_offset
            elif month == 12:
                index = 3 + 2 * year_offset
            else:
                return

        return index

    @staticmethod
    def trans_hardid(id):
        hardid = ['3ds', 'ds', 'ds', 'wii', 'wiiu', 'etc', 'amibo']
        return hardid[id-1]

    @staticmethod
    def trans_mediatype(id):
        mediatypes = ['package', 'download', 'package/download', 'vc']
        return mediatypes[id-1]

    @staticmethod
    def _parse_details(details):
        html = BeautifulSoup(details)
        spans = html.find_all('span')
        detail = {}
        for s in spans:
            c = s.get('class')[0]
            if c == 'softinfo__date':
                #detail['Date'] = re.search('([\d\.]+)', s.text).group().encode('utf-8')
                detail['Date'] = s.text
            elif c == 'softinfo__price':
                #detail['Price'] = re.search('([\d,]+)', s.text).group().encode('utf-8')
                detail['Price'] = s.text
            elif c == 'softinfo__maker':
                detail['Maker'] = s.text
            else:
                pass
        return detail
