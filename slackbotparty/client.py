import os, json
import asyncio
import signal
from slack_sdk.errors import SlackApiError


from bot import AsyncSlackBot

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

async def main(message):

    secrets = load_secrets()
    options = load_options()

    louie = AsyncSlackBot(options.get('Louie'), secrets.get('Louie'))
    
    try:
        await louie.send_message(
            channel="#bots-dev",
            message=message
        )
    except SlackApiError as e:
        print(f"Slack Error: {e}")
        assert e.response["error"]

    except Exception as e:
        print(f"Error: {e}")


if __name__ == '__main__':
    import sys
    message = sys.argv[1] if len(sys.argv) > 1 else "Hello world! :tada:"
    asyncio.run(main(message))
