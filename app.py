# For curtana.surge.sh
# By Priyam Kalra

import os
import sys
from asyncio import sleep


async def is_auth(event):
    chat = await event.get_chat()
    if f"@{chat}" in Config.CHATS:
        return True
    return False


def required(text):
    return True if "#ROM" in text else (True if "#Port" in text else (True if "#Kernel" in text else (True if "#Recovery" in text else False)))


@client.on(register(outgoing=True, func=is_auth))
async def manual(event):
    logger.info("Starting jobs for manual update.")
    await deploy(event)


@client.on(register(incoming=True, func=is_auth))
async def automatic(event):
    logger.info("Starting jobs for automatic update.")
    await deploy(event)


async def deploy(event):
    """
    Parses the data, and then deploys it to surge.sh
    """
    messages = []
    util.data = {}
    thumbnails = []
    util = utils(logger)
    chats = Config.CHATS
    logger.info(util.today + " -- its update day!")
    logger.info("Updates chat(s): " + str(chats))
    logger.info("Starting update..")
    for chat in chats:
        async for message in client.iter_messages(chat):
            messages.append(message)
    for message in messages:
        text = message.text if message.text is not None else ""
        if not required(text):
            continue
        head = f"{text.split()[0][1:]}"
        if head in Config.BLOCKED_UPDATES:
            continue
        with open("surge/index.html", "r") as index:
            with open("index.bak", "w") as backup:
                backup.write(index.read())
        if head.lower() not in str(util.data.keys()).lower():
            util.data.update({head: text})
            image = await client.download_media(message, f"surge/{head}/")
            thumbnail = f"surge/{head}/thumbnail.png"
            os.rename(image, thumbnail)
            thumbnails.append(thumbnail)
            util.save(head)
    util.refresh()
    logger.info("Update completed.")
    sleep(1)
    util.deploy()
    sleep(1)
    logger.info("Cleaning up leftover files..")
    for file in thumbnails:
        os.remove(file)
    os.remove("surge/index.html")
    os.rename("index.bak", "surge/index.html")
    logger.info("Cleaned up all leftover files.")
    sleep(1)
    logger.info("All jobs executed, idling..")
