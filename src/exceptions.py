# encoding: utf-8

class StoryUpToDateException(Exception):
    def __init__(self):
        self.message = "Downloaded story already contains as many chapters as on the website."
        super().__init__(self.message)


class MoreChaptersLocallyException(Exception):
    def __init__(self):
        self.message = "There are more chapters at the url than in the saved epub."
        super().__init__(self.message)


class BadDataException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TooManyRequestsException(Exception):
    def __init__(self):
        self.message = "Too many requests for now."
        super().__init__(self.message)
