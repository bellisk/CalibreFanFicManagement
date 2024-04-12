import browser_cookie3

cj = browser_cookie3.load(domain_name='archiveofourown.org')
for c in cj:
    if c.name == "_otwarchive_session":
        print(c.value)
