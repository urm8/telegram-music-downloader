#!/usr/bin/env python
import traceback
import downloader  # our module to download audio
import helpers
import os
import sys
import time


from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    CallbackQueryHandler,
)
from telegram.ext.dispatcher import run_async
from telegram import InlineKeyboardMarkup, InlineKeyboardButton

import logging

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

print("hi")
TOKEN = os.environ["YOUTUBE_TELEGRAM_BOT_TOKEN"]
print(f"running with token: {TOKEN}")

dwn_msg = "/d youtube_video_url to download audio."
srch_msg = "/s text to search for audio."

usage_msg = "Use: \n%s \n%s" % (dwn_msg, srch_msg)

start_msg = "Hi %s! %s"

dwn_msg = "Your song is downloading, please wait..."


@run_async
def download(update, _):
    try:
        if not update.effective_message.text.startswith("/d "):
            return
        text = update.effective_message.text
        update.message = update.effective_message
        print(f"start downloading: {text}")

        if not helpers.check(text):
            bot_msg = _.bot.send_message(chat_id=update.message.chat_id, text=usage_msg)
            time.sleep(5)
            _.bot.delete_message(
                chat_id=update.message.chat_id, message_id=bot_msg.message_id
            )
        else:
            sent_msg = _.bot.send_message(chat_id=update.message.chat_id, text=dwn_msg)
            url = helpers.get_url(text)
            vId = helpers.get_vId(url)
            sys.stdout.write(
                "New song request client username %s\n" % update.message.chat.username
            )
            audio_info = downloader.download_audio(vId, url)
            _.bot.delete_message(
                chat_id=update.message.chat_id, message_id=sent_msg.message_id
            )

            try:
                _.bot.delete_message(
                    chat_id=update.message.chat_id, message_id=update.message.message_id
                )
            except:
                pass

            if not audio_info["status"]:
                msg = "Something went wrong: %s" % audio_info["error"]
                return _.bot.send_message(chat_id=update.message.chat_id, text=msg)

            audio = open(audio_info["path"], "rb")
            _.bot.send_audio(
                chat_id=update.message.chat_id,
                audio=audio,
                duration=audio_info["duration"],
                title=audio_info["title"],
                timeout=999,
            )
            try:
                _.bot.delete_message(
                    chat_id=update.message.chat_id, message_id=update.message.message_id
                )
            except Exception:
                traceback.print_exc()
    except Exception:
        traceback.print_exc()


@run_async
def search(update, _):
    try:
        text = update.message.text
        query = helpers.get_query(text)
        if not query:
            msg = "Use: %s" % srch_msg
            return _.bot.send_message(
                chat_id=update.callback_query.message.chat_id, text=msg
            )

        results = helpers.search_songs(query)
        text = ""
        for res in results:
            text += "%s - %s\n" % (res["title"], helpers.youtube_url % res["url"])

        button_list = list(
            map(
                lambda x: InlineKeyboardButton(x["title"], callback_data=x["url"]),
                results,
            )
        )
        reply_markup = InlineKeyboardMarkup(helpers.build_menu(button_list, n_cols=3))
        _.bot.send_message(
            chat_id=update.message.chat_id, text=text, reply_markup=reply_markup
        )
    except:
        pass


@run_async
def button(update, _):
    try:
        data = update.callback_query.data
        update.callback_query.data = "/d %s" % (helpers.youtube_url % data)
        download(_.bot, update)
    except:
        pass


@run_async
def echo(update, _):
    try:
        bot_msg = _.bot.send_message(chat_id=update.message.chat_id, text=usage_msg)
        time.sleep(20)
        _.bot.delete_message(
            chat_id=update.message.chat_id, message_id=bot_msg.message_id
        )
    except:
        pass


@run_async
def start(update, _):
    try:
        msg = start_msg % (update.message.chat.first_name, usage_msg)
        _.bot.send_message(chat_id=update.message.chat_id, text=msg)
    except:
        pass


download_handler = MessageHandler(Filters.command, download)
search_handler = CommandHandler("s", search)
start_handler = CommandHandler("start", start)

if __name__ == "__main__":
    updater = Updater(token=TOKEN)
    print("setting up dispatcher...")
    dispatcher = updater.dispatcher
    dispatcher.add_handler(download_handler)
    print("start polling...")
    updater.start_polling()
    updater.idle()
    print("Bot started...")
