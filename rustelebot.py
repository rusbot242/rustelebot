#!/usr/bin/env python

import logging
import ujson

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, ParseMode
from telegram.ext import Updater, MessageHandler, CommandHandler, CallbackQueryHandler, Filters, CallbackContext

from datetime import time
from tinydb import TinyDB, Query

from texts import start_text, edit_text, completed_text, non_existing_question, non_number_entry, help_text, questions, edit_text


configfile = "config.json"
dbfile = "db.json"


db = TinyDB(dbfile)
config = ujson.load(open(configfile, "r"))

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def start(update, context) -> None:
    """Sends a message with inline buttons attached."""
    context.bot.send_message(chat_id=update.message.chat.id, text=start_text, parse_mode=ParseMode.HTML, disable_web_page_preview=True)
#    update.message.reply_text(start_text, parse_mode=ParseMode.HTML)
    
    # create entry in db if chat_instance does not exist yet
    # we also store the current question a user is on, as we need to know it for when the bot receives
    # an ordinary message (aka an answer to a question). When collecting the data, this information is omitted
    if (db.search(Query().chat_id == update.message.chat.id) == []):
        db.insert({'chat_id': update.message.chat.id,
                   'question': 1,
                   })
    else:
        db.update({'question': 1}, Query().chat_id == update.message.chat.id)
        print(f"user {update.message.chat.id} already in database, reset question to 1")


def button(update, context) -> None:
    """Parses the CallbackQuery and updates the message text."""
    query = update.callback_query

    # CallbackQueries need to be answered, even if no notification to the user is needed
    # Some clients may have trouble otherwise. See https://core.telegram.org/bots/api#callbackquery
    query.answer()

    # check query.data which button is pressed: edit question, or next question
    # if user hits edit question, update database question to ?
    if query.data == "Edit":
        query.message.reply_text(f"Напишите номер вопроса, ответ на который вы хотите отредактировать")
        db.update({'question': '?'}, Query().chat_id == query.message.chat.id)

    elif query.data == "Next":
        # get highest dict key and go from there, since we want the next button to work even if question is ?
        question = max([int(i) if i.isnumeric() else 0 for i in list(db.search(Query().chat_id == query.message.chat_id)[0].keys())])
        print("QUESTION:", question)
        if question >= len(questions):
            query.message.reply_text(completed_text)
        else:
            db.update({'question': (question + 1)}, Query().chat_id == query.message.chat.id)
            print("QUESTION:", questions[question - 1])
            query.message.reply_text(f"{question + 1}) {questions[question]}")

    else:
        query.message.reply_text("idk what you did, but you managed to hit a non-existing button. Please click Edit or Next")



def help_command(update, context) -> None:
    update.message.reply_text(help_text)


def mhandler(update, context):
    # check what what question user is on
    message = update.message

    question = db.search(Query().chat_id == message.chat_id)[0].get('question')
    if (question == "?"):
        try:
            if (str(int(message.text)) in db.search(Query().chat_id == message.chat.id)[0]):
                db.update({f'question': int(message.text)}, Query().chat_id == message.chat.id)
                message.reply_text(f"В настоящее время вы редактируете свой ответ на вопрос {message.text}, предыдущий ответ на этот вопрос будут полностью перезаписан вашим новым ответом. Если это не входит в ваши намерения, нажмите «Следующий», чтобы перейти к следующему вопросу.") 
            else:
                message.reply_text(non_existing_question)
        except ValueError:
                message.reply_text(non_number_entry)
    else:
        db.update({f'{question}': str(message.text)}, Query().chat_id == message.chat.id)
        message.reply_text(f"Ваш ответ на вопрос {question}: «{questions[question - 1]}» был обновлен до:\n«{message.text}»")
        keyboard = [
            [ InlineKeyboardButton(f"Отредактировать", callback_data="Edit")
            , InlineKeyboardButton(f"Следующий", callback_data="Next")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        update.message.reply_text(edit_text, reply_markup=reply_markup)


if __name__ == '__main__':
    updater = Updater(config['token'])

    updater.dispatcher.add_handler(CommandHandler('start', start))
    updater.dispatcher.add_handler(CommandHandler('help', help_command))
    updater.dispatcher.add_handler(CallbackQueryHandler(button))
    updater.dispatcher.add_handler(MessageHandler(Filters.text, mhandler))
    
    #dispatcher.add_error_handler(mhandler.exception)
    # start_polling() is non-blocking and will stop the bot gracefully on SIGTERM
    updater.start_polling()
    updater.idle()

