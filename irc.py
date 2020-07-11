# -*- coding: utf-8 -*-
# credit: modified from socialbot's irc.py
# https://github.com/Ghostofapacket/socialscrape-bot/blob/master/irc.py

import datetime
import re
import socket
import sys
import threading
import time

import logger
import mongoset
import queuebot
import settings


class IRC(threading.Thread):
    def __init__(self, bot=queuebot.QueueBot):
        threading.Thread.__init__(self)
        self.channel_bot = settings.irc_channel_bot
        self.nick = settings.irc_nick
        self.server_name = settings.irc_server_name
        self.server_port = settings.irc_server_port
        self.server = None
        self.scrapesite = None
        self.logger = logger.Logger

        self.state = False

        self.start_pinger()
        self.bot = bot()


        if settings.db_name:
            self.messages = mongoset.connect(uri=settings.db_uri, db_name=settings.db_name)["messages"]
            self.commands = mongoset.connect(uri=settings.db_uri, db_name=settings.db_name)["commands"]
        else:
            self.messages = mongoset.connect(uri=settings.db_uri)["messages"]
            self.commands = mongoset.connect(uri=settings.db_uri)["commands"]

    def start_pinger(self):
        self.pinger = threading.Thread(target=self.pinger)
        self.pinger.daemon = True
        self.pinger.start()

    def pinger(self):
        while True:
            self.send("PING", ":")
            for i in range(24):
                time.sleep(5)
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
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.connect((self.server_name, self.server_port))
        time.sleep(0.5)
        self.send(
            "USER",
            "{nick} {nick} {nick} :I am a bot; "
            "https://github.com/InnovativeInventor/queuebot.".format(nick=self.nick),
        )
        time.sleep(0.5)
        self.send("NICK", "{nick}".format(nick=self.nick))
        time.sleep(0.5)
        self.send("JOIN", "{channel_bot}".format(channel_bot=self.channel_bot))
        #        self.send('PRIVMSG', 'Version {version}.'
        #                  .format(version=settings.version), self.channel_bot)
        logger.Logger.log_info("Connected to " + self.server_name + " as " + self.nick)

    def send(self, command="PRIVMSG", string="", channel=""):
        if string:
            if channel != "":
                channel += " :"
            message = "{command} {channel}{string}".format(**locals())
            try:
                logger.Logger.log_info("IRC - {message}".format(**locals()))
                self.messages.insert({"msg":message, "sent": True})
                self.server.send("{message}\n".format(**locals()).encode("utf-8"))
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
            while True:
                if self.state:
                    msg = self.bot.poll()
                    if msg:
                        self.send(string=msg, channel=settings.irc_channel_bot)

                message = self.server.recv(4096).decode("utf-8")
                self.messages.insert({"msg": message, "sent": False})
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
                            self.commands.insert(
                                {"command": command, "user": user, "channel": channel}
                            )
                            self.command(command, user, channel)
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

                        elif (command[1] == "stop" or command[1] == "help") and command[
                            0
                        ].replace(":", "") == settings.irc_nick:
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
            self.state = True
            self.bot.state = True
            msg = self.bot.poll(restore=True)
            if msg:
                self.send(string=msg, channel=settings.irc_channel_bot)


if __name__ == "__main__":
    bot = IRC()
    bot.run()
