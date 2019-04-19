from telegram.ext import MessageHandler, Filters, CommandHandler, Updater
from mastodon import MastodonIllegalArgumentError, MastodonUnauthorizedError
import DataHandler
import threading
import os
import sys
import logging
import certifi
import urllib3
import re

bot_token = '<your bot token here>'

# secretfile = open('secretbot', 'r')
# secret = secretfile.readline().rstrip('\n')
#bot_token = secret


logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)

test_visibility = 'public'

group_media_queue = {}
lookup_dict = {}
tootObject = DataHandler.mastodonapi.TootObject

def geturl(url_string):
    man = urllib3.PoolManager(cert_reqs='CERT_REQUIRED', ca_certs=certifi.where() ,num_pools=1)
    response = man.urlopen('GET', url_string)
    rurl = response.geturl()
    return re.search(r'([://a-z.0-9]+/)', rurl, re.I).group(0)

def load_account(chat_id, force_reload=False):
    try:
        if force_reload:
            raise KeyError
        return lookup_dict[chat_id]
    except KeyError:
        account = DataHandler.account_object(chat_id)
        lookup_dict[chat_id] = account
        return account

def process_group_media(chat_id, key):
    toot_obj = group_media_queue.pop(key)
    tooting(chat_id, toot_obj, test_visibility)
    for media in toot_obj.medias:
        os.remove(media)


def add_to_group_media_queue(chat_id, group_id, media, caption):
    key = str(chat_id) + str(group_id)
    try:
        media_container = group_media_queue[key]
    except KeyError:
        threading.Timer(30, process_group_media, [chat_id, key]).start()
        media_container = tootObject()
        group_media_queue[key] = media_container
    finally:
        media_container.append(caption, media)


def tooting(chat_id, tootobject, visibility):
    load_account(chat_id).toot(tootobject, visibility)
 
def reply(context, chat_id, text):
    context.bot.send_message(chat_id=chat_id, text=text, parse_mode='markdown')

def start(update, context):
    context.bot.send_message(chat_id=update.message.chat_id,
                             text="Toot to Mastodon using this bot. See /help")

def add(update, context):
    chat_id = update.message.chat_id
    try:
        assert len(context.args) == 3
    except AssertionError:
        reply(context, chat_id, 'usage:`\n/add <user_email> <password> <full_instance_url>`\nexample: `/add john@doe.com cyberpunk277 https://mastodon.social/`')
        return
    else:
        username = context.args[0]
        instance = geturl(context.args[2])
        password = context.args[1]
    try:
        newAcc = DataHandler.insert_account( chat_id,
                                             username,
                                             instance, 
                                             password)
    except MastodonIllegalArgumentError:
        reply(context, chat_id, 'Authentication failed')
        reply(context, chat_id, 'usage:`\n/add <user_email> <password> <full_instance_url>`\nexample: `\add john@doe.com cyberpunk277 https://mastodon.social/`')
    except MastodonUnauthorizedError:
        reply(context, chat_id, 'Authentication failed')
    except DataHandler.InsertError:
        reply(context, chat_id, 'Account already registered')
    except:
        reply(context, chat_id, 'Oops!, Something gone wrong. Check and try again')
    else:
        if isinstance(newAcc, DataHandler.mastodonapi.MastodonAccount) and (DataHandler.number_of_accounts(chat_id) == 1):
            lookup_dict[chat_id] = newAcc
            DataHandler.upsert_user(chat_id, 1)
        reply(context, chat_id, 'Great!, You can use /listall to list your currently registered accounts')


def setdefault(update, context):
    chat_id = update.message.chat_id
    number_of_accounts = DataHandler.number_of_accounts(chat_id)
    if number_of_accounts == 1:
        acc = DataHandler.account_info(chat_id)
        reply(context, chat_id, "Your only registered account is `{}` at `{}`".format(acc[0], acc[1]))
        return
    try:
        newDefault = int(context.args[0])
        if newDefault <= number_of_accounts:
            DataHandler.upsert_user(chat_id, newDefault)
            accountObj = load_account(chat_id, force_reload=True)
            reply(context, chat_id,
                    "Now you can toot to your account `{}` at `{}`".format(
                    accountObj.user,
                    accountObj.instance))
        else:
            reply(context, chat_id,
                    "You need to specify right account number as given in /listall")
    except:
        reply(context, chat_id, "`/setdefault` <number>")


