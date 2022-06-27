#!/usr/bin/python
#
# A utility that logs into the battle game and saves your refresh/access token to a file.
import json
from distutils.util import strtobool

from battle_client.client import BattleClient

client = BattleClient(expect_keys=False)

print('go into the battle game, put in your email address, and hit send code')
print('you need to enter the exact same email (case sensitive) below')
print()
user_email = input('Input email: ')

print('if you want to request a login code, type y')
print('if you already have a login code, type anything else')
print()
fetch_code = input('Request code? (y/n): ')
if strtobool(fetch_code):
    resp = client.get_login_code(user_email)
    print(resp)

print()
print('you should have or get an email with a 6 digit code. enter that here')
print()
user_code = input('Input code: ')

if '@' not in user_email:
    print('Does not look like an email:', user_email)
    exit(-1)

if len(user_code) != 6:
    print('expected a six digit code:', user_code)
    exit(-1)

if not user_code.isdigit():
    print('expected only numbers in the code code:', user_code)
    exit(-1)

result = client.login(user_email, user_code)
output = {
    'access_token': result.access_token,
    'refresh_token': result.refresh_token,
}

with open('battle_keys.json', 'w') as f:
    json.dump(output, f, sort_keys=True, indent=2)

print('Done writing battle_keys.json')
