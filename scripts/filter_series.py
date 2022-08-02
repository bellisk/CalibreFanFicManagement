import json

with open("books_in_series.json") as f:
    books_in_series = json.loads(f.read())

series = {}
for book in books_in_series:
    if book["series"] not in series.keys():
        series[book["series"]] = [book["series_index"]]
    else:
        series[book["series"]].append(book["series_index"])

print(series)
# print(len(series))

for title, indices in series.items():
    if 1.0 not in indices:
        print(title)
        print(indices)
