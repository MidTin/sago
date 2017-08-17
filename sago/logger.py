# -*- coding: utf-8 -*-
import logging

async_logger = logging.getLogger('asyncio')

logger = async_logger.getLogger('sago')

formatter = logging.Formatter(
    '[%(levelname)s](%(name)s) %(asctime)s %(pathname)s %(lineno)d %(funcName)s %(message)s')

handler = logging.StreamHandler()
handler.setFormatter(formatter)

logger.addHandler(handler)
