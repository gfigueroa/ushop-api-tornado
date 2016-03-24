from handlers.base import BaseHandler
import logging

logger = logging.getLogger('ushop.' + __name__)


class FooHandler(BaseHandler):
    def get(self):
        logger.info('foo')
        self.render("base.html")
