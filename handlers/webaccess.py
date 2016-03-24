"""
Module to handle access to the WebAccess web services. Includes SUSIAccessHandler and other necessary
methods and classes.
"""

import urllib2
from datetime import datetime
from datetime import timedelta
from tornado import httpclient
from tornado.httputil import HTTPHeaders
from handlers.base import BaseHandler, require_basic_auth
import logging
import base64
from xml.etree import ElementTree
from settings import settings
import json

# Global variables
logger = logging.getLogger('ushop.' + __name__)
WA_ROOT_URL = settings['WA_ROOT_URL']
WA_TAG_NAMES = settings['WA_TAG_NAMES'][0]
WA_DATETIME_FORMAT = '%Y-%m-%d %H:%M:%S'  # The datetime format required by WebAccess web services


@require_basic_auth
class WebAccessHandler(BaseHandler):
	"""
	A class to handle all calls to the WebAccess web services.
	"""

	# Private members
	# WebAccess-related (STATIC)
	_wa_user = 'admin'
	_wa_password = ''
	_wa_user_password_enc = base64.b64encode(_wa_user + ':' + _wa_password)
	_wa_headers = HTTPHeaders({"authorization": "Basic {0}".format(_wa_user_password_enc)})

	def initialize(self):
		pass

	def data_received(self, chunk):
		pass

	def get(self, ws_type, ws_name, params, trash, **kwargs):  # TODO: Get rid of the 'trash' parameter
		"""
		When using the get method, the WebAccessHandler fetches the required WebAccess web service and
		writes the result.
		:param ws_type: Whether the type of web service to fetch - JSON or XML
		:param ws_name: The name of the web service to fetch
		:param params: The parameters for the web service
		:param trash: Trash argument that appears for no reason
		:param **kwargs: this includes the basicauth_user and basicauth_pass
		:return:
		"""

		# Check the web service type (JSON or XML)
		if ws_type.lower() == "json":
			get_json = True
			self.set_header("content-type", "application/json; charset=utf-8")
		else:
			get_json = False
			self.set_header("content-type", "application/xml; charset=utf-8")

		param_list = str(params).split("/")
		if len(param_list) >= 1:
			del param_list[0]  # First parameter is empty

		# Basic user authentication (override)
		wa_basicauth_user = kwargs['basicauth_user']
		wa_basicauth_pass = kwargs['basicauth_pass']
		wa_user_password_enc = base64.b64encode(wa_basicauth_user + ':' + wa_basicauth_pass)
		self._wa_headers = HTTPHeaders({"authorization": "Basic {0}".format(wa_user_password_enc)})

		try:
			result = get_wa_web_service(self._wa_headers, ws_name, param_list if param_list else None, get_json)
			if "error" not in result:
				self.write(result)
			else:
				logger.error(result, exc_info=True)
				self.send_error(status_code=400, reason=result)
		except httpclient.HTTPError, e:
			if e.code == 401:  # Authentication error, set Authentication header to None
				# self.request.headers.pop('Authorization')
				self.send_error(status_code=401, reason="Wrong user name and/or password")

	def _async_logon(self):
		"""Private function to test logon web service using an asynchronous, non-blocking request
		"""
		server_url = "http://211.23.50.153/WaWebService/Json/Logon"
		self.async_request(self.write, server_url, method=u'GET', headers=self._wa_headers, body=None)
		logger.info("testing __logon()...")


