#!/usr/bin/env python

import logging
import ujson

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import Updater, MessageHandler, CommandHandler, CallbackQueryHandler, Filters, CallbackContext

from datetime import time
from tinydb import TinyDB, Query

from texts import start_text, help_text, questions


configfile = "config.json"
dbfile = "db.json"


db = TinyDB(dbfile)
config = ujson.load(open(configfile, "r"))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def start(update, context) -> None:
    """Sends a message with inline buttons attached."""
    update.message.reply_text(start_text)
    keyboard = [
        [InlineKeyboardButton(f"{i}) {question}", callback_data=str(i))] for i, question in enumerate(questions)
    ]

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text("Type on the question you would like to answer", reply_markup=reply_markup)


def button(update, context) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    # create entry in db if chat_instance does not exist yet
    # we also store the current question a user is on, as we need to know it for when the bot receives
    # an ordinary message (aka an answer to a question). When collecting the data, this information is omitted
    if (db.search(Query().chat_id == query.message.chat.id) == []):
        db.insert({'chat_id': query.message.chat.id,
                   'question': '0',
                   })
    # else:
    #     print(f"user {query.chat_instance} already in database")

    db.update({'question': query.data}, Query().chat_id == query.message.chat.id)
    query.message.reply_text(f"You're currently editing your reply to question {query.data}")


def help_command(update, context) -> None:
    update.message.reply_text(help_text)


def mhandler(update, context):
    message = update.message

    reply = db.search(Query().chat_id == message.chat_id)[0].get('question')
    message.reply_text(f"Your answer to question {reply} has been updated to:\n{message.text}")
    db.update({f'{reply}': message.text}, Query().chat_id == message.chat.id)


if __name__ == '__main__':
    updater = Updater(config['token'])

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, mhandler))

    # start_polling() is non-blocking and will stop the bot gracefully on SIGTERM
    updater.start_polling()
    updater.idle()

