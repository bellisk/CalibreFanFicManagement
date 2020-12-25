# CalibreFanFicManagement
A commandline utility to fill my own needs for managing fanfic on Calibre.

## Resources
- [Calibre CLI](https://manual.calibre-ebook.com/generated/en/cli-index.html)
- [FanFicFare](https://github.com/JimmXinu/FanFicFare)
- Unofficial [ao3 client](https://github.com/ladyofthelog/ao3.git)
- [AutomatedFanFic](https://github.com/MrTyton/AutomatedFanfic) as example code

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

## Todo
- set up basic script
- log in to AO3
- get my bookmarks
- distinguish between series and story bookmarks
- check whether each story is in my library
- if not, or if yes and should be updated, import (using FFF/Calibre cli)
