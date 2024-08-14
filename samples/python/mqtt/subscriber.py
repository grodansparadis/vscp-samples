#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
A simple VSCP demo server MQTT subscriber
"""
import paho.mqtt.client as paho

def on_message(mosq, obj, msg):
    print("%-20s %d %s" % (msg.topic, msg.qos, msg.payload))
    mosq.publish('pong', 'ack', 0)

def on_publish(mosq, obj, mid):
    pass

if __name__ == '__main__':
    client = paho.Client()
    client.on_message = on_message
    client.on_publish = on_publish

    client.username_pw_set(username="vscp", password="secret")

    #client.tls_set('root.ca', certfile='c1.crt', keyfile='c1.key')
    client.connect("mqtt.vscp.org", 1883, 60)

    client.subscribe("vscp/25:00:00:00:00:00:00:00:00:00:00:00:0D:02:00:01/20/3/#", 0) // ON
    client.subscribe("vscp/25:00:00:00:00:00:00:00:00:00:00:00:0D:02:00:01/20/4/#", 0) // OFF

    while client.loop() == 0:
      pass

# vi: set fileencoding=utf-8 :
