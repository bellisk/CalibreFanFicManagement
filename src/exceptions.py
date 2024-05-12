# encoding: utf-8


class StoryUpToDateException(Exception):
    def __init__(self):
        self.message = (
            "Downloaded story already contains as many chapters as on the website."
        )
        super().__init__(self.message)


class MoreChaptersLocallyException(Exception):
    def __init__(self):
        self.message = (
            "There are more chapters in the saved epub than at the source url."
        )
        super().__init__(self.message)


class TempFileUpdatedMoreRecentlyException(Exception):
    def __init__(self):
        self.message = (
            "The saved epub has been updated more recently than the source url."
        )
        super().__init__(self.message)


class BadDataException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TooManyRequestsException(Exception):
    def __init__(self):
        self.message = "Too many requests for now."
        super().__init__(self.message)


class InvalidConfig(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class UrlsCollectionException(Exception):
    def __init__(self, error_message):
        self.message = f"Error collecting fic urls: {error_message}"
        super().__init__(self.message)


class EmptyFanFicFareResponseException(Exception):
    def __init__(self, command):
        self.message = (
            f"Got no output when running the following command: {command}"
        )
