import mastodonapi
import dataset
import os

def upsert_user(chat_id, default_acc):
    try:
        acc_id = account_id(chat_id, default_acc)
        data = dict(chat_id=chat_id, default_acc=acc_id)
        telegram.upsert(data, ['chat_id'])
    except:
        raise InsertError

def delete_user(chat_id):
    telegram.delete(chat_id=chat_id)
    secretfiles = [od['hash_str'] for od in accounts.find(chat_id=chat_id)]
    for i in secretfiles:
        os.remove(i+'.secret')
    accounts.delete(chat_id=chat_id)

def insert_account(chat_id, username, instance, password):
    if not accounts.find_one(user=username, instance=instance):
        tootAcc = mastodonapi.MastodonAccount(username, instance, password=password)
        accounts.insert(dict(user=tootAcc.user, instance=tootAcc.instance, hash_str=tootAcc.hash_str, chat_id=chat_id))
        return tootAcc
    else:
        raise InsertError

def delete_account(accountid):
    try:
        accounts.delete(id=accountid)
    except:
        pass

def account_id(chat_id, index):
    try:
        iterobj = accounts.find(chat_id=chat_id)
        i = 1
        while i < index:
            iterobj.__next__()
            i += 1
        return iterobj.__next__()['id']
    except StopIteration:
        raise NoDataError

def account_info(chat_id):
        teleuser = telegram.find_one(chat_id=chat_id)
        if not teleuser:
            return '', '', ''
        acc_id = teleuser['default_acc']
        account = accounts.find_one(id=acc_id)
        return account['user'], account['instance'], account['hash_str']

def account_object(chat_id):
    user, instance, hash_str = account_info(chat_id)
    if not (user or instance or hash_str):
        raise NoDataError
    account = mastodonapi.MastodonAccount(user, instance, hash_str=hash_str)
    return account

def all_accounts(chat_id):
    text = ''
    i = 1
    records = accounts.find(chat_id=chat_id)
    for account in records:
        text += str(i) + '. ' + str(account['user']) + '@' + str(
            mastodonapi.MastodonAccount.get_instance_name(account['instance'])) + '\n'
        i += 1
    return text

def get_default_acc(chat_id):
    return telegram.find_one(chat_id=chat_id)['default_acc']

def number_of_accounts(chat_id):
    qry = 'select count(*) c from accounts where chat_id={}'.format(chat_id)
    count = db.query(qry).next()['c']
    return count

class NoDataError(BaseException):
    pass

class InsertError(BaseException):
    pass

db = dataset.connect("sqlite:///tootbot.db")
telegram = db.create_table('telegram', 'chat_id', db.types.integer)
accounts = db.create_table('accounts')
