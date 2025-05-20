from datetime import datetime
from unittest.mock import MagicMock

from ao3 import AO3, Collection, Series, User


class MockUser(User):
    def bookmarks_ids(
        self,
        max_count=None,
        expand_series=False,
        oldest_date=None,
        sort_by_updated=False,
    ):
        ids = ["1", "2", "3", "4", "5"]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def gift_ids(self, max_count=None, oldest_date=None):
        ids = ["1", "2", "3", "4", "5"]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def marked_for_later_ids(self, max_count=None, oldest_date=None):
        ids = ["1", "2", "3", "4", "5"]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def works_count(self):
        return int(self.username[-1]) * 10

    def work_ids(self, max_count=0, oldest_date=None):
        ids = [
            self.username[-1] + "1",
            self.username[-1] + "2",
            self.username[-1] + "3",
            self.username[-1] + "4",
            self.username[-1] + "5",
        ]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def work_subscription_ids(self, max_count=None):
        ids = ["1", "2", "3", "4", "5"]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def series_subscription_ids(self, max_count=None):
        ids = ["1", "2", "3", "4", "5"]

        if max_count:
            return ids[:max_count]
        else:
            return ids

    def user_subscription_ids(self, max_count=None):
        return ["user1", "user2", "user3"]


class MockSeries(Series):
    def work_ids(self, max_count=0, oldest_date=None):
        return [self.id + str(n) for n in range(int(self.id))]

    def info(self):
        return {
            "Title": "Series " + self.id,
            "Works": self.id,
        }


class MockCollection(Collection):
    def work_ids(self, max_count=0, oldest_date=None):
        return ["1", "2", "3"]


class MockAO3(AO3):
    def login(self, username, cookie):
        self.user = MockUser(username, self.session, self.ao3_url)

    def work(self, id):
        work_published_date = {
            "1": "2021-01-01",
            "2": "2022-01-01",
            "3": "2023-01-01",
            "4": "2024-01-01",
            "5": "2025-01-01",
        }[id]

        mock_work = MagicMock(url="https://archiveofourown.org/works/" + id)
        mock_work.completed = datetime.strptime(work_published_date, "%Y-%m-%d").date()

        return mock_work

    def author(self, username):
        return MockUser(username, self.session, self.ao3_url)

    def series(self, id):
        return MockSeries(id, self.session, self.ao3_url)

    def collection(self, id):
        return MockCollection(id, self.session, self.ao3_url)
