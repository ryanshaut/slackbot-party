import json
import asyncio
import signal

from bots.asyncslackbot import AsyncSlackBot
from bots.asyncwebhookconsumerbot import AsyncWebhookConsumerBot

def load_json(filename):
    return json.load(open(filename))

def load_secrets():
    # import dotenv
    # dotenv.load_dotenv()

    secrets = load_json("secrets.json")
    return secrets

def load_options():
    options = load_json("bot_definitions/all.json")
    return options

async def main():

    secrets = load_secrets()
    options = load_options()

    dexter = AsyncSlackBot(options.get('Dexter'), secrets.get('Dexter'))
    poppy = AsyncSlackBot(options.get('Poppy'), secrets.get('Poppy'))

    louie = AsyncWebhookConsumerBot(options.get('Louie'), secrets.get('Louie'))

    dexter.mute()
    poppy.mute()

    async with asyncio.TaskGroup() as tg:
        tg.create_task(dexter.start_async())
        tg.create_task(poppy.start_async())
        tg.create_task(louie.start_async())


# Graceful shutdown
def shutdown():
    for task in asyncio.all_tasks():
        task.cancel()

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, shutdown)

    try:
        loop.run_until_complete(main())
    except asyncio.CancelledError:
        pass
    finally:
        loop.close()