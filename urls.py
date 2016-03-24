# coding=utf-8
"""
Module to maintain all URL patterns used in this Tornado web server.
These URLs must be imported into the main program and used in the tornado.web.Application initializer.
"""

from tornado.web import url, StaticFileHandler
from handlers.index_handler import IndexHandler
from handlers.power_metering_api import PowerMeteringHandler
from handlers.susiaccess import SUSIAccessHandler
from handlers.webaccess import WebAccessHandler
from settings import settings

# File export path
FILE_EXPORT_PATH = settings['FILE_EXPORT_PATH']

# Reusable regex expressions
alphanumeric_regex = "[a-zA-Z0-9._-]+"
slash_param_list = "(\/{0})*".format(alphanumeric_regex)
json_or_xml = "[jJ][sS][oO][nN]|[xX][mM][lL]"

# URL dictionary
url_dictionary = {
    'susi_ws': "/susi",
    'wa_ws': '/WaWebService',
    'susi_login': "susi_login.html",
    'susi_create_tables': "susi_create_tables.html",
}

url_patterns = [
    # **** Main index ****
    url(r"/", IndexHandler),

    # **** SUSIAccess web service fetch ****
    # 1st parameter is web service group, 2nd parameter is optional web service name, 3rd is optional list of parameters
    # Example: http://localhost:8888/susi/APIInfoMgmt/getEncryptPwd/password
    url(r"{0}/({1})(\/{1})?{2}\/?".format(url_dictionary['susi_ws'], alphanumeric_regex, slash_param_list),
        SUSIAccessHandler, name="susi"),

    # **** WebAccess web service fetch ****
    # 1st parameter is 'JSON' or 'XML', 2nd parameter is web service name, 3rd is optional list of parameters
    # Example: http://localhost:8888/WaWebService/json/DeviceDetail/85/energy/1/ACR
    url(r"{0}/({1})/({2})({3})\/?".format(url_dictionary['wa_ws'], json_or_xml, alphanumeric_regex, slash_param_list),
        WebAccessHandler),

    # **** Power Metering API ****
    # 取得電表 (Get power meter)
    # Example: http://localhost:8888/get_power_meter
    url(r"/get_power_meter", PowerMeteringHandler),

    # B11 - 本日電量
    # Example: http://localhost:8888/get_energy_consumption_today?power_meter_id=id&date=d&intervaltype=i&interval=x
    url(r"/get_energy_consumption_today", PowerMeteringHandler),

    # B12-1 - 用電趨勢（日） & B12-2 - 用電趨勢（月）
    # Example: http://localhost:8888/get_energy_consumption_history?power_meter_id=id&date=d&datarange=r&intervaltype=i&interval=x
    url(r"/get_energy_consumption_history", PowerMeteringHandler),
	# B12-1 - 用電趨勢（日）匯出 & B12-2 - 用電趨勢（月）匯出
    # Example: http://localhost:8888/get_energy_consumption_history_export?power_meter_id=id&date=d&datarange=r&intervaltype=i&interval=x
    url(r"/get_energy_consumption_history_export", PowerMeteringHandler),

    # B13 - 用電比較 (日比較) & B14 - 用電比較 (月比較)
    # Example: http://localhost:8888/get_energy_consumption_history_comparison?power_meter_id=id&date_1=d&date_2=d&datarange=r&intervaltype=i&interval=x
    url(r"/get_energy_consumption_history_comparison", PowerMeteringHandler),

    # *** Serve static files ***
	# Export files:
    # Example: http://localhost:8888/static/exportfiles/1260.csv
    url(r"/static/exportfiles/(.*)", StaticFileHandler, {'path': FILE_EXPORT_PATH})
]

# Append function URLs to root '/'
for url_pattern in url_dictionary:
    url_patterns.append(url(r"/({0})".format(url_pattern), IndexHandler))