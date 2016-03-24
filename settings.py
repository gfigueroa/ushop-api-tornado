import logging
import tornado
import tornado.template
import os
from tornado.options import define, options
import logconfig

# Make filepaths relative to settings.
path = lambda root, *a: os.path.join(root, *a)
ROOT = os.path.dirname(os.path.abspath(__file__))

define("host", default="localhost", help="app host", type=str)
define("port", default=8888, help="run on the given port", type=int)
define("config", default=None, help="tornado config file")
define("debug", default=False, help="debug mode")
tornado.options.parse_command_line()

STATIC_ROOT = path(ROOT, 'static')
TEMPLATE_ROOT = path(ROOT, 'templates')


# Deployment Configuration

class DeploymentType:
    PRODUCTION = "PRODUCTION"
    DEV = "DEV"
    SOLO = "SOLO"
    STAGING = "STAGING"
    dict = {
        SOLO: 1,
        PRODUCTION: 2,
        DEV: 3,
        STAGING: 4
    }


if 'DEPLOYMENT_TYPE' in os.environ:
    DEPLOYMENT = os.environ['DEPLOYMENT_TYPE'].upper()
else:
    DEPLOYMENT = DeploymentType.SOLO

settings = {}
settings['debug'] = DEPLOYMENT != DeploymentType.PRODUCTION or options.debug
settings['static_path'] = STATIC_ROOT
settings['cookie_secret'] = "your-cookie-secret"
settings['xsrf_cookies'] = True
settings['template_loader'] = tornado.template.Loader(TEMPLATE_ROOT)

# UShop specific settings
settings['WA_ROOT_URL'] = "http://211.23.50.153/WaWebService/"  # The WebAccess web services URL
settings['SA_ROOT_URL'] = "http://localhost:8080/webresources/"  # The SUSIAccess server web services URL

'''
The Tags whose Tag Values and Data Log will be retrieved.
To give the flexibility of the mapping, we need a variable to do the mapping in tornado system.
The variable mapping the power_meter_id to data tag will look like this: MAPPING_METER_ID_2_DATA_TAG[A+B+C+D, A, B, C, D].
'''
settings['WA_TAG_NAMES'] = [["kw"], "kw"]

settings['FILE_EXPORT_PATH'] = "static/exportfiles"  # Relative path where export files will be stored
settings['FILE_DELETE_INTERVAL_HOURS'] = 1  # Interval to run delete file export scheduled task
settings['FILE_EXPORT_LIFETIME_HOURS'] = 1  # Number of hours export files can last in the system

# WebAccess web service settings
settings['PROJECT_NAME'] = "85"
settings['NODE_NAME'] = "energy"
settings['DATA_TYPE'] = "3"  # The DataType value for power metering data - 0 (last), 1 (min), 2 (max), 3 (avg)

SYSLOG_TAG = "ushop"
SYSLOG_FACILITY = logging.handlers.SysLogHandler.LOG_LOCAL2

# See PEP 391 and logconfig for formatting help.  Each section of LOGGERS
# will get merged into the corresponding section of log_settings.py.
# Handlers and log levels are set up automatically based on LOG_LEVEL and DEBUG
# unless you set them here.  Messages will not propagate through a logger
# unless propagate: True is set.
LOGGERS = {
    'loggers': {
        'ushop': {},
    },
}

if settings['debug']:
    LOG_LEVEL = logging.DEBUG
else:
    LOG_LEVEL = logging.INFO
USE_SYSLOG = DEPLOYMENT != DeploymentType.SOLO

logconfig.initialize_logging(SYSLOG_TAG, SYSLOG_FACILITY, LOGGERS,
                             LOG_LEVEL, USE_SYSLOG)

if options.config:
    tornado.options.parse_config_file(options.config)
