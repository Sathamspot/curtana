# This Source Code Form is subject to the terms of the Mozilla Public
# License, v. 2.0. If a copy of the MPL was not distributed with this
# file, You can obtain one at http://mozilla.org/MPL/2.0/.

import re
import math
import os
import subprocess
import time
from telethon import events
from markdown import markdown
from production import Config
from jinja2 import Environment, FileSystemLoader
from datetime import date
from telethon.tl.functions.messages import GetPeerDialogsRequest


ENV = bool(os.environ.get("ENV", False))
if ENV:
    from production import Config
else:
    if os.path.exists("development.py"):
        from development import Config


def register(pattern=None, allow_sudo=False, incoming=False, func=None, **args):
    """
    Simpler function to handle events without having to import telethon.events
    also enables command_handler functionality
    """
    args["func"] = lambda e: e.via_bot_id is None
    if func is not None:
        args["func"] = func
    if pattern is not None:
        args["pattern"] = re.compile(Config.COMMAND_HANDLER + pattern)
    if allow_sudo:
        args["from_users"] = list(Config.SUDO_USERS)
    if incoming:
        args["incoming"] = True
    else:
        args["outgoing"] = True
    args["blacklist_chats"] = True
    black_list_chats = list(Config.BLACK_LIST)
    if len(black_list_chats) > 0:
        args["chats"] = black_list_chats
    return events.NewMessage(**args)


async def is_read(userbot, entity, message, is_out=None):
    """
    Returns True if the given message (or id) has been read
    if a id is given, is_out needs to be a bool
    """
    is_out = getattr(message, "out", is_out)
    if not isinstance(is_out, bool):
        raise ValueError(
            "Message was id but is_out not provided or not a bool")
    message_id = getattr(message, "id", message)
    if not isinstance(message_id, int):
        raise ValueError("Failed to extract id from message")

    dialog = (await userbot(GetPeerDialogsRequest([entity]))).dialogs[0]
    max_id = dialog.read_outbox_max_id if is_out else dialog.read_inbox_max_id
    return message_id <= max_id


async def progress(current, total, event, start, type_of_ps):
    """Generic progress_callback for both
    uploads and downloads"""
    now = time.time()
    diff = now - start
    if round(diff % 10.00) == 0 or current == total:
        percentage = current * 100 / total
        speed = current / diff
        elapsed_time = round(diff) * 1000
        time_to_completion = round((total - current) / speed) * 1000
        estimated_total_time = elapsed_time + time_to_completion
        progress_str = "[{0}{1}]\nPercent: {2}%\n".format(
            ''.join(["█" for i in range(math.floor(percentage / 5))]),
            ''.join(["░" for i in range(20 - math.floor(percentage / 5))]),
            round(percentage, 2))
        tmp = progress_str + \
            "{0} of {1}\nETA: {2}".format(
                humanbytes(current),
                humanbytes(total),
                time_formatter(estimated_total_time)
            )
        await event.edit("{}\n {}".format(
            type_of_ps,
            tmp
        ))


def humanbytes(size):
    """Input size in bytes,
    outputs in a human readable format"""
    # https://stackoverflow.com/a/49361727/4723940
    if not size:
        return ""
    # 2 ** 10 = 1024
    power = 2 ** 10
    raised_to_pow = 0
    dict_power_n = {
        0: "",
        1: "Ki",
        2: "Mi",
        3: "Gi",
        4: "Ti"
    }
    while size > power:
        size /= power
        raised_to_pow += 1
    return str(round(size, 2)) + " " + dict_power_n[raised_to_pow] + "B"


def time_formatter(milliseconds: int) -> str:
    """Input time in milliseconds, to get beautified time,
    as string"""
    seconds, milliseconds = divmod(int(milliseconds), 1000)
    minutes, seconds = divmod(seconds, 60)
    hours, minutes = divmod(minutes, 60)
    days, hours = divmod(hours, 24)
    tmp = ((str(days) + "d, ") if days else "") + \
        ((str(hours) + "h, ") if hours else "") + \
        ((str(minutes) + "m, ") if minutes else "") + \
        ((str(seconds) + "s, ") if seconds else "") + \
        ((str(milliseconds) + "ms, ") if milliseconds else "")
    return tmp[:-2]


class Utils():
    today = date.today().strftime("%B %d, %Y")
    data = {}

    def __init__(self, logger):
        self.logger = logger

    def deploy(self):
        self.logger.info(f"Deploying {Config.SUBDOMAIN}.surge.sh..")
        output = subprocess.check_output(
            f"surge surge https://{Config.SUBDOMAIN}.surge.sh", shell=True)
        if "Success!" in str(output):
            self.logger.info(
                f"{Config.SUBDOMAIN}.surge.sh deployed sucessfully.")
        else:
            self.logger.info(
                f"Failed to deploy {Config.SUBDOMAIN}.surge.sh " + "\nError: " + str(output))

    def parse_text(self, text):
        # We only want to parse links
        changes = {"**": "", "__": "", "\n": "\n<br>"}
        for a, b in changes.items():
            text = text.replace(a, b)
        text = markdown(text)
        return text

    def parse_data(self):
        data = self.data
        roms = []
        kernels = []
        recoveries = []
        for value in data.values():
            head = f"{value.split()[0][1:]}"
            if "#ROM" in value:
                roms.append(head)
            if "#Kernel" in value:
                kernels.append(head)
            if "#Recovery" in value:
                recoveries.append(head)
        return [roms, kernels, recoveries]

    def save(self, webpage="index", **kwargs):
        path = f"surge/{webpage}/index.html"
        if webpage == "index":
            path = "surge/index.html"
            jinja2_template = str(open(path, "r").read())
        else:
            data = self.data
            text = self.parse_text(data[webpage])
            self.logger.info(text)
            img = f"<img src=https://curtana.surge.sh/{webpage}/thumbnail.png height='225'>"
            head = f"{text.split()[0]}"
            jinja2_template = "{%extends 'base.html'%}\n{%block title%}\n"\
                + webpage + "\n{%endblock%}\n{%block body%}\n<div class='jumbotron'>"\
                + img + "\n<p class='display-4'>\n<hr>\n"\
                + head + "\n</p>\n"\
                + "<p class='lead'>\n\n"\
                + text[len(head):] + "\n</p>\n<hr>\n</div>\n{%endblock%}"
        template_object = Environment(
            loader=FileSystemLoader("surge")).from_string(jinja2_template)
        static_template = template_object.render(**kwargs)
        with open(path, "w") as f:
            f.write(static_template)

    def refresh(self):
        data = self.parse_data()
        latest = [data[0][0], data[1][0], data[2][0]]
        self.save(roms=sorted(data[0]), kernels=sorted(
            data[1]), recoveries=sorted(data[2]), latest=latest, today=self.today)
