# coding=utf-8
from webapp import db


class NovelInfo(db.Model):
    task = db.Column(db.String(36), primary_key=True)
    start = db.Column(db.Integer, autoincrement=False)
    end = db.Column(db.Integer, autoincrement=False)
    title = db.Column(db.String(200))
    start_url = db.Column(db.String(200))
    request_time = db.Column(db.DateTime)

    def __init__(self, task, start, end, title, start_url, request_time):
        self.task = task
        self.start = start
        self.end = end
        self.title = title
        self.start_url = start_url
        self.request_time = request_time


class Chapter(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    chapter_number = db.Column(db.Integer, autoincrement=False)
    url = db.Column(db.String(200))
    content = db.Column(db.Text)
    task = db.Column(db.String(36))

    def __init__(self, task, chapter_number, url, content):
        self.chapter_number = chapter_number
        self.url = url
        self.content = content
        self.task = task
