# coding=utf-8
"""
Module to handle access to the WebAccess web services. Includes SUSIAccessHandler and other necessary
methods and classes.
"""
import ast
from calendar import monthrange
import json

import logging
import base64
import datetime
import random

from tornado import httpclient
from tornado.httputil import HTTPHeaders
from tornado.options import options

from handlers.base import BaseHandler, callback
from handlers.base import require_basic_auth, construct_error_json
from settings import settings
import webaccess

# Global variables
logger = logging.getLogger('ushop.' + __name__)
WA_ROOT_URL = settings['WA_ROOT_URL']
WA_TAG_NAME_MAP = settings['WA_TAG_NAMES']
PROJECT_NAME = settings['PROJECT_NAME']
NODE_NAME = settings['NODE_NAME']
DATA_TYPE = settings['DATA_TYPE']
WS_DATETIME_FORMAT = '%m/%d/%Y'  # The datetime format for power metering web service calls
FILE_EXPORT_DATETIME_FORMAT = '%Y/%m/%d'
FILE_EXPORT_TIME_FORMAT = '%H:%M'
FILE_EXPORT_PATH = settings['FILE_EXPORT_PATH']

@require_basic_auth
class PowerMeteringHandler(BaseHandler):
	"""
	A class to handle all calls to web services related to Power Metering (電量報表).
	"""

	# Private attributes
	_static_headers = HTTPHeaders({"content-type": "application/json; charset=utf-8"})

	def initialize(self):
		for header in self._static_headers:
			self.set_header(header, self._static_headers[header])

	def data_received(self, chunk):
		pass

	@callback
	def write(self, chunk):
		super(PowerMeteringHandler, self).write(chunk)

	def get(self, **kwargs):
		"""
		Fetches the required web service from the WebAccess server (or handler) and displays it as a Json object
		:param ws_name: The name of the web service to fetch
		:param params: The parameters for the web service
		:param **kwargs: this includes the basicauth_user and basicauth_pass
		:return: the result of a web service in Json format
		"""

		# Basic user authentication (override)
		wa_basicauth_user = kwargs.get('basicauth_user')
		wa_basicauth_pass = kwargs.get('basicauth_pass')
		wa_user_password_enc = base64.b64encode(wa_basicauth_user + ':' + wa_basicauth_pass)
		wa_headers = HTTPHeaders({"authorization": "Basic {0}".format(wa_user_password_enc)})

		ws_name = self.request.path[1:]  # original path is like "/get_energy_consumption_today"
		arguments = self.request.arguments

		try:
			result = get_power_metering_ws(wa_headers, ws_name, arguments)
		except httpclient.HTTPError, e:
			if e.code == 401:  # Authentication error
				result = construct_error_json("0005")
			else:
				result = construct_error_json("0001")
		except Exception, e:
				result = construct_error_json("0001")

		# Convert result to JSON
		result = json.dumps(result)

		self.write(result)


def get_power_metering_ws(wa_headers, ws_name, arguments):
	"""
	Get a Power Metering web service
	:param wa_headers: the headers to send to the WebAccess server
	:param ws_name: the name of the web service to access
	:param arguments: the URL arguments for the web service
	:return: a dictionary with the requested web service information
	"""

	# Copy the headers
	headers = wa_headers.copy()

	try:
		if ws_name == "get_power_meter":
			return get_power_meter()
		# For all other web services
		else:
			# Common arguments
			# =id (id: integer, where 0 refers to total energy; 1: refer to 1st power meter, and etc.)
			power_meter_id_index = int(arguments['power_meter_id'][0])
			power_meter_ids = WA_TAG_NAME_MAP[power_meter_id_index]
			# If not a list, then make it one
			if isinstance(power_meter_ids, str):
				power_meter_ids = [power_meter_ids]

			interval = int(arguments['interval'][0])

			if ws_name == "get_energy_consumption_today":
				return get_energy_consumption_today(headers, power_meter_ids, interval)
			elif ws_name == "get_energy_consumption_history":
				date_string = arguments['date'][0]
				date = datetime.datetime.strptime(date_string, WS_DATETIME_FORMAT)  # =d (d: mm/dd/yyyy represents the user selected date.)
				data_range = arguments['datarange'][0]
				return get_energy_consumption_history(headers, power_meter_ids, date, data_range, interval)
			elif ws_name == "get_energy_consumption_history_export":
				date_string = arguments['date'][0]
				date = datetime.datetime.strptime(date_string, WS_DATETIME_FORMAT)  # =d (d: mm/dd/yyyy represents the user selected date.)
				data_range = arguments['datarange'][0]
				return get_energy_consumption_history_export(headers, power_meter_ids, date, data_range, interval)
			elif ws_name == "get_energy_consumption_history_comparison":
				date_string1 = arguments['date_1'][0]
				date1 = datetime.datetime.strptime(date_string1, WS_DATETIME_FORMAT)  # =d (d: mm/dd/yyyy represents the user selected date.)
				date_string2 = arguments['date_2'][0]
				date2 = datetime.datetime.strptime(date_string2, WS_DATETIME_FORMAT)  # =d (d: mm/dd/yyyy represents the user selected date.)
				data_range = arguments['datarange'][0]
				return get_energy_consumption_history_comparison(headers, power_meter_ids, date1, date2, data_range, interval)
			else:
				return construct_error_json("0004")
	except KeyError, e:
		return construct_error_json("0003")
	except Exception, e:
		raise e


