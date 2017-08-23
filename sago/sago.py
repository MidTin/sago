# -*- coding: utf-8 -*-
import asyncio
import re

from .core import Core
from .loop import EventLoop
from .models.contact import Contact, ContactList
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
        self.contact = Contact()
        self.contact.add('friends', ContactList(Friend))
        self.contact.add('mps', ContactList(MP))
        self.contact.add('chatrooms', ContactList(ChatRoom))
        self.contact.add('special_accounts', ContactList(SpecialAccount))

        self.login()

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

        await self._update_all_contact()
        await self._update_chatrooms_info()

    async def heart_beat(self):
        while True:
            pass

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

    def get_user(self, user_id):
        for contact in self.contact.values():
            user = contact.get(user_id)
            if user:
                return user

    def update_contact(self, *user_id):
        pass

    async def _update_contact(self, *user_id):
        contact_data = self.core.batch_get_contact(
            self.skey, self.sid, self.uin, self.pass_ticket, *user_id)

        for user_info in contact_data:
            user = self.get_user(user_info['UserName'])
            new_user = create_user(user_info)
            user.contact_list.add(new_user)
            del user

            if isinstance(new_user, ChatRoom):
                for member_data in user_info['MemberList']:
                    member = self.contact.get(member_data['UserName'])
                    if not member:
                        member = create_user(member_data)

                    new_user.add(member)

    async def _update_chatrooms_info(self):
        await self.update_contact(
            *[u.id for u in self.contact.chatrooms.members])

    async def _update_all_contact(self):
        contact_data = await self.core.request_all_contact(
            self.skey, self.pass_ticket)

        for user_info in contact_data:
            user = create_user(user_info)
            self.contact.add_user(user)

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
