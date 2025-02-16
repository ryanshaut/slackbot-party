import os, json

from bot import AsyncSlackBot

def load_json(filename):
    return json.load(open(filename))

def load_secrets():
    import dotenv
    dotenv.load_dotenv()

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

    await asyncio.gather(
        dexter.start_async(),
        poppy.start_async()
    )

if __name__ == '__main__':

    
    import asyncio

    asyncio.run(main())