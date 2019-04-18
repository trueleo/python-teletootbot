'''

RUN THIS FILE ONCE TO SETUP EMPTY DATABASE

'''

import dataset
import os

file_path = os.path.abspath(os.getcwd())+"/tootbot.db"

db = dataset.connect("sqlite:///" + file_path)

telegram = db.create_table('telegram','chat_id', db.types.integer)
accounts = db.create_table('accounts')

telegram.insert(dict(chat_id=8, default_acc=1))
accounts.insert(dict(user='test', instance='test', hash_str='test', chat_id=8))
