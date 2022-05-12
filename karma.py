#! /usr/bin/python3

# by FvH, released under Apache License v2.0

# either install 'python3-paho-mqtt' or 'pip3 install paho-mqtt'

import paho.mqtt.client as mqtt
import sqlite3
import threading
import time

mqtt_server  = '192.168.64.1'
topic_prefix = 'GHBot/'
channels     = ['nurdbottest', 'test']
db_file      = 'karma.db'

con = sqlite3.connect(db_file)

def on_message(client, userdata, message):
    text = message.payload.decode('ascii')

    topic = message.topic[len(topic_prefix):]

    parts = topic.split('/')
    channel = parts[2]
    nick = parts[3]

    if channel in channels:
        if text[0] == '~':
            tokens  = text.split(' ')

            if len(tokens) != 2:
                return

            command = tokens[0][1:]
            word    = tokens[1]

            if command == 'karma':
                query = 'SELECT count FROM karma WHERE channel=? and word=?'

                cur = con.cursor()

                try:
                    cur.execute(query, (channel.lower(), word.lower()))

                    row = cur.fetchone()

                    if row == None:
                        client.publish(f'{topic_prefix}to/irc/{channel}/privmsg', f'"{word}" has no karma (yet)')

                    else:
                        client.publish(f'{topic_prefix}to/irc/{channel}/privmsg', f'Karma of "{word}" is {row[0]}')

                except Exception as e:
                    print(f'Exception: {e}')

        else:
            for word in text.split(' '):
                count = 0

                add = 0
                while word[-1] == '+':
                    add += 1

                    word = word[:-1]

                if add >= 2:
                    count += add - 1

                sub = 0
                while word[-1] == '-':
                    sub += 1

                    word = word[:-1]

                if sub >= 2:
                    count -= sub - 1

                if count != 0:
                    print(f'Adding {count} karma to {word}')

                    query = 'INSERT INTO karma(channel, word, count) VALUES(?, ?, ?) ON CONFLICT(channel, word) DO UPDATE SET count=count+?'

                    cur = con.cursor()

                    try:
                        cur.execute(query, (channel.lower(), word.lower(), count, count))

                    except sqlite3.OperationalError as oe:
                        # table does not exist probably

                        try:
                            query = 'CREATE TABLE karma(channel TEXT NOT NULL, word TEXT NOT NULL, count INTEGER, PRIMARY KEY(channel, word))'

                            cur.execute(query)

                        except Exception as e:
                            print(f'Unexpected exception {e} while handling exception {oe}')

                    con.commit()
                    cur.close()

def on_connect(client, userdata, flags, rc):
    if rc == 0:
        client.subscribe(f'{topic_prefix}from/irc/#')

def announcer(client):
    target_topic = f'{topic_prefix}to/bot/register'

    print(f'Announcing to {target_topic}')

    while True:
        time.sleep(3)

        client.publish(target_topic, 'cmd=karma|descr=Show karma of a word/entity.')

        time.sleep(27)

client = mqtt.Client()
client.connect(mqtt_server, port=1883, keepalive=4, bind_address="")
client.on_message = on_message
client.on_connect = on_connect

t = threading.Thread(target=announcer, args=(client,))
t.start()

client.loop_forever()
