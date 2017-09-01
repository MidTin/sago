# -*- coding: utf-8 -*-
from urllib.parse import urlencode


class Message:

    MESSAGE_TYPE = -1

    def __init__(self, **kwargs):
        assert 'MsgId' in kwargs, 'Message should contains MsgId.'
        assert 'ToUserName' in kwargs, 'Message should contains ToUserName.'
        assert 'FromUserName' in kwargs, 'Message should contains FromUserName.'
        assert 'Content' in kwargs, 'Message should contains Content.'

        self._msg_id = kwargs['MsgId']
        self._to = kwargs['ToUserName']
        self._from = kwargs['FromUserName']
        self._raw = kwargs

        self.parse_content(kwargs.get('Content'))

    @property
    def msg_id(self):
        return self._msg_id

    @property
    def to_user(self):
        return self._to

    @property
    def from_user(self):
        return self._from

    @property
    def raw(self):
        return self._raw

    @property
    def content(self):
        return self._content

    def parse_content(self, content):
        self._content = content
        return content


class TextMessage(Message):

    MESSAGE_TYPE = 1


class PictureMessage(Message):

    MESSAGE_TYPE = 3
    FETCH_PICTURE_URL = 'https://wx.qq.com/cgi-bin/mmwebwx-bin/webwxgetmsgimg'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        assert 'skey' in kwargs, 'An argument skey is expected.'

        params = {
            'MsgID': self._msg_id,
            'skey': kwargs['skey'],
            'type': 'big'
        }

        self._url = '?'.join((self.FETCH_PICTURE_URL, urlencode(params)))

        params['type'] = 'slave'
        self._thumb_url = '?'.join((self.FETCH_PICTURE_URL, urlencode(params)))


class EmotionMessage(PictureMessage):

    MESSAGE_TYPE = 47

    def parse_content(self, content):
        if not content:
            self._url = self._thumb_url = ''
            self._content = '[发送了一个表情，请在手机上查看]'
        else:
            self._content = content

        return self._content


class UnknownMessage(Message):

    MESSAGE_TYPE = -2


class MessageFactory:
    MESSAGE_TYPES = {
        TextMessage.MESSAGE_TYPE: TextMessage,
        PictureMessage.MESSAGE_TYPE: PictureMessage,
        EmotionMessage.MESSAGE_TYPE: EmotionMessage,
    }

    def __init__(self, contacts):
        self.contacts = contacts

    def build(self, msg_data):
        msg_cls = self.MESSAGE_TYPES.get(msg_data['MsgType'], UnknownMessage)
        msg_data['FromUserName'] = self.contacts.search(
            msg_data['FromUserName'])
        msg_data['ToUserName'] = self.contacts.search(
            msg_data['ToUserName'])