def get_power_meter():
	"""
	Function: 取得電表
	URL: http://host:port/get_power_meter
	The list of the identifiers of the monitored power meters, where each power meter is denoting by a positive integer.
	Also note that 0 represents the summation of the readings of the power meters.
	:return: { "power_meter_list": [ 1, 2, 3, 4, 5 ] }
	"""

	dict_key = 'power_meter_list'
	tag_map_size = len(WA_TAG_NAME_MAP)
	power_meter_list = [x for x in range(1, tag_map_size)]
	power_meter_dict = {dict_key: power_meter_list}

	return power_meter_dict


def get_energy_consumption_today(wa_headers, power_meter_ids, interval):
	"""
	Function: B11 本日電量
	URL: http://host:port/get_energy_consumption_today?power_meter_id=id&date=d&intervaltype=i&interval=x
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param interval: =x (x: 15, 30, or 60, representing integer interval value (>0) with the unit of Minute.)
	:return:
		if interval == 15:
			{ "energy_consumption_today":
			[ { "time_0_6": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_6_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_12_18": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_18_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
		if interval == 30:
			{ "energy_consumption_today":
			[ { "time_0_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_12_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
		if interval == 60:
			{ "energy_consumption_today":
			[ { "time_0_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
	"""

	# Date is today
	now = datetime.datetime.now()
	return get_energy_consumption_day(wa_headers, power_meter_ids, now, interval, values_key='energy_consumption_today')


def get_energy_consumption_history(wa_headers, power_meter_ids, date, data_range, interval):
	"""
	Function: B12-1 - 用電趨勢（日） & B12-2 - 用電趨勢（月）
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param date: the date in which to retrieve the energy consumption data
	:param data_range: =r (r: d (day) representing data range is a day, r: m (month) representing data range is a month).
	:param interval:
		if data_range == d:
			=x (x: 15, 30, or 60, representing integer interval value (>0) with the unit of Minute.)
		if data_range == m:
			=x (x: 1, representing integer interval value (>0) with the unit of day.)
	:return:
		if data_range == d:
			if interval == 15:
				{ "energy_consumption_day": [
				{ "time_0_6": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_6_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_18": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_18_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"sum": 2048 }
			if interval == 30:
				{ "energy_consumption_day": [
				{ "time_0_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"sum": 2048 }
			if interval == 60:
				{ "energy_consumption_day": [
				{ "time_0_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ] ,
				"sum": 2048 }
		if data_range == m:
			{ "energy_consumption_month": [ { "day_1_31": [ 1, 2, 3, 4, 5, ..., 31 ] } ],
			"sum": 4096  }
	"""

	if data_range == 'd':  # day
		return get_energy_consumption_day(wa_headers, power_meter_ids, date, interval,
		                                  values_key='energy_consumption_day')
	elif data_range == 'm':  # month
		return get_energy_consumption_month(wa_headers, power_meter_ids, date, interval,
		                                    values_key='energy_consumption_month')
	else:
		return construct_error_json("0006")


