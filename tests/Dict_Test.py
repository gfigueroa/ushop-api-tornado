import tornado
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url


class MainHandler(RequestHandler):
    sensor_data = dict(sensor1=10, sensor2=20)
    sensor_module = dict(a=1, b=2, c=3, sensor_data=sensor_data)

    def get(self):
        self.write(self.sensor_module)


class MyFormHandler(RequestHandler):
    def get(self):
        self.write('<html><body><form action="/post" method="POST">'
                   '<input type="text" name="message">'
                   '<input type="submit" value="Submit">'
                   '</form></body></html>')

    def post(self):
        self.set_header("Content-Type", "text/plain")
        self.write("You wrote " + self.get_body_argument("message"))


db = ""
app = Application([
    url(r"/", MainHandler),
    url(r"/post", MyFormHandler)
    ])

if __name__ == "__main__":
    app.listen(9992)
    IOLoop.current().start()