def get_wa_web_service(original_headers, ws_name, param_list=None, get_json=True):
	"""
	Fetches a GET web service from the WebAccess url
	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to post_wa_web_service() is performed.
	:param ws_name: the first parameter of the web service call is the name of the web service
	:param param_list: the list of parameters for the web service being called, default - None
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:return the web service result as a string object
	"""

	headers = original_headers.copy()
	# Check whether a Json format is requested or an XML format
	if get_json:
		url = WA_ROOT_URL + "Json/"
		headers.add("content-type", "application/json; charset=utf-8", )
	else:
		url = WA_ROOT_URL
		headers.add("content-type", "application/xml; charset=utf-8", )

	# Check the web service name
	# Logon
	if ws_name.lower() == "logon":
		url += "Logon"
	# ProjectList
	elif ws_name.lower() == "projectlist":
		url += "ProjectList"
	# ProjectDetail
	elif ws_name.lower() == "projectdetail":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "ProjectDetail"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
	# NodeList
	elif ws_name.lower() == "nodelist":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "NodeList"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
	# NodeDetail
	elif ws_name.lower() == "nodedetail":
		if len(param_list) < 2:
			return "error: missing_parameters"
		else:
			url += "NodeDetail"
			project_name = param_list[0]
			node_name = param_list[1]
			url += "/{0}/{1}".format(project_name, node_name)
	# PortList
	elif ws_name.lower() == "portlist":
		if len(param_list) < 2:
			return "error: missing_parameters"
		else:
			url += "PortList"
			project_name = param_list[0]
			node_name = param_list[1]
			url += "/{0}/{1}".format(project_name, node_name)
	# PortDetail
	elif ws_name.lower() == "portdetail":
		if len(param_list) < 3:
			return "error: missing_parameters"
		else:
			url += "PortDetail"
			project_name = param_list[0]
			node_name = param_list[1]
			port_number = param_list[2]
			url += "/{0}/{1}/{2}".format(project_name, node_name, port_number)
	# DeviceList
	elif ws_name.lower() == "devicelist":
		if len(param_list) < 3:
			return "error: missing_parameters"
		else:
			url += "DeviceList"
			project_name = param_list[0]
			node_name = param_list[1]
			port_number = param_list[2]
			url += "/{0}/{1}/{2}".format(project_name, node_name, port_number)
	# DeviceDetail
	elif ws_name.lower() == "devicedetail":
		if len(param_list) < 4:
			return "error: missing_parameters"
		else:
			url += "DeviceDetail"
			project_name = param_list[0]
			node_name = param_list[1]
			port_number = param_list[2]
			device_name = param_list[3]
			url += "/{0}/{1}/{2}/{3}".format(project_name, node_name, port_number, device_name)
	# TagList (can have additional NODE_NAME, port_number, and device_name parameters)
	elif ws_name.lower() == "taglist":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "TagList"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
			if len(param_list) > 1:
				node_name = param_list[1]
				url += "/{0}".format(node_name)
				if len(param_list) > 2:
					port_number = param_list[2]
					url += "/{0}".format(port_number)
					if len(param_list) > 3:
						device_name = param_list[3]
						url += "/{0}".format(device_name)
	# TagDetail
	elif ws_name.lower() == "tagdetail":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			project_name = param_list[0]
			response = get_tag_details(original_headers, project_name, get_json=get_json)
			return response
	# GetTagValue
	elif ws_name.lower() == "gettagvalue":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			project_name = param_list[0]
			response = get_tag_values(original_headers, project_name, WA_TAG_NAMES, get_json)
			return response
	# GetDataLog
	elif ws_name.lower() == "getdatalog":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			project_name = param_list[0]
			if len(param_list) > 1:
				node_name = param_list[1]
			else:
				node_name = None
			response = get_data_log(original_headers, project_name, node_name, WA_TAG_NAMES, get_json)
			return response
	# Wrong web service name
	else:
		return "error: wrong_name"

	http_client = httpclient.HTTPClient()
	try:
		http_request = httpclient.HTTPRequest(url, headers=headers)
		response = http_client.fetch(http_request)
	except httpclient.HTTPError, e:
		logger.error(("Error:", e), exc_info=True)
		raise e
	finally:
		http_client.close()

	return response.body


def get_tag_values(original_headers, project_name, tag_names=None, get_json=True):
	"""
	This method calls a series of web services from the WebAccess in order to retrieve the Tag Values of a project.
	It has been made in order to have a higher level of abstraction, since the original GetTagValue web service
	is a POST request.
	The XML response will look like this:
	<GetTagValue xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
		<Result>
			<Ret>0</Ret>
			<Total>2</Total>
		</Result>
		<Values>
			<Value>
				<Name>kw</Name>
				<Value>-1</Value>
				<Quality>1</Quality>
			</Value>
			<Value>
				<Name>kw1</Name>
				<Value>-1</Value>
				<Quality>1</Quality>
			</Value>
		</Values>
	</GetTagValue>
	The Json response will look like this:
	{"Result":{"Ret":0,"Total":2},"Values":[{"Name":"kw","Value":-1,"Quality":1},{"Name":"kw1","Value":-1,"Quality":1}]}

	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to post_wa_web_service() is performed.
	:param project_name: the name of the Project whose Tag Values will be retrieved
	:param tag_names: the names of the Tags whose Tag Values will be retrieved, default - None (for all Tags)
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:return: a Json or XML web service with the tag values for the given Project and Tags
	"""

	# 1. Get TagList (names) for the given project
	if tag_names is None:
		tag_names = get_tag_names(original_headers, project_name, get_json)

	# 2. Create POST request
	if get_json:
		# Json request body looks like this:
		# {
		# "Tags":[{
		# "Name": "String"
		# }]
		# }
		json_request_body = {'Tags': []}
		for tag_name in tag_names:
			json_request_body['Tags'].append({'Name': tag_name})
		request_body = json.dumps(json_request_body)
	else:
		# XML request body looks like this:
		# <GetTagValueText>
		# <Tags>
		# <TagName>
		#           <Name>String</Name>
		#       </TagName>
		#   </Tags>
		# </GetTagValueText>
		xml_tag_names = ""
		for tag_name in tag_names:
			xml_tag_names += "<TagName><Name>{0}</Name></TagName>".format(tag_name)
		request_body = "<GetTagValue><Tags>{0}</Tags></GetTagValue>".format(xml_tag_names)

	# 3. Send POST request and get Tag Values
	# post_wa_web_service(WA_ROOT_URL, original_headers, ws_name, slash_param_list=None, data=None, get_json=True)
	response, ws_name = \
		post_wa_web_service(original_headers, "GetTagValue", [project_name], request_body, get_json)

	return response


