import os

# variables to be changed
version = "0.1.1"
irc_channel_bot = "#test"
irc_nick = "queuebot"
irc_server_name = "irc.servercentral.net"
irc_server_port = 6667
db_uri = os.environ.get("DATABASE_URI")
db_name = os.environ.get("DB_NAME")

if not db_uri:
    raise ValueError("DB env var not found")
