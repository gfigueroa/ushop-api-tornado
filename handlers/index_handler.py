from handlers.base import BaseHandler
import logging
import urls

logger = logging.getLogger('ushop.' + __name__)


class IndexHandler(BaseHandler):
    """
    Root handler class with index to the various server functions
    """

    def data_received(self, chunk):
        pass

    def get(self, function=None):
        """
        Print main page
        :param function: the UShop server function that the user wishes to execute
        """
        if function is None:
            self.render("index.html", wa_ws_url=urls.url_dictionary['wa_ws'])
        else:
            self.render(urls.url_dictionary[function])