def get_data_log(original_headers, project_name, node_name=None, tag_names=None, get_json=True, **kwargs):
	"""
	This method calls a series of web services from the WebAccess in order to retrieve the Data Log of the Tags
	in a Project.
	It has been made in order to have a higher level of abstraction, since the original GetDataLog web service
	is a POST request.
	The XML response will look like this:
	<GetDataLog xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
		<Result>
			<Ret>0</Ret>
			<Total>1</Total>
		</Result>
		<DataLog>
			<Tags>
				<Name>kw</Name>
				<Total>15</Total>
				<StartTime>2015-04-25 20:25:47</StartTime>
				<Values>
					<string>0</string>
					<string>0</string>
					<string>0</string>
				</Values>
			</Tags>
		</DataLog>
	</GetDataLog>
	The Json response will look like this:
	{"Result":
		{"Ret":0,"Total":2},
	"DataLog":[
		{"Name":"kw",
		"Total":15,
		"StartTime":"2015-04-25 20:16:50",
		"Values":["0","0","0","0","0","0","0","0","0","0","0","0","0","0","0"]},
		{"Name":"kw1",
		"Total":15,
		"StartTime":"2015-04-25 20:16:50",
		"Values":["#","#","#","#","#","#","#","#","#","#","#","#","#","#","#"]}
		]
	}

	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to post_wa_web_service() is performed.
	:param project_name: the name of the Project whose Data Log will be retrieved
	:param node_name: the name of the Node in the Project whose Data Log will be retrieved, default - None
	:param tag_names: the names of the Tags whose Tag Values will be retrieved, default - None (for all Tags)
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:param kwargs:
		start_time - the starting time in the format YYYY-MM-DD HH:mm:ss
		interval_type - S (seconds), M (minutes), H (hours), D (days)
		interval - Date Time interval, unit as type
		records - number of records
		data_type - 0 (last), 1 (min), 2 (max), 3 (avg)
	:return: a Json or XML web service with the Data Logo for the given Project, Node and Tags
	"""

	# 1. Get TagList (names) for the given project
	if tag_names is None:
		tag_names = get_tag_names(original_headers, project_name, get_json)

	# 2. Create POST request
	start_time = kwargs.get('start_time')
	if start_time is None:
		before = datetime.now() - timedelta(minutes=15)
		start_time = before.strftime(WA_DATETIME_FORMAT)  # StartTime - YYYY-MM-DD HH:mm:ss
	interval_type = kwargs.get('interval_type')
	if interval_type is None:
		interval_type = 'S'  # IntervalType - S (seconds), M (minutes), H (hours), D (days)
	interval = kwargs.get('interval')
	if interval is None:
		interval = 1  # Interval - Date Time interval, unit as type
	records = kwargs.get('records')
	if records is None:
		records = 15  # Records - number of records
	data_type = kwargs.get('data_type')
	if data_type is None:
		data_type = '0'  # DataType - 0 (last), 1 (min), 2 (max), 3 (avg)

	if get_json:
		# Json request body looks like this:
		# {
		# "StartTime": "2015-04-21 18:05:00",
		# "IntervalType": "String",
		#   "Interval": Value,
		#   "Records": Value,
		#   "Tags":[{ "Name": "String", "DataType": "String" }]
		# }
		json_tags = []
		for tag_name in tag_names:
			json_tags.append({'Name': tag_name, 'DataType': data_type})
		json_request_body = {'StartTime': start_time, 'IntervalType': interval_type, 'Interval': interval,
		                     'Records': records, 'Tags': json_tags}
		request_body = json.dumps(json_request_body)
	else:
		# XML request body looks like this:
		# <GetDataLog>
		# <StartTime>yyyy-mm-dd HH:MM:SS</StartTime>
		# <IntervalType>M</IntervalType>
		#   <Interval>1</Interval>
		#   <Records>2</Records>
		#   <Tags>
		#       <Tag>
		#           <Name>Tag1</Name>
		#           <DataType>0</DataType>
		#       </Tag>
		#   </Tags>
		# </GetDataLog>
		xml_tags = ""
		for tag_name in tag_names:
			xml_tags += "<Tag><Name>{0}</Name><DataType>{1}</DataType></Tag>".format(tag_name, data_type)

		request_body = "<GetDataLog>" \
		               "<StartTime>{0}</StartTime>" \
		               "<IntervalType>{1}</IntervalType>" \
		               "<Interval>{2}</Interval>" \
		               "<Records>{3}</Records>" \
		               "<Tags>{4}</Tags>" \
		               "</GetDataLog>".format(start_time, interval_type, interval, records, xml_tags)

	# 3. Send POST request and get Tag Values
	# post_wa_web_service(WA_ROOT_URL, original_headers, ws_name, slash_param_list=None, data=None, get_json=True)
	param_list = [project_name]
	if node_name is not None:
		param_list.append(node_name)
	response, ws_name = \
		post_wa_web_service(original_headers, "GetDataLog", param_list, request_body, get_json)

	return response


