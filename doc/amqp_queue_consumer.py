#!/usr/bin/env python
from __future__ import print_function
import pika
import logging
logging.basicConfig()

HOST = "hostname"
PORT = 5672
USER = "guest"
PASS = "guest"

def on_message(channel, method_frame, header_frame, body):
	print("Message body: ", body)
	channel.basic_ack(delivery_tag=method_frame.delivery_tag)

def main():
	credentials = pika.PlainCredentials(USER, PASS)
	parameters = pika.ConnectionParameters(host=HOST, port=PORT, credentials=credentials)
	connection = pika.BlockingConnection(parameters)

	channel = connection.channel()
	channel.exchange_declare(exchange="munin2es", exchange_type="direct", passive=False, durable=False, auto_delete=True)
	channel.queue_declare(queue="munin2es", auto_delete=True)
	channel.queue_bind(queue="munin2es", exchange="munin2es", routing_key="munin2es")
	channel.basic_qos(prefetch_count=512)
	channel.basic_consume(on_message, 'munin2es')

	try:
		channel.start_consuming()
	except KeyboardInterrupt:
		channel.stop_consuming()

	connection.close()

if __name__ == "__main__":
	main()
