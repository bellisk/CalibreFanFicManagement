#!/bin/bash

NEW_COOKIE="$(python3 get_ao3_cookie.py)"
echo "$NEW_COOKIE"

NEW_COOKIE="${NEW_COOKIE//%/%%}"
echo "$NEW_COOKIE"