def delete(update, context):
    chat_id = update.message.chat_id
    number_of_accounts = DataHandler.number_of_accounts(chat_id)
    
    if number_of_accounts == 0:
        reply(context, chat_id,
                  'You don\'t have any registered account(s) to delete')
    elif number_of_accounts == 1:
        DataHandler.delete_user(chat_id)
        lookup_dict.pop(chat_id)
    else:
        try:
            acc_num = int(context.args[0])
            if acc_num > number_of_accounts:
                reply(context, chat_id, "You need to specify right account number as given in /listall")
                return
            current_default = DataHandler.get_default_acc(chat_id)
            id_to_delete = DataHandler.account_id(chat_id, acc_num) 
            DataHandler.delete_account(id_to_delete)
            if id_to_delete == current_default:
                DataHandler.upsert_user(chat_id, 1)
                load_account(chat_id, force_reload=True)
                account_info_tuple = DataHandler.account_info(chat_id)
                reply(context, chat_id, 'Your current default account is now set to {username} @ {instance}'.format(
                                                                                                    username=account_info_tuple[0],
                                                                                                    instance=account_info_tuple[1]))
        except:
            reply(context, chat_id, '`usage:`\n`/delete <number>`')

def deleteall(update, context):
    chat_id = update.message.chat_id
    try: 
        assert (context.args[0] == 'yes')
    except:
        reply(context, chat_id, '`NOTE: delete all registered accounts \nusage:\n/deleteall yes`')
    else:
        DataHandler.delete_user(chat_id)
        try:
            lookup_dict.pop(chat_id)
        except KeyError:
            pass

def listall(update, context):
    chat_id = update.message.chat_id
    text = DataHandler.all_accounts(chat_id)
    reply(context, chat_id, "currenly registered accounts\n" + text)


def media(update, context):
    chat_id = update.message.chat_id
    file_id = update.message.photo[-1].file_id
    newFile = context.bot.get_file(file_id)
    file_url = newFile.file_path
    file_ext = re.search(r'\.[0-9a-z]+$', file_url).group()
    media_name = 'media-' + str(file_id) + file_ext
    newFile.download(media_name)
    if update.message.media_group_id:
        add_to_group_media_queue(chat_id, update.message.media_group_id,
                           media_name, update.message.caption)
    else:
        try:
            tooting(chat_id, tootObject(update.message.caption, media_name), test_visibility)
        except DataHandler.NoDataError:
            reply(context, chat_id, 'Please add an account first using /add')

def text(update, context):
    chat_id = update.message.chat_id
    try:
        tooting(chat_id, tootObject(update.message.text), test_visibility)
    except DataHandler.NoDataError:
        reply(context, chat_id, 'Please add an account first using /add')

def helpcommand(update, context):
    chat_id = update.message.chat_id
    reply(context, chat_id, "With TeleToot Bot you can to post on any Mastodon account's public timeline. Currently you can only post on one account at a time although you can authenticate various accounts and switch between them\n`availible commands:\n`/add\n/listall\n/setdefault\n/delete\n/deleteall") 
    reply(context, chat_id, "To start tooting using your mastodon account send `/add <registered email> <password> <instance_url>`. See /add for more detail")

updater = Updater(bot_token, use_context=True)
dispatcher = updater.dispatcher

list_of_commands = [start, add, listall, setdefault, delete, deleteall]

def load_commands(commands):
    for command in commands:
        dispatcher.add_handler(CommandHandler(command.__name__, command))

load_commands(list_of_commands)


media_handler = MessageHandler(Filters.photo | (Filters.text & Filters.photo),
                                               media, pass_job_queue=True)

text_handler = MessageHandler(Filters.text, text)
dispatcher.add_handler(media_handler)
dispatcher.add_handler(text_handler)
dispatcher.add_handler(CommandHandler('help', helpcommand))

updater.start_polling(poll_interval=1.0, timeout=60)
updater.idle()
