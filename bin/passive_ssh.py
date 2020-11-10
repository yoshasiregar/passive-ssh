#!/usr/bin/env python3
# -*-coding:UTF-8 -*

import redis

redis_host = 'localhost'
redis_port = 7301
redis_ssh = redis.StrictRedis(host=redis_host, port=redis_port, db=0, decode_responses=True)

######################################

# def sanityze_date(date_from, date_to):
#     if not date_from and not date_to:
#         return (0, -1)
#     if date_from:

def unpack_date(date):
    if len(date) == 8:
        date = time.mktime(time.strptime(s, "%Y%m%d"))
    else:
        try:
            date = int(date)
        except:
            date = None
    return date

######################################

def get_host_type(host):
    if str(host).endswith('.onion'):
        return 'onion'
    else:
        return 'ip'

def get_all_keys_types():
    return redis_ssh.smembers('all:key:type')

def get_all_key_fingerprint_by_type(key_type):
    return redis_ssh.smembers('all:key:fingerprint:{}'.format(key_type))

def get_all_onion():
    return redis_ssh.smembers('all:onion')

def get_all_ip():
    return redis_ssh.smembers('all:ip')

#### BANNER ####
def get_all_banner():
    return redis_ssh.smembers('all:banner')

def get_banner_host(banner, host_type=None):
    if not host_type:
        host_type = get_host_type(host)
    return redis_ssh.smembers('banner:{}:{}'.format(host_type, banner))

def get_banner_host_nb(banner, host_type=None):
    if not host_type:
        host_type = get_host_type(host)
    return redis_ssh.scard('banner:{}:{}'.format(host_type, banner))

def get_banner_by_host(host, host_type=None):
    if not host_type:
        host_type = get_host_type(host)
    return redis_ssh.smembers('{}:banner:{}'.format(host_type, host))

#### ####

#### HASSH ####
def get_host_by_hassh(hassh, host_type=None):
    if not host_type:
        host_type = get_host_type(host)
    return redis_ssh.smembers('hassh:{}:{}'.format(host_type, hassh))

def get_hassh_by_host(host, host_type=None):
    return redis_ssh.smembers('{}:hassh:kex:{}'.format(host_type, host))

def get_hassh_kex(hassh):
    return list(redis_ssh.smembers('hassh:kex:{}'.format(hassh)))

def get_host_kex(host, host_type=None, hassh=None, hassh_host=None): ## TODO: # OPTIMIZE:
    host_kex = {}
    for hassh in get_hassh_by_host(host, host_type=host_type):
        host_kex[hassh] = get_hassh_kex(hassh)
    return host_kex
#### ####

def get_host_fingerprint(host, host_type=None):
    if not host_type:
        host_type = get_host_type(host)
    return redis_ssh.smembers('{}:{}'.format(host_type, host))

def get_host_by_fingerprint(key_type, fingerprint, host_type='ip'):
    return redis_ssh.smembers('fingerprint:{}:{}:{}'.format(host_type, key_type, fingerprint))

def get_host_history(host, host_type=None, date_from=None, date_to=None, get_key=False):
    # # TODO:
    #date_from, date_to = sanityze_date()
    if not host_type:
        host_type = get_host_type(host)
    ssh_history = redis_ssh.zrange('fingerprint:history:{}:{}'.format(host_type, host), 0 , -1, withscores=True)
    if not get_key:
        return ssh_history
    else:
        host_history = {}
        for history_tuple in ssh_history:
            epoch = int(history_tuple[1])
            host_history[epoch] = list(get_host_key_by_epoch(host, epoch, host_type=host_type))
        return host_history

def get_host_key_by_epoch(host, epoch, host_type=None):
    return redis_ssh.smembers('{}:fingerprint:{}:{}'.format(host_type, host, epoch))


#### METADATA ####
def get_host_metadata(host, host_type=None, banner=False, hassh=False, kex=False, pkey=False):
    if not host_type:
        host_type = get_host_type(host)
    host_metadata = {}
    host_metadata['first_seen'] = redis_ssh.hget('{}_metadata:{}'.format(host_type, host), 'first_seen')
    host_metadata['last_seen'] = redis_ssh.hget('{}_metadata:{}'.format(host_type, host), 'last_seen')
    port = host_metadata['port'] = redis_ssh.hget('{}_metadata:{}'.format(host_type, host), 'port')
    if not port:
        port = 22
    host_metadata['port'] = port
    if banner:
        host_metadata['banner'] = list(get_banner_by_host(host, host_type=host_type))
    if hassh:
        if kex:
            host_metadata['hassh'] = get_host_kex(host, host_type=host_type)
        else:
            host_metadata['hassh'] = get_host_kex(host, host_type=host_type)
            host_metadata['kex'] = json.load(get_hassh_by_host(host, host_type=host_type))
    if pkey:
        host_metadata['pkey'] = list(get_host_fingerprint(host, host_type=host_type))
    return host_metadata

def get_key_metadata(key_type, fingerprint):
    key_metadata = {}
    key_metadata['first_seen'] = redis_ssh.hget('onion_metadata:{}', 'first_seen')
    key_metadata['last_seen'] = redis_ssh.hget('onion_metadata:{}', 'last_seen')
    key_metadata['base64'] = get_key_base64(key_type, fingerprint)
    return key_metadata

def get_key_base64(key_type, fingerprint):
    return redis_ssh.hget('key_metadata:{}:{}'.format(key_type, fingerprint), 'base64')

#### ####

#### ADVANCED ####
def deanonymize_onion():
    fing_inter = redis_ssh.sinter('all:ip:fingerprint', 'all:onion:fingerprint')
    deanonymized_onion = []
    for row_fingerprint in fing_inter:
        key_type, fingerprint = row_fingerprint.split(';')
        fing_match = {}
        fing_match['onion'] = get_host_by_fingerprint(key_type, fingerprint, host_type='onion')
        fing_match['ip'] = get_host_by_fingerprint(key_type, fingerprint, host_type='ip')
        deanonymized_onion.append(fing_match)
    return deanonymized_onion

def get_stats_nb_banner(sorted=True, host_type='ip', reverse=False):
    nb_banner = {}
    for banner in get_all_banner():
        nb_banner[banner] = get_banner_host_nb(banner, host_type=host_type)
    if sorted:
        return [(k, nb_banner[k]) for k in sorted(nb_banner, key=nb_banner.get, reverse=reverse)]
    else:
        return nb_banner
#### ####


if __name__ == '__main__':
    deanonymize_onion()