def get_tag_details(original_headers, project_name, tag_names=None, get_json=True):
	"""
	This method calls a series of web services from the WebAccess in order to retrieve the Tag Details of each
	Tag (or a specified list of Tags) in a project.
	It has been made in order to have a higher level of abstraction, since the original TagDetail web service
	is a POST request.
	The XML response will look like this:
	<TagDetail xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
		<Result>
			<Ret>0</Ret>
			<Total>2</Total>
		</Result>
		<Tags>
			<Tag>
				<NAME>kw</NAME>
				<DESCRP>Description</DESCRP>
				<TYPE>ANALOG</TYPE>
			</Tag>
			<Tag>
				<NAME>kw1</NAME>
				<DESCRP>Analog Output</DESCRP>
				<TYPE>ANALOG</TYPE>
			</Tag>
		</Tags>
		</TagDetail>
		The Json response will look like this:
		{"Result":
		{"Ret":0,"Total":2},
		"Tags":[
			{"NAME":"kw","DESCRP":"Description","TYPE":"ANALOG"},
			{"NAME":"kw1","DESCRP":"Analog Output","TYPE":"ANALOG"}
		]
	}
	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to post_wa_web_service() is performed.
	:param project_name: the name of the Project whose Tag Details will be retrieved
	:param tag_names: the names of the Tags whose Tag Details will be retrieved, default - None (for all Tags)
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:return: a Json or XML web service with the tag details of each (or a specified) Tag in the given Project
	"""

	# 1. Get TagList (names) for the given project
	if tag_names is None:
		tag_names = get_tag_names(original_headers, project_name, get_json)

	# 2. Define attribute name list
	attribute_names = ['NAME', 'DESCRP', 'TYPE']

	# 3. Create POST request
	if get_json:
		# Json request body looks like this:
		# {
		# "Tags":[{
		# "Name": "String"
		# "Attributes": [{
		#       "Name": "String"
		#   }]
		# }]
		# }
		json_request_body = {'Tags': []}
		for tag_name in tag_names:
			attributes = []
			for attribute_name in attribute_names:
				attributes.append({'Name': attribute_name})
			tags = {'Name': tag_name, 'Attributes': attributes}
			json_request_body['Tags'].append(tags)

		request_body = json.dumps(json_request_body)
	else:
		# XML request body looks like this:
		# <TagDetail>
		# <Tags>
		# <Tag>
		#           <Name>String</Name>
		#           <Attributes>
		#               <Attribute>
		#                   <Name>ALL</Name>
		#               </Attribute>
		#           </Attributes>
		#       </Tag>
		#   </Tags>
		# </TagDetail>
		xml_attributes = ""
		for attribute_name in attribute_names:
			xml_attributes += "<Attribute><Name>{0}</Name></Attribute>".format(attribute_name)

		xml_tags = ""
		for tag_name in tag_names:
			xml_tags += "<Tag><Name>{0}</Name><Attributes>{1}</Attributes></Tag>".format(tag_name, xml_attributes)
		request_body = "<TagDetail><Tags>{0}</Tags></TagDetail>".format(xml_tags)

	# 4. Send POST request and get Tag Details
	# post_wa_web_service(WA_ROOT_URL, original_headers, ws_name, slash_param_list=None, data=None, get_json=True)
	response, ws_name = \
		post_wa_web_service(original_headers, "TagDetail", [project_name], request_body, get_json)

	return response


