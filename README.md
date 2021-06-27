# CalibreFanFicManagement
A commandline utility to fill my own needs for managing fanfic on Calibre.

Currently, there is one command, `download`, which is adapted from 
[AutomatedFanFic](https://github.com/MrTyton/AutomatedFanfic). It will scrape
bookmarks from a user's AO3 account, download the works as epub files and add
them to a calibre library.

Planned:
- mass editing of calibre tags for fanfics
- deduplicating AO3 bookmarks in cases where I have both a series and individual
  works bookmarked
- statistics about bookmarked/downloaded fics
- import from page with list of urls, e.g. collection or author page
- import all works from author
- import all works from your subscriptions

## Usage
If you want to save bookmarks in a calibre library, you will need to install the
[calibre CLI](https://manual.calibre-ebook.com/generated/en/cli-index.html).

- Clone this repository and `cd` into the `CalibreFanFicManagement` directory
- `pip install -r requirements.txt`
- If needed, copy `config_template.ini` to `config.ini` and fill in
- Copy [FanFicFare example config](https://github.com/JimmXinu/FanFicFare/blob/master/fanficfare/example.ini)
  to `personal.ini` and fill in necessary fields
- `python fanficmanagement.py download -C config.ini`
- For help: `python fanficmanagement.py -h`

## Resources
- [Calibre CLI](https://manual.calibre-ebook.com/generated/en/cli-index.html)
- [FanFicFare](https://github.com/JimmXinu/FanFicFare)
- Unofficial [ao3 client](https://github.com/ladyofthelog/ao3.git)
  and [my fork](https://github.com/bellisk/ao3) with custom changes
- [AutomatedFanFic](https://github.com/MrTyton/AutomatedFanfic)

## Requirements
I want to:

- import fics from my AO3 bookmarks into Calibre
- convert AO3 tags into Calibre tags by appending 'ao3.' to them, e.g.
```
`Hurt/Comfort` -> `ao3.Hurt/Comfort`
```
- see a progress bar while importing
- do the tag conversion both while importing and as a batch operation on
  existing fanfics in Calibre
- get aggregate metadata about fics in my Calibre library, e.g.
```
100 stories and 100,000 total words in fandom Vampire Chronicles
```
- find out whether I have bookmarks for stories that are part of a series that
  is also bookmarked
