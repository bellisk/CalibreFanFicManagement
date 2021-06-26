# encoding: utf-8

class StoryUpToDateException(Exception):
    def __init__(self):
        self.message = "Downloaded story already contains as many chapters as on the website."
        super().__init__(self.message)
