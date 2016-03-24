import tornado
from tornado.ioloop import IOLoop
from tornado.web import RequestHandler, Application, url


class MainHandler(RequestHandler):
    def get(self):
        self.write('<a href="%s">link to story 1</a>' %
                   self.reverse_url("story", "1"))


class StoryHandler(RequestHandler):
    def initialize(self, db):
        self.db = db

    def get(self, story_id):
        self.write("this is story %s" % story_id)

db = ""
app = Application([
    url(r"/", MainHandler),
    url(r"/story/([0-9]+)", StoryHandler, dict(db=db), name="story")
    ])

if __name__ == "__main__":
    app.listen(9991)
    IOLoop.current().start()