# -*- coding: utf-8 -*-


class AbstractUser:

    def __init__(self, initial_data, skey):
        if not initial_data.get('UserName'):
            raise ValueError('Intial data should contains UserName.')

        self._uid = initial_data['UserName']
        self._nickname = initial_data.get('NickName', '')
        self._avatar_url = ''
        if initial_data.get('HeadImgUrl'):
            self._avatar_url = ''.join((
                'https://wx.qq.com', initial_data['HeadImgUrl'],
                initial_data['skey']))

        self._city = initial_data.get('City', '')

    def __repr__(self):
        return '<%s id: %s nickname: %s>' % (
            self.__class__.__name__, self.uid, self.nickname)

    @property
    def uid(self):
        return self._uid

    @property
    def nickname(self):
        return self.nickname

    @property
    def avatar_url(self):
        return self._avatar_url

    @property
    def city(self):
        return self.city


class User(AbstractUser):

    GENDERS = {
        1: '男',
        2: '女',
        3: '未知',
    }

    def __init__(self, initial_data, skey):
        super().__init__(initial_data)
        self._gender = initial_data.get('Sex', 0)
        self.signature = initial_data.get('Signature', '')

    @property
    def gender(self):
        return self.GENDERS.get(self._gender, '未知')


class Friend(User):
    """好友"""


class MP(AbstractUser):
    """公众号"""


class ChatRoom(AbstractUser):
    """群聊"""

    def __init__(self, initial_data):
        super().__init__(initial_data)
        self._members = {}

    @property
    def members(self):
        return list(self._members.values())

    def add(self, friend):
        assert isinstance(friend, Friend)

        self._members[friend.id] = friend


special_account_name = (
    'filehelper', 'newsapp', 'fmessage', 'weibo', 'qqmail', 'tmessage',
    'qmessage', 'qqsync', 'floatbottle', 'lbsapp', 'shakeapp', 'medianote',
    'qqfriend', 'readerapp', 'blogapp', 'facebookapp', 'masssendapp',
    'meishiapp', 'feedsapp', 'voip', 'blogappweixin', 'weixin',
    'brandsessionholder', 'weixinreminder', 'officialaccounts',
    'notification_messages', 'wxitil', 'userexperience_alarm',
    'notification_messages',
)


class SpecialAccount(AbstractUser):
    """特殊账号

    已知特殊：
    filehelper, newsapp, fmessage, weibo, qqmail, tmessage, qmessage, qqsync,
    floatbottle, lbsapp, shakeapp, medianote, qqfriend, readerapp, blogapp,
    facebookapp, masssendapp, meishiapp, feedsapp, voip, blogappweixin, weixin,
    brandsessionholder, weixinreminder, officialaccounts, notification_messages,
    wxitil, userexperience_alarm, notification_messages
    """


def create_user(user_info, skey):
    username = user_info.get('UserName', '')
    user_info['skey'] = skey
    if username.startswith('@'):
        if username.count('@') == 2:
            return ChatRoom(user_info)

        elif user_info.get('VerifyFlag', 0) & 8 != 0:
            return MP(user_info)

        else:
            return Friend(user_info)

    if username in special_account_name:
        return SpecialAccount(user_info)
