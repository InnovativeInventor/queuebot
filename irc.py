# -*- coding: utf-8 -*-
# credit: modified from socialbot's irc.py
# https://github.com/Ghostofapacket/socialscrape-bot/blob/master/irc.py

import datetime
import re
import socket
import ssl
import sys
import threading
import time

import logger
# import mongoset
import queuebot
import settings


class IRC(threading.Thread):
    def __init__(self, bot=queuebot.QueueBot):
        threading.Thread.__init__(self)
        self.channel_bot = settings.irc_channel_bot
        self.context = ssl.SSLContext(ssl.PROTOCOL_TLS)
        # ssl.SSLContext.verify_mode = ssl.CERT_NONE
        self.nick = settings.irc_nick
        self.server_name = settings.irc_server_name
        self.server_port = settings.irc_server_port
        self.server = None
        self.scrapesite = None
        self.logger = logger.Logger

        self.state = False

        self.start_pinger()
        self.bot = bot()

        # if settings.db_name:
            # self.messages = mongoset.connect(
            #     uri=settings.db_uri, db_name=settings.db_name
            # )["messages"]
            # self.commands = mongoset.connect(
            #     uri=settings.db_uri, db_name=settings.db_name
            # )["commands"]
        # else:
        #     self.messages = mongoset.connect(uri=settings.db_uri)["messages"]
        #     self.commands = mongoset.connect(uri=settings.db_uri)["commands"]

    def start_pinger(self):
        self.pinger = threading.Thread(target=self.pinger)
        self.pinger.daemon = True
        self.pinger.start()

    def pinger(self):
        while True:
            self.send("PING", ":")
            for i in range(30):
                time.sleep(7)
                if self.state:
                    msg = self.bot.poll()
                    if msg:
                        self.send(string=msg, channel=settings.irc_channel_bot)

    def run(self):
        self.connect()
        self.poll()

    def connect(self):
        if self.server:
            self.server.close()
        logger.Logger.log_info("Connecting to IRC server " + self.server_name)
        self.server = self.context.wrap_socket(socket.socket(socket.AF_INET, socket.SOCK_STREAM), server_hostname = self.server_name)
        self.server.connect((self.server_name, self.server_port))
        time.sleep(1)
        self.send(
            "USER",
            "{nick} {nick} {nick} :I am a bot; "
            "https://github.com/InnovativeInventor/queuebot.".format(nick=self.nick),
        )
        # time.sleep(1)
        self.send("NICK", "{nick}".format(nick=self.nick))
        time.sleep(1)
        self.identify()
        #        self.send('PRIVMSG', 'Version {version}.'
        #                  .format(version=settings.version), self.channel_bot)
        logger.Logger.log_info("Connected to " + self.server_name + " as " + self.nick)

    def identify(self):
        self.send(string=f"identify {settings.irc_password}", channel="NickServ")

    def send(self, command="PRIVMSG", string="", channel=""):
        if string:
            if channel != "":
                channel += " :"
            message = str(f"{command} {channel}{string}")
            try:
                logger.Logger.log_info("IRC - {message}".format(**locals()))
                # self.messages.insert({"msg": message, "sent": True})
                self.server.send(f"{message}\r\n".encode("utf-8"))
            except Exception as exception:
                logger.Logger.log_info("{exception}".format(**locals()), "WARNING")
                # self.connect()
                # self.server.send('{message}\n'.format(**locals()))
        else:
            logger.Logger.log_info(
                "Failed message " + str(command) + " " + str(channel)
            )

    def poll(self):
        try:
            prev_messages = []
            while True:
                messages = self.server.recv(4096).decode("utf-8")
                prev_messages.extend(messages.split("\r\n"))
                current_messages = prev_messages

                for message in current_messages[:-1]:
                    del prev_messages[0]
                    # self.messages.insert({"msg": message, "sent": False})
                    if message.strip().startswith("PING"):
                        logger.Logger.log_info('Received ping msg: ' + message.rstrip())
                        message_new = message.split()[-1]
                        self.send('PONG', '{message_new}'.format(**locals()))
                    # elif "join" in message.rstrip():
                    #     logger.Logger.log_info("Recieved authentication message")
                    elif "You have not registered" in message:
                        self.identify()
                        self.send("JOIN", "{channel_bot}".format(channel_bot=self.channel_bot))

                    if self.state:
                        msg = self.bot.poll()
                        if msg:
                            self.send(string=msg, channel=settings.irc_channel_bot)

                    for line in message.splitlines():
                        logger.Logger.log_info("IRC - {line}".format(**locals()))
                        if len(line.split()) > 4:
                            command = line.split()[3:]
                            user = line.split("!")[0].replace(":", "")
                            msg_type = line.split()[1]
                            channel = line.split()[2]

                            if (
                                self.check_admin(user)
                                and command[0].replace(":", "") == settings.irc_nick
                            ):
                                # self.commands.insert(
                                #     {"command": command, "user": user, "channel": channel}
                                # )
                                # self.command(command, user, channel)
                                logger.Logger.log_info(
                                    "COMMAND - Received in channel {channel} - {command}".format(
                                        channel=channel, command=" ".join(command)
                                    )
                                )

                                # Command poll
                                if self.state:
                                    msg = self.bot.poll(command)
                                    if msg:
                                        self.send(
                                            string=msg, channel=settings.irc_channel_bot
                                        )

                            if (command[1] == "stop" or command[1] == "help" or command[1] == "start") and command[
                                0
                            ].replace(":", "") == settings.irc_nick:
                                logger.Logger.log_info("Command detected")
                                self.command(command, user, channel)

                if self.state:
                    msg = self.bot.poll()
                    if msg:
                        self.send(string=msg, channel=settings.irc_channel_bot)
        except KeyboardInterrupt:
            logger.Logger.log_info("Caught KeyboardInterrupt. Closing connection")
            self.send(
                string="queuebot is shutting down due to a KeyboardInterrupt. Not a crash!",
                channel=settings.irc_channel_bot,
            )
            sys.exit()

    def check_admin(self, user):
        logger.Logger.log_info("User authenticated " + str(user))
        if str(user).rstrip() in [
            "maxfan8",
            "Major",
            "kiska",
            "Larsenv",
            "JAA",
            "Ryz",
            "katocala",
            "Kaz",
            "SketchCow",
            "arkiver",
            "jodizzle",
            "VoynichCr",
        ]:
            return True
        else:
            return False

    def command(self, command, user, channel):
        logger.Logger.log_info("command" + str(command))
        if command[1] == "help":
            self.send(
                "PRIVMSG",
                "{user}: Source code is at https://github.com/InnovativeInventor/queuebot. Anybody can tell me to stop if things get out of hand. Currently the state of the bot is {state}, where True means that I'm running. The number of slots that I am allotted is {slot_size}.".format(
                    user=user, state=self.state, slot_size=self.bot.size
                ),
                channel,
            )
            logger.Logger.log_info("Gave help")
        elif command[1] == "stop":
            logger.Logger.log_info(
                "EMERGENCY: {user} has requested I stop".format(user=user)
            )
            msg = self.bot.poll(restore=True, command=["queuebot","status"])
            if msg:
                self.send(string=msg, channel=settings.irc_channel_bot)

            self.bot.save()
            self.bot.state = False
            self.state = False
            self.send("PRIVMSG", "{user}: Stopped queuebot.".format(user=user), channel)
            logger.Logger.log_info("Stopped")
        elif command[1] == "version":
            self.send(
                "PRIVMSG",
                "{user}: Version is {version}.".format(
                    user=user, version=settings.version
                ),
                channel,
            )
            logger.Logger.log_info("Gave version")
        elif command[1] == "start":
            logger.Logger.log_info("Server started.")
            self.send(
                "PRIVMSG",
                "{user}: queuebot started. Anything that was previously running should be restored.".format(
                    user=user
                ),
                channel,
            )
            self.bot.size = 1
            self.state = True
            self.bot.state = True

            msg = self.bot.poll(restore=True, command=["queuebot","status"])
            if msg:
                self.send(string=msg, channel=settings.irc_channel_bot)


if __name__ == "__main__":
    bot = IRC()
    bot.run()
