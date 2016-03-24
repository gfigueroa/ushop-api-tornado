"""
Main entry point for the UShop Tornado Web Server.
This module should be used to initialize the whole server.
"""

# !/usr/bin/env python
import tornado.httpserver
import tornado.ioloop
import tornado.web
from tornado.options import options
import logging
from lib.scheduled_tasks import Scheduler

from settings import settings
from urls import url_patterns

logger = logging.getLogger('ushop.' + __name__)


class UShopWebServer(tornado.web.Application):
	"""
	Wrapper class for the Tornado Application.
	"""
	def __init__(self):
		tornado.web.Application.__init__(self, url_patterns, autoreload=settings['debug'], **settings)

def main():
	"""
	Initialize the UShop Web Server.
	"""
	app = UShopWebServer()
	http_server = tornado.httpserver.HTTPServer(app)
	http_server.listen(options.port)
	logger.info("Starting UShop_Web_Server (debug=%s)..." % (app.settings['debug']))
	main_loop = tornado.ioloop.IOLoop.instance()

	# Begin scheduled tasks
	logger.info("Starting scheduled tasks...")
	scheduler = Scheduler(main_loop)
	scheduler.run_scheduled_tasks()

	# Begin main loop
	logger.info("UShop_Web_Server running at {0}:{1}".format(options.host, options.port))
	main_loop.start()

	logger.info("UShop_Web_Server terminated")


if __name__ == "__main__":
	main()