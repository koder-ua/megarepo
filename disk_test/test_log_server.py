__author__ = 'koder'
import os
import sys
import logging
import logging.handlers

logger = logging.getLogger(str(os.getpid()))
logger.setLevel(logging.DEBUG)

socketHandler = logging.handlers.SocketHandler('localhost',
    logging.handlers.DEFAULT_TCP_LOGGING_PORT)

logger.addHandler(socketHandler)

logger.info("info")
logger.debug("debug")
logger.warning("warning")
logger.error("error")
logger.critical("critical")
