import browser_cookie3

cj = []
for browser in browser_cookie3.all_browsers:
    try:
        cj = browser(domain_name="archiveofourown.gay")
        if len(cj) > 0:
            break
    except browser_cookie3.BrowserCookieError:
        # Browser is not installed
        continue
    except TypeError:
        # Known bug in browser_cookie3 for Arc browser
        continue

for c in cj:
    if c.name == "_otwarchive_session":
        print(c.value)