def get_energy_consumption_history_export(wa_headers, power_meter_ids, date, data_range, interval):
	"""
	Function: B12-1 - 用電趨勢（日）匯出 & B12-2 - 用電趨勢（月）匯出
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param date: the date in which to retrieve the energy consumption data
	:param data_range: =r (r: d (day) representing data range is a day, r: m (month) representing data range is a month).
	:param interval:
		if data_range == d:
			=x (x: 15, 30, or 60, representing integer interval value (>0) with the unit of Minute.)
		if data_range == m:
			=x (x: 1, representing integer interval value (>0) with the unit of day.)
	:return: a link to the file like:
		{ "csv_file_link": "http://host:port/static/exportfiles/XXXX.csv" }
	"""

	fixed_data_range = 'd'  # Data range will always be days
	interval = 15  # Interval will always be 15 minutes

	energy_consumption_history_list = []
	if data_range == 'd':
		energy_consumption_history = get_energy_consumption_history(wa_headers, power_meter_ids, date, fixed_data_range,
		                                                            interval)
		energy_consumption_history_list.append(energy_consumption_history)
	elif data_range == 'm':
		month_range = monthrange(date.year, date.month)
		for day in range(1, month_range[1] + 1):
			current_date = datetime.datetime(date.year, date.month, day=day)
			energy_consumption_history = get_energy_consumption_history(wa_headers, power_meter_ids, current_date, fixed_data_range,
		                                                            interval)
			energy_consumption_history_list.append(energy_consumption_history)

	# Create the file
	random1 = random.randint(0, 9)
	random2 = random.randint(0, 9)
	random3 = random.randint(0, 9)
	random4 = random.randint(0, 9)
	file_name = "{0}{1}{2}{3}.csv".format(random1, random2, random3, random4)
	file_directory = FILE_EXPORT_PATH
	file_path = file_directory + '/' + file_name
	csv_file = open(file_path, 'w')

	# File construction
	# Headers
	headers = "date,time,electricity consumption\n"
	csv_file.write(headers)
	# Data
	# Reset date if data range is month
	if data_range == 'm':
		date = datetime.datetime(date.year, date.month, day=1)
	for energy_consumption_history in energy_consumption_history_list:
		for key in energy_consumption_history:
			if isinstance(energy_consumption_history[key], list):
				time_list = energy_consumption_history[key]
				for data_dict in time_list:
					for data_dict_key in data_dict:
						data_list = data_dict[data_dict_key]
						for data_point in data_list:
							date_string = date.strftime(FILE_EXPORT_DATETIME_FORMAT)
							time_string = date.strftime(FILE_EXPORT_TIME_FORMAT)
							line = "{0},{1},{2}\n".format(date_string, time_string, data_point)
							csv_file.write(line)
							date += datetime.timedelta(minutes=interval)

	csv_file.close()

	# Create dictionary to return
	export_dic = {'csv_file_link': "http://{0}:{1}/{2}".format(options.host, options.port, file_path)}
	return export_dic


