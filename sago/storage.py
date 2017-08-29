# -*- coding: utf-8 -*-
import os

from .utils.functional import random_str


class BaseStorage:

    def save(self, *args, **kwargs):
        pass


class TmpFileStorage(BaseStorage):

    TMP_PATH = '/tmp/sago/qrcode/'

    def __init__(self, path=None):
        path = os.path.normpath(path) if path else self.TMP_PATH
        abs_path = os.path.abspath(path)

        if not os.path.exists(abs_path):
            os.makedirs(abs_path)

        file_name = '%s.png' % random_str()
        self.file_path = os.path.join(abs_path, file_name)

    def save(self, buff):
        with open(self.file_path, 'wb') as f:
            f.write(buff.getvalue())

        return self.file_path
