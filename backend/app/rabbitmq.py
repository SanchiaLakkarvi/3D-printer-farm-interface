import aio_pika
import json


async def consume_messages():

    connection = await aio_pika.connect_robust(
        "amqp://guest:guest@localhost/"
    )

    channel = await connection.channel()

    queue = await channel.declare_queue(
        "printer_events",
        durable=True
    )

    async with queue.iterator() as queue_iter:

        async for message in queue_iter:

            async with message.process():

                event = json.loads(message.body)

                print("Received:", event)