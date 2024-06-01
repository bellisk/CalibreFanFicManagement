#!/bin/bash

readonly SERVER=$1
readonly CONFIG_PATH="$2"

cd "${BASH_SOURCE%/*}" || exit

NEW_COOKIE="$(python3 get_ao3_cookie.py)"
NEW_COOKIE="${NEW_COOKIE//%/%%}"

if [ -n "$NEW_COOKIE" ]; then
  echo "Got AO3 cookie from browser"

  ssh "$SERVER" "sed -i -e 's/^cookie=.*/cookie=${NEW_COOKIE}/' $CONFIG_PATH"

  echo "Updated AO3 cookie in config on server"
else
  echo "Couldn't find an AO3 cookie from the browser: you need to log in first"
fi
