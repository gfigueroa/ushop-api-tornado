"""
Module to handle access to the SUSIAccess server. Includes SUSIAccessHandler and other necessary
methods and classes.
"""

import urllib2
from tornado import httpclient
from tornado.httputil import HTTPHeaders
from tornado import escape
from handlers.base import BaseHandler
from settings import settings
import logging
import base64

# Global variables
logger = logging.getLogger('ushop.' + __name__)
SA_ROOT_URL = settings['SA_ROOT_URL']


class SUSIAccessHandler(BaseHandler):
    """
    A class to handle all calls to the SUSIAccess server
    """

    # Private members
    # SusiAccess related
    _sa_user = 'admin'
    _sa_password = 'admin'
    _sa_user_password_enc = base64.b64encode(_sa_user + ':' + _sa_password)
    _sa_headers = HTTPHeaders({"content-type": "application/xml; charset=utf-8",
                               "authorization": "Basic {0}".format(_sa_user_password_enc)})

    # Self related
    _fixed_headers = HTTPHeaders({"content-type": "application/xml; charset=utf-8",
                                  })

    def initialize(self):
        pass

    def data_received(self, chunk):
        pass

    def get(self, ws_group, ws_name, params):
        """
        When using the get method, the SUSIAccessHandler fetches the required SUSIAccess GET web service and
        writes the result to the browser.
        :param ws_group: The group of the web service to fetch (e.g. APIInfoMgmt, AccountMgmt, DeviceMgmt, etc.)
        :param ws_name: The name of the web service
        :param params: The parameters for the web service
        """

        # Set header content-type to application/xml
        self.set_header("content-type", "application/xml; charset=utf-8")

        param_list = str(params).split("/")
        if param_list is not None and len(param_list) >= 1:
            del param_list[0]  # First parameter is empty

        result = get_sa_web_service(self._sa_headers, ws_group, ws_name,
                                    param_list if param_list else None)
        if "error" not in result:
            self.write(result)
        else:
            logger.error(result, exc_info=True)
            self.send_error(status_code=400, reason=result)

    def post(self, ws_group, ws_name, trash):
        """
        When using the put method, the SUSIAccessHandler fetches the required POST SUSIAccess web service and
        writes the given data on the SUSIAccess server.
        :param ws_group: The group of the web service to access (e.g. SQLMgmgt, etc.)
        :param ws_name: The name of the web service
        :param trash: POST services have no params, so this will be discarded
        """

        # Set header content-type to text/html
        self.set_header("content-type", "text/html; charset=utf-8")

        # Get data list
        data_list = self.get_arguments('data')

        results = ""
        for data in data_list:
            result, ws_group, ws_name = post_sa_web_service(self._sa_headers, ws_group, ws_name,
                                                            data)
            results += result

        if "error" in results:
            logger.error(results, exc_info=True)
            self.send_error(status_code=400, reason=results)
        elif "<result>false</result>" in results:
            self.redirect("/?group={0}&action={1}&result={2}&reason={3}".format(ws_group, ws_name, 'fail',
                                                                                escape.url_escape(results)),
                          permanent=True)
        else:
            self.redirect("/?group={0}&action={1}&result={2}".format(ws_group, ws_name, 'success'), permanent=True)