def get_tag_names(original_headers, project_name, get_json=True):
	"""
	Get a list of all Tag Names for the given project.
	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to post_wa_web_service() is performed.
	:param project_name: the name of the Project whose Tag names will be retrieved
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:return: the list of tag names from the given project
	"""

	tag_list = get_wa_web_service(original_headers, "TagList", [project_name], get_json)
	tag_names = []
	# Check if it is Json or XML
	if get_json:
		# Json string will look like this:
		# {
		# "Result": {"Ret": 0, "Total": 2},
		# "Tags":[
		#       {
		#       "Name": "kw",
		#       "Description": "Description"
		#       },
		#       {
		#       "Name": "kw1",
		#       "Description": "Analog Output"
		#       }
		#   ]
		# }
		json_tag_list = json.loads(tag_list)
		result = json_tag_list['Result']
		total = int(result['Total'])
		if total > 0:
			for tag in json_tag_list['Tags']:
				tag_names.append(tag['Name'])
	else:
		# XML string will look like this:
		# <TagList xmlns:i="http://www.w3.org/2001/XMLSchema-instance">
		# <Result>
		# <Ret>0</Ret>
		#         <Total>2</Total>
		#     </Result>
		#     <Tags>
		#         <Tag>
		#             <Name>kw</Name>
		#             <Description>Description</Description>
		#         </Tag>
		#         <Tag>
		#             <Name>kw1</Name>
		#             <Description>Analog Output</Description>
		#         </Tag>
		#     </Tags>
		# </TagList>
		xml_root = ElementTree.fromstring(tag_list)
		result = xml_root.find('Result')
		total = int(result.find('Total').text)
		if total > 0:
			for tag_name in xml_root.iter('Name'):
				tag_names.append(tag_name.text)

	return tag_names


def post_wa_web_service(original_headers, ws_name, param_list=None, data=None, get_json=True):
	"""
	Fetches a POST web service from the WebAccess url. Returns a success or fail response.
	:rtype : str, str
	:param original_headers: the original headers needed to make the request to the WebAccess server. This object
	will be immutable, so its value will remain unchanged. These headers should be passed if another call to
	this function or to get_wa_web_service() is performed.
	:param ws_name: the first parameter of the web service call is the name of the web service
	:param param_list: the list of parameters for the web service being called, default - None
	:param data: the data string for the POST request, default - None
	:param get_json: whether to get the JSON web service (True) or the XML version (False), default - True
	:return the web service result as a string object
	"""

	headers = original_headers.copy()
	# Check whether a Json format is requested or an XML format
	if get_json:
		url = WA_ROOT_URL + "Json/"
		headers.add("content-type", "application/json; charset=utf-8", )
	else:
		url = WA_ROOT_URL
		headers.add("content-type", "application/xml; charset=utf-8", )

	# Check the web service name
	# TagDetail of given Project
	if ws_name.lower() == "tagdetail":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "TagDetail"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
	# GetTagValue of Tags in given Project
	elif ws_name.lower() == "gettagvalue":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "GetTagValue"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
	# GetTagValueText of Tags in given Project
	elif ws_name.lower() == "gettagvaluetext":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "GetTagValueText"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
	# GetDataLog of Tags in given Project
	elif ws_name.lower() == "getdatalog":
		if len(param_list) < 1:
			return "error: missing_parameters"
		else:
			url += "GetDataLog"
			project_name = param_list[0]
			url += "/{0}".format(project_name)
			if len(param_list) > 1:
				node_name = param_list[1]
				url += "/{0}".format(node_name)
	# Wrong web service name
	else:
		return "error: wrong_name"

	http_client = httpclient.HTTPClient()
	try:
		req = urllib2.Request(url)
		req.headers = headers
		response = urllib2.urlopen(req, data).read()
	except httpclient.HTTPError, e:
		logger.error(("Error:", e), exc_info=True)
		raise e
	finally:
		http_client.close()

	result = response

	return result, ws_name