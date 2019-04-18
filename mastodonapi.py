import os
import re
import hashlib
from mastodon import Mastodon

def authinstance(instance, instance_name):
    if not os.path.exists(os.getcwd() + '/teletootbot_{}.secret'.format(instance_name)):
        Mastodon.create_app('teletootbot', api_base_url=instance,
                            to_file='teletootbot_{}.secret'.format(instance_name))


class TootObject:
    def __init__(self, text='', medias=[]):
        self.text = text
        if isinstance(medias, list):
            self.medias = medias
        elif isinstance(medias, str):
            self.medias = [medias]

    def append(self, text='', media=''):
        if text:
            self.text += text + '\n'
        if media:
            self.medias.append(media)


class MastodonAccount:
    def __init__(self, user, instance, password='', hash_str=''):
        self.user = user
        self.instance = instance
        if hash_str:
            self.hash_str = hash_str
        elif password:
            self.hash_str = self.get_hash(password)
            self.auth(password)
        else:
            pass

    @staticmethod
    def get_instance_name(instance):
        return '-'.join(re.search(r'([a-z]*)\.([a-z]*)\/', instance, re.I).groups())

    def get_hash(self, password):
        return hashlib.sha256(self.user.encode() + self.instance.encode() + password.encode()).hexdigest()

    def auth(self, password):
        instance_name = self.get_instance_name(self.instance)
        authinstance(self.instance, instance_name)
        mastodon = Mastodon(client_id='teletootbot_{}.secret'.format(instance_name),
                            api_base_url=self.instance)
        self.hash_str = self.get_hash(password)
        mastodon.log_in(str(self.user), str(password),
                        to_file='{0}.secret'.format(self.hash_str))
                        
    def toot(self, tootobject, visiblity):
        mastodon = Mastodon(access_token='{0}.secret'.format(
            self.hash_str), api_base_url=self.instance)
        if (tootobject.medias and tootobject.text) or (tootobject.medias):
            media_listid = [mastodon.media_post(
                media)['id'] for media in tootobject.medias]
            mastodon.status_post(
                tootobject.text, media_ids=media_listid, visibility=visiblity)
        elif tootobject.text:
            mastodon.status_post(tootobject.text, visibility=visiblity)
        else:
            raise 'Not sufficient argument in toot()'
