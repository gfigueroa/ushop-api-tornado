import tornado
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url


class MainHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    def get(self):
        self.write("Hello, world")


class ByeHandler(tornado.web.RequestHandler):
    def data_received(self, chunk):
        pass

    def get(self):
        self.write("Goodbye, world")

application = tornado.web.Application([
    (r"/", MainHandler), (r"/bye", ByeHandler)
])

if __name__ == "__main__":
    application.listen(9999)
    tornado.ioloop.IOLoop.instance().start()