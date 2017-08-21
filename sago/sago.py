# -*- coding: utf-8 -*-
import asyncio
import re

from .core import Core
from .loop import EventLoop
from .models.contact import Contact
from .models.user import ChatRoom, create_user, Friend, MP, SpecialAccount, User


class BaseSago:

    def __init__(self):
        self.loop = EventLoop()
        self.core = Core(loop=self.loop)

        self.skey = None
        self.uin = None
        self.pass_ticket = None
        self.sid = None
        self.sync_key = None

        self.user = None

        self._has_logged = False
        self.contact = {
            'friends': Contact(Friend),
            'mps': Contact(MP),
            'chat_rooms': Contact(ChatRoom),
            'special_accounts': Contact(SpecialAccount),
        }

        self.login()

    @property
    def friends(self):
        return self.contact['friend']

    @property
    def mps(self):
        return self.contact['mps']

    @property
    def chat_rooms(self):
        return self.contact['chat_rooms']

    @property
    def special_accounts(self):
        return self.contact['special_accounts']

    async def _login(self):
        uuid = await self.core.request_uuid()
        if not uuid:
            raise ValueError('Request uuid failed.')

        qrcode_storage = self.get_qrcode_storage()
        await self.core.get_login_qrcode(self.uuid, qrcode_storage)
        self.handle_login_qrcode()

        login_confirm_url = await self.waiting_login_confirm(uuid)
        ret = self.core.login_confirm(login_confirm_url)

        self.skey = ret['skey']
        self.sid = ret['sid']
        self.uin = ret['uin']
        self.pass_ticket = ret['pass_ticket']

        data = await self.core.init_client(
            self.skey, self.sid, self.uin, self.pass_ticket)
        self._set_user_info(data['user_info'])
        self.sync_key = data['sync_key']

        self._has_logged = True

        await self.update_all_contact()
        await self.update

    async def waiting_login_confirm(self, uuid):
        while True:
            ret = await self.core.listen_qrcode_scanned(uuid)
            m = re.search(r'window.code=(?P<code>\d+);', ret)
            code = m.group('code')
            if code == '200':
                m = re.search(
                    r'window.redirect_uri="(?P<redirect_uri>\S+)";', ret)
                return m.group('redirect_uri')

            if code == '201':
                self.qrcode_scanned()
                continue
            if code == '408':
                return self.login_timeout()

    async def _update_all_contact(self):
        member_list = await self.core.request_all_contact(
            self.skey, self.pass_ticket)

        for user_info in member_list:
            user = create_user(user_info)
            if isinstance(user, Friend):
                self.friends.add(user)

            elif isinstance(user, MP):
                self.mps.add(user)

            elif isinstance(user, ChatRoom):
                self.chat_rooms.add(user)

            elif isinstance(user, SpecialAccount):
                self.special_accounts.add(user)

    def update_all_contact(self):
        pass

    def qrcode_scanned(self):
        pass

    def login_timeout(self):
        pass

    def get_qrcode_storage(self):
        pass

    def handle_login_qrcode(self):
        pass

    def _set_user_info(self, user_info):
        self.user = User(user_info)

    def login(self):
        pass
