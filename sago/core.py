# -*- coding: utf-8 -*-
import asyncio
import functools
import io
import json
import logging
import re
import threading
import time
import urllib.parse
import xml.etree.ElementTree as ET

import aiohttp
import pyqrcode

from .utils.decorators import singleton
from .utils.functional import random_num

logger = logging.getLogger('sago')

APPID = 'wx782c26e4c19acffb'
LANG = 'zh_CN'

CHECK_QRCODE_SCANNED_URL = r'https://login.wx.qq.com/cgi-bin/mmwebwx-bin/login'
GET_ALL_CONTACT_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetcontact'
GET_BATCH_CONTACT_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxbatchgetcontact'
LOGIN_PAGE_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxnewloginpage'
LOGIN_QRCODE_URL = r'https://login.weixin.qq.com/l/'
SYNC_CHECK_URL = r'https://webpush.wx.qq.com/cgi-bin/mmwebwx-bin/synccheck'
SYNC_DATA_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxsync'
UUID_URL = r'https://login.weixin.qq.com/jslogin'
WECHAT_INIT_URL = r'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxinit'


class Core:

    @singleton
    def __new__(cls, **kwargs):
        loop = asyncio.get_event_loop()
        run_event_loop(loop)

        instance = super().__new__(cls, **kwargs)
        instance._client = aiohttp.ClientSession(loop=loop)
        instance._loop = loop
        return instance

    def __init__(self, lang=LANG):
        self.lang = lang

    @property
    def loop(self):
        return self._loop

    @property
    def reversed_timestamp(self):
        return abs(~int(time.time()))

    async def request_uuid(self):
        params = {
            'appid': APPID,
            'fun': 'new',
            'lang': self.lang,
            'redirect_uri': LOGIN_PAGE_URL,
            '_': self.reversed_timestamp,
        }

        async with self._client.get(UUID_URL, params=params) as resp:
            if resp.status != 200:
                logger.error('The server returned code %s while request uuid',
                             resp.status)
                return

            ret = await resp.text()

        m = re.search(
            r'window.QRLogin.code = (?P<status_code>\d+); '
            r'window.QRLogin.uuid = "(?P<uuid>\S+)"', ret)

        if not m:
            logger.error('Request uuid failed. resp: %r', ret)
            return

        return m.group('uuid')

    async def get_login_qrcode(self, uuid, storage=None):
        qrcode = pyqrcode.create(LOGIN_QRCODE_URL + uuid)
        if storage:
            buff = io.BytesIO()
            qrcode.png(buff, scale=10)
            fn = functools.partial(storage.save, buff)
            return await self._loop.run_in_executor(None, fn)

        print(qrcode.terminal(quiet_zone=1))

    async def listen_qrcode_scanned(self, uuid, tip=0):
        params = {
            'loginicon': 'true',
            'uuid': uuid,
            'tip': tip,
        }

        logger.info('Listening the qrcode scan event..')
        params['_'] = self.reversed_timestamp

        async with self._client.get(
                CHECK_QRCODE_SCANNED_URL, params=params) as resp:
            print(resp.status)
            ret = await resp.text()
            print(ret)
            return ret

    async def login_confirm(self, login_page_url):
        params = {
            'version': 'v2',
            'fun': 'new',
        }
        async with self._client.get(
                login_page_url + urllib.parse.urlencode(params)) as resp:
            xml_ret = await resp.text()

        root = ET.fromstring(xml_ret)
        return {
            'skey': root.find('skey').text,
            'sid': root.find('wxsid').text,
            'uin': root.find('wxuin').text,
            'pass_ticket': root.find('pass_ticket').text,
        }

    def get_base_request_data(self, skey, sid, uin):
        return {
            'BaseRequest': {
                'Skey': skey,
                'Sid': sid,
                'Uin': uin,
                'DeviceID': 'e' + random_num(),
            }
        }

    def serialize_sync_key(self, sync_key_list):
        sync_key = []
        for itm in sync_key_list:
            sync_key.append('%d_%d' % (itm['Key'], itm['Val']))

        return '|'.join(sync_key)

    async def init_client(self, skey, sid, uin, pass_ticket):
        data = self.get_base_request_data(skey, sid, uin)
        params = {
            'pass_ticket': pass_ticket,
            'r': self.reversed_timestamp,
            'lang': self.lang,
        }

        async with self._client.post(
                WECHAT_INIT_URL, params=params, json=data) as resp:
            ret = json.loads(await resp.text())

        return {
            'user_info': ret['User'],
            'sync_key': ret['SyncKey'],
        }

    async def request_all_contact(self, skey, pass_ticket):
        params = {
            'skey': skey,
            'pass_ticket': pass_ticket,
            'seq': 0,
            'r': self.reversed_timestamp,
            'lang': self.lang,
        }
        async with self._client.post(GET_ALL_CONTACT_URL, params=params) as resp:
            return json.loads(await resp.text(encoding='utf-8'))['MemberList']

    async def sync_check(self, skey, sid, uin, sync_key):
        params = {
            'r': self.reversed_timestamp,
            'skey': skey,
            'sid': sid,
            'uin': uin,
            'synckey': self.serialize_sync_key(sync_key['List']),
            '_': self.reversed_timestamp,
        }

        async with self._client.get(SYNC_CHECK_URL, params=params) as resp:
            ret = await resp.text()

        m = re.search(
            r'window.synccheck={retcode: "(?P<retcode>\d+)", '
            r'selector: "(?P<selector>\d+)"}', ret)
        return m.group('retcode'), m.group('selector')

    async def sync_data(self, skey, sid, uin, sync_key, pass_ticket):
        params = {
            'skey': skey,
            'pass_ticket': pass_ticket,
            'sid': sid,
        }
        data = self.get_base_request_data(skey, sid, uin)
        data['SyncKey'] = sync_key
        data['rr'] = self.reversed_timestamp

        async with self._client.post(
                SYNC_DATA_URL, params=params, json=data) as resp:
            return json.loads(await resp.text(encoding='utf-8'))

    async def batch_get_contact(self, skey, sid, uin, pass_ticket, *username):
        params = {
            'pass_ticket': pass_ticket,
            'r': self.reversed_timestamp,
            'type': 'ex',
        }

        data = self.get_base_request_data(skey, sid, uin)
        data.update({
            'Count': len(username),
            'List': [{'UserName': un, 'EncryChatRoomId': ''} for un in username]
        })

        async with self._client.post(
                GET_BATCH_CONTACT_URL, params=params, json=data) as resp:
            return json.loads(await resp.text(encoding='utf-8'))['ContactList']

    def __del__(self):
        self._client.close()


def run_event_loop(loop):
    thread = threading.Thread(target=loop.run_forever)
    thread.daemon = True
    thread.start()
