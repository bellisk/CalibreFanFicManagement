import browser_cookie3

cj = browser_cookie3.firefox(domain_name="archiveofourown.gay")
for c in cj:
    if c.name == "_otwarchive_session":
        print(c.value)
