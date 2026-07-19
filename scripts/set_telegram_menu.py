import urllib.request
import urllib.error
import json

TOKEN = "8915165344:AAFBy28wo3cNUvvVZX03Pv1qzckLmDw7I1g"
url = f"https://api.telegram.org/bot{TOKEN}/setMyCommands"

commands = {
    "commands": [
        {"command": "start", "description": "Start the bot and get info"},
        {"command": "status", "description": "View system and generation status"},
        {"command": "start_trading", "description": "Wake the agent up"},
        {"command": "stop_trading", "description": "Put the agent to sleep"},
        {"command": "spawn", "description": "Spawn a new generation"},
        {"command": "kill", "description": "Terminate current generation"},
        {"command": "report", "description": "Generate performance report"},
        {"command": "memory", "description": "View recent trade memories"},
        {"command": "mode", "description": "Switch mode [paper|live]"},
        {"command": "help", "description": "List all commands"}
    ]
}

data = json.dumps(commands).encode('utf-8')
req = urllib.request.Request(url, data=data, headers={'Content-Type': 'application/json'})

import ssl
ctx = ssl.create_default_context()
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE

try:
    with urllib.request.urlopen(req, context=ctx, timeout=30) as response:
        result = json.loads(response.read().decode())
        print(result)
except urllib.error.URLError as e:
    print(f"Error: {e}")