def get_sa_web_service(headers, ws_group, ws_name=None, param_list=None, format_xml=True):
    """
    Fetches a GET web service from the SUSIAccess url. All web services are returned in XML format.
    :param headers: the headers needed to make the request to the SUSIAccess server
    :param ws_group: the first parameter of the web service call is the web service group
    :param ws_name: the second parameter of the web service call is the name of the web service
    :param param_list: the list of parameters for the web service being called, default - None
    :param format_xml: whether to format the XML result with a root node and xmlns, default - True
    :return the web service result as a string object
    """

    url = SA_ROOT_URL

    # Remove '/' from ws_name
    if ws_name is not None:
        ws_name = ws_name.replace('/', '')

    # Check the web service group
    # API Info Management group
    if ws_group.lower() == "apiinfomgmt":
        url += "APIInfoMgmt/"
        # API Information
        if ws_name is None:
            url += ""
        # Get encrypted password
        elif ws_name.lower() == "getencryptpwd":
            if len(param_list) < 1:
                return "error: missing_parameters"
            else:
                url += "getEncryptPwd"
                pwd = param_list[0]
                url += "/{0}".format(pwd)
        # Wrong web service name
        else:
            return "error: wrong_ws_name"
    # Account Management group
    elif ws_group.lower() == "accountmgmt":
        url += "AccountMgmt/"
        # Retrieve all accounts information
        if ws_name is None:
            url += ""
        # Wrong web service name
        else:
            return "error: wrong_ws_name"
    # Wrong web service group
    else:
        return "error: wrong_ws_group"

    http_client = httpclient.HTTPClient()
    try:
        http_request = httpclient.HTTPRequest(url, headers=headers)
        response = http_client.fetch(http_request)
    except httpclient.HTTPError, e:
        logger.error(("Error:", e), exc_info=True)
        raise e
    finally:
        http_client.close()

    if format_xml:
        # Add xmlns and root tag (comes without them) if needed
        xmlns = "xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\""
        opening_root_node = "<{0} {1}>".format(ws_name if ws_name else ws_group, xmlns)
        closing_root_node = "</{0}>".format(ws_name if ws_name else ws_group)
        result = "{0}{1}{2}".format(opening_root_node, response.body, closing_root_node)
    else:
        result = response.body

    return result


def post_sa_web_service(headers, ws_group, ws_name=None, data=None, format_xml=False):
    """
    Fetches a POST web service from the SUSIAccess url. Returns a success or fail response.
    :param headers: the headers needed to make the request to the SUSIAccess server
    :param ws_group: the first parameter of the web service call is the web service group
    :param ws_name: the second parameter of the web service call is the name of the web service
    :param data: the data (string) for the POST request, default - None
    :param format_xml: whether to format the XML result with a root node and xmlns, default - False
    :return the web service result (success or error), the ws_group and the ws_name
    """

    url = SA_ROOT_URL

    # Remove '/' from ws_name
    if ws_name is not None:
        ws_name = ws_name.replace('/', '')

    # Check the web service group
    # SQL Management
    if ws_group.lower() == "sqlmgmt":
        url += "SQLMgmt/"

        # If ws_name is None
        if ws_name is None:
            return "error: missing_ws_name"
        # Create table
        elif ws_name.lower() == "createtables":
            url += "CreateTable"
        # Wrong web service name
        else:
            return "error: wrong_ws_name"
    elif ws_group.lower() == "accountmgmt":
        url += "AccountMgmt/"

        # If ws_name is None
        if ws_name is None:
            return "error: missing_ws_name"
        elif ws_name.lower() == "login":
            url += "Login"
        else:
            return "error: wrong_ws_name"
    # Wrong web service group
    else:
        return "error: wrong_ws_group"

    http_client = httpclient.HTTPClient()
    try:
        '''
        post_data = {'data': data}  # A dictionary of your post data
        body = urllib.urlencode(post_data)  # Make it into a post request
        http_request = httpclient.HTTPRequest(url, headers=self._sa_headers, body=body, method='POST')
        # response = http_client.fetch(http_request, method='POST', data=data)
        response = http_client.fetch(http_request)
        '''
        req = urllib2.Request(url)
        req.headers = headers
        response = urllib2.urlopen(req, data).read()
    except httpclient.HTTPError, e:
        logger.error(("Error:", e), exc_info=True)
        raise e
    finally:
        http_client.close()

    if format_xml:
        # Add xmlns and root tag (comes without them) if needed
        xmlns = "xmlns:i=\"http://www.w3.org/2001/XMLSchema-instance\""
        opening_root_node = "<{0} {1}>".format(ws_name if ws_name else ws_group, xmlns)
        closing_root_node = "</{0}>".format(ws_name if ws_name else ws_group)
        result = "{0}{1}{2}".format(opening_root_node, response, closing_root_node)
    else:
        result = response

    return result, ws_group, ws_name