def get_energy_consumption_history_comparison(wa_headers, power_meter_ids, date1, date2, data_range, interval):
	"""
	Function: B13 - 用電比較 (日比較) & B14 - 用電比較 (月比較)
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param date1: the first date in which to retrieve the energy consumption data
	:param date2: the second date in which to retrieve the energy consumption data
	:param data_range: =r (r: d (day) representing data range is a day, r: m (month) representing data range is a month).
	:param interval:
		if data_range == d:
			=x (x: 15, 30, or 60, representing integer interval value (>0) with the unit of Minute.)
		if data_range == m:
			=x (x: 1, representing integer interval value (>0) with the unit of day.)
	:return:
		if data_range == d:
			if interval == 15:
				{
				"energy_consumption_date_1": [
				{ "time_0_6": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_6_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_18": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_18_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"energy_consumption_date_2": [
				{ "time_0_6": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_6_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_18": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_18_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"sum_date_1": 2048 , "sum_date_2": 2048
				}
			if interval == 30:
				{
				"energy_consumption_date_1":[
				{ "time_0_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"energy_consumption_date_2": [
				{ "time_0_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
				{ "time_12_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"sum_date_1": 2048 , "sum_date_2": 2048
				}
			if interval == 60:
				{
				"energy_consumption_date_1": [
				{ "time_0_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
				"energy_consumption_date_2": [
				{ "time_0_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ] ,
				"sum_date_1": 2048 , "sum_date_2": 2048
				}
		if data_range == m:
			{
			"energy_consumption_month_1": [
			{ "day_1_31": [ 1, 2, 3, 4, 5, ..., 31 ] } ],
			"energy_consumption_month_2": [
			{ "day_1_31": [ 1, 2, 3, 4, 5, ..., 31 ] } ],
			"sum_month_1": 2048 , "sum_month_2": 2048
			}
	"""

	if data_range == 'd':  # day
		values_key1 = 'energy_consumption_date_1'
		values_key2 = 'energy_consumption_date_2'
		energy_consumption1 = \
			get_energy_consumption_day(wa_headers, power_meter_ids, date1, interval,
			                           values_key=values_key1, sum_key='sum_date_1')
		energy_consumption2 = \
			get_energy_consumption_day(wa_headers, power_meter_ids, date2, interval,
			                           values_key=values_key2, sum_key='sum_date_2')
	elif data_range == 'm':  # month
		values_key1 = 'energy_consumption_month_1'
		values_key2 = 'energy_consumption_month_2'
		energy_consumption1 = \
			get_energy_consumption_month(wa_headers, power_meter_ids, date1, interval,
			                             values_key=values_key1, sum_key='sum_month_1')
		energy_consumption2 = \
			get_energy_consumption_month(wa_headers, power_meter_ids, date2, interval,
			                             values_key=values_key2, sum_key='sum_month_2')
	else:
		return construct_error_json("0006")

	# Construct final Json object
	energy_consumption_comparison = {}
	for key in energy_consumption1:
		energy_consumption_comparison[key] = energy_consumption1[key]
	for key in energy_consumption2:
		energy_consumption_comparison[key] = energy_consumption2[key]

	return energy_consumption_comparison


def get_energy_consumption_day(wa_headers, power_meter_ids, date, interval, **kwargs):
	"""
	Get energy consumption web service for a given date
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param date: the date in which to retrieve the energy consumption data
	:param interval: =x (x: 15, 30, or 60, representing integer interval value (>0) with the unit of Minute.)
	:param kwargs:
		values_key - The key string to use for the values
		sum_key - The key string to use for the sum
	:return:
		if interval == 15:
			{ "energy_consumption_day":
			[ { "time_0_6": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_6_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_12_18": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_18_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
		if interval == 30:
			{ "energy_consumption_day":
			[ { "time_0_12": [ 1, 2, 3, 4, 5, ..., 24 ] },
			{ "time_12_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
		if interval == 60:
			{ "energy_consumption_day":
			[ { "time_0_24": [ 1, 2, 3, 4, 5, ..., 24 ] } ],
			"sum": 2048 }
	"""

	# Json keys
	values_key = kwargs.get('values_key') if kwargs.get('values_key') is not None else 'energy_consumption_day'
	sum_key = kwargs.get('sum_key') if kwargs.get('sum_key') is not None else 'sum'

	start_time = datetime.datetime(date.year, date.month, date.day)
	start_time_string = start_time.strftime(webaccess.WA_DATETIME_FORMAT)
	interval_type = 'M'  # interval type will always be minutes for a day's records
	records = 24  # records will always be 24 for a day's records

	# Get data logs depending on the interval
	no_sets = 60 / interval
	delta_hours = records / (60 / interval)
	energy_consumption_dict = {values_key: []}
	sum = 0
	for i in range(0, no_sets):
		# Call the data log web service:
		# start_time - the starting time in the format YYYY-MM-DD HH:mm:ss
		# interval_type - S (seconds), M (minutes), H (hours), D (days)
		# interval - Date Time interval, unit as type
		# records - number of records
		# data_type - 0 (last), 1 (min), 2 (max), 3 (avg)
		data_log_string = webaccess.get_data_log(wa_headers,
		                                         PROJECT_NAME,
		                                         NODE_NAME,
		                                         tag_names=power_meter_ids,
		                                         start_time=start_time_string,
		                                         interval_type=interval_type,
		                                         interval=interval,
		                                         records=records,
		                                         data_type=DATA_TYPE)

		# Build values list
		result_values_dict = {}
		result_values_list = [0] * records
		data_log_dict = ast.literal_eval(data_log_string)  # Convert str object to dict
		for data_log in data_log_dict['DataLog']:
			data_log_values = data_log['Values']
			j = 0
			for data_log_string_value in data_log_values:
				try:
					value = int(data_log_string_value)
				except ValueError:
					value = 0
				result_values_list[j] += value
				sum += value
				j += 1

		# Build key
		starting_hour = start_time.hour
		ending_hour = starting_hour + delta_hours
		term_key_prefix = "time"
		term_key = "{0}_{1}_{2}".format(term_key_prefix, starting_hour, ending_hour)

		# Add value set to dictionary
		result_values_dict[term_key] = result_values_list

		energy_consumption_dict[values_key].append(result_values_dict)

		# Advance delta_hours
		start_time += datetime.timedelta(hours=delta_hours)
		start_time_string = start_time.strftime(webaccess.WA_DATETIME_FORMAT)

	# Finally, place sum of all values
	energy_consumption_dict[sum_key] = sum

	return energy_consumption_dict


