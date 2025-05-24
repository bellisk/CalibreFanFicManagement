from random import randint

from src.calibre import CalibreHelper


class MockCalibreHelper(CalibreHelper):
    def check_library(self):
        pass

    def search(
        self, authors=None, urls=None, series=None, book_formats=None, incomplete=False
    ):
        if authors:
            return [str(i) for i in range(10)]
        elif series:
            return [str(i) for i in range(2)]

    def list_titles_and_urls(
        self, authors=None, urls=None, series=None, book_formats=None, incomplete=False
    ):
        if authors:
            result = [
                {
                    "title": "test_title",
                    "url": f"https://archiveofourown.org/works/"
                    f"{randint(100, 100000)}",
                }
                for i in range(10)
            ]
            return result

        elif series:
            return [
                {
                    "title": "test_title",
                    "url": f"https://archiveofourown.org/works/{series[0][-1]}{i}",
                }
                for i in range(2)
            ]
