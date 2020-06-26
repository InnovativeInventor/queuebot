# -*- coding: utf-8 -*-
# credit: modified from socialbot's irc.py
# https://github.com/Ghostofapacket/socialscrape-bot/blob/master/irc.py

import socket
import datetime
import re
import sys
import time
import logger

import settings
import queuebot
import threading


class IRC(threading.Thread):
    def __init__(self, bot=queuebot.QueueBot):
        threading.Thread.__init__(self)
        self.channel_bot = settings.irc_channel_bot
        self.nick = settings.irc_nick
        self.server_name = settings.irc_server_name
        self.server_port = settings.irc_server_port
        self.server = None
        self.scrapesite = None
        self.messages_received = []
        self.messages_sent = []
        self.commands_received = []
        self.commands_sent = []

        self.logger = logger.Logger

        self.state = False

        self.start_pinger()
        self.bot = bot()

    def start_pinger(self):
        self.pinger = threading.Thread(target=self.pinger)
        self.pinger.daemon = True
        self.pinger.start()

    def pinger(self):
        while True:
            self.logger.log_info("ping")
            time.sleep(30)

            if self.state:
                msg = self.bot.poll()
                if msg:
                    self.send(string=msg, channel=settings.irc_channel_bot)

            time.sleep(30)
            self.send("PING", ":")

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
        self.send(
            "USER",
            "{nick} {nick} {nick} :I am a bot; "
            "https://github.com/InnovativeInventor/queuebot.".format(nick=self.nick),
        )
        self.send("NICK", "{nick}".format(nick=self.nick))
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
                self.messages_sent.append(message)
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
                self.messages_received.append(message)
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
                            self.commands_received.append(
                                {"command": command, "user": user, "channel": channel}
                            )
                            self.command(command, user, channel)
                            logger.Logger.log_info(
                                "COMMAND - Received in channel {channel} - {command}".format(
                                    channel=channel, command=" ".join(command)
                                )
                            )

                            # Command poll
                            msg = self.bot.poll(command)
                            if msg:
                                self.send(string=msg, channel=settings.irc_channel_bot)

                        elif command[1] == "stop":
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
        if str(user).rstrip() in ["maxfan8", "Major"]:
            return True
        else:
            return False

    def command(self, command, user, channel):
        logger.Logger.log_info("command" + str(command))
        if command[1] == "help":
            self.send(
                "PRIVMSG",
                "{user}: Source code is at https://github.com/InnovativeInventor/queuebot. Anybody can tell me to halt if things get out of hand.",
                channel,
            )
            logger.Logger.log_info("Gave help")
        elif command[1] == "stop":
            logger.Logger.log_info(
                "EMERGENCY: {user} has requested I stop".format(**locals())
            )
            self.state = False
            self.send("PRIVMSG", "{user}: Stopped.".format(**locals()), channel)
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
            self.state = True
            logger.Logger.log_info("Server started.")
            self.send(
                "PRIVMSG", "{user}: Server started.".format(user=user), channel,
            )


if __name__ == "__main__":
    bot = IRC()
    bot.run()