def get_energy_consumption_month(wa_headers, power_meter_ids, date, interval, **kwargs):
	"""
	Get energy consumption web service for a given month
	:param wa_headers: the headers to send to WebAccess
	:param power_meter_ids: list of power meters whose energy consumption will be checked
	:param date: the date in which to retrieve the energy consumption data
	:param interval: =x (x: 1, representing integer interval value (>0) with the unit of day.)
	:param kwargs:
		values_key - The key string to use for the values
		sum_key - The key string to use for the sum
	:return:
		{ "energy_consumption_month": [ { "day_1_31": [ 1, 2, 3, 4, 5, ..., 31 ] } ],
		"sum": 4096  }
	"""

	# Json keys
	values_key = kwargs.get('values_key') if kwargs.get('values_key') is not None else 'energy_consumption_month'
	sum_key = kwargs.get('sum_key') if kwargs.get('sum_key') is not None else 'sum'

	start_time = datetime.datetime(date.year, date.month, 1)
	start_time_string = start_time.strftime(webaccess.WA_DATETIME_FORMAT)
	interval_type = 'd'  # interval type will always be days for a month's records
	records = 31  # records will always be 31 for a month's records

	# Get data logs depending on the interval
	no_sets = 1 / interval
	delta_days = 30
	energy_consumption_dict = {values_key: []}
	sum = 0
	for i in range(0, no_sets):
		# Call the data log web service:
		# start_time - the starting time in the format YYYY-MM-DD HH:mm:ss
		# interval_type - S (seconds), M (minutes), H (hours), D (days)
		# interval - Date Time interval, unit as type
		# records - number of records
		# data_type - 0 (last), 1 (min), 2 (max), 3 (avg)
		data_log_string = webaccess.get_data_log(wa_headers,
		                                         PROJECT_NAME,
		                                         NODE_NAME,
		                                         tag_names=power_meter_ids,
		                                         start_time=start_time_string,
		                                         interval_type=interval_type,
		                                         interval=interval,
		                                         records=records,
		                                         data_type=DATA_TYPE)

		# Build values list
		result_values_dict = {}
		result_values_list = [0] * records
		data_log_dict = ast.literal_eval(data_log_string)  # Convert str object to dict
		for data_log in data_log_dict['DataLog']:
			data_log_values = data_log['Values']
			j = 0
			for data_log_string_value in data_log_values:
				try:
					value = int(data_log_string_value)
				except ValueError:
					value = 0
				result_values_list[j] += value
				sum += value
				j += 1

		# Build key
		starting_day = start_time.day
		ending_day = starting_day + delta_days
		time_key_prefix = "day"
		time_key = "{0}_{1}_{2}".format(time_key_prefix, starting_day, ending_day)

		# Add value set to dictionary
		result_values_dict[time_key] = result_values_list

		energy_consumption_dict[values_key].append(result_values_dict)

		# Advance delta_hours
		start_time += datetime.timedelta(days=delta_days)
		start_time_string = start_time.strftime(webaccess.WA_DATETIME_FORMAT)

	# Finally, place sum of all values
	energy_consumption_dict[sum_key] = sum

	return energy_consumption_dict