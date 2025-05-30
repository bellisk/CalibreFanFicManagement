# encoding: utf-8


class StoryUpToDateException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class MoreChaptersLocallyException(Exception):
    def __init__(self):
        self.message = (
            "There are more chapters in the saved epub than at the source url."
        )
        super().__init__(self.message)


class TempFileUpdatedMoreRecentlyException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class BadDataException(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)


class TooManyRequestsException(Exception):
    def __init__(self):
        self.message = "Too many requests for now."
        super().__init__(self.message)


class CloudflareWebsiteException(Exception):
    def __init__(self):
        self.message = (
            "Got Cloudflare Error 525: this means a temporary error on AO3's side."
        )
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
        self.message = f"Got no output when running the following command: {command}"
        super().__init__(self.message)
