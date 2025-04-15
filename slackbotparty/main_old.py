import os, dotenv
from slack_bolt import  *
from slack_bolt.adapter.socket_mode import SocketModeHandler
import logging
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import aiohttp
import uuid

dotenv.load_dotenv()

logging.basicConfig(level=logging.WARN)  

mylogger = logging.getLogger(__name__)
mylogger.setLevel(logging.INFO)
# Install the Slack app and get xoxb- token in advance
app = AsyncApp(token=os.environ["SLACK_BOT_TOKEN"])

slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)
llm_app_url = 'https://chatapi.apps.shaut.us'

state = {}
    

def reset_state(channel: str):
    state[channel] = {"session_id": str(uuid.uuid4()), "context": []}

  
async def call_llm_app(message: str, channel: str):
    if channel not in state:
        reset_state(channel)
    req_body = {
        "message": message,
        "session_id": state[channel]["session_id"],
    }

    connector=aiohttp.TCPConnector(ssl=False)
    async with aiohttp.ClientSession(connector=connector) as session:
        async with session.post(llm_app_url + '/chat', json=req_body) as response:
            if response.status == 200:
                if response.content_type == 'application/json':
                    result = await response.json()
                    return result
                else:
                    return await response.text()
            else:
                response.raise_for_status()

async def send_message(channel: str, message: str):
    try:
        if type(message) is not str:
            message = str(message)
        mylogger.info(f"Sending message to channel {channel}: {message}")
        client.chat_postMessage(
            channel = channel,
            text = message
            )

    except SlackApiError as e:
        assert e.response["error"]

    except Exception as e:
        print(e)


@app.event("message")
async def handle_message_events(body, logger):
    
    return
    # check is message is a @mention to this bot. If so, ignore
    message = body['event']['text']
    channel = body['event']['channel']
    if message.find('rollcall') != -1:
        await send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
    elif message.find('reset') != -1:
        reset_state(channel)
        await send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
    else:
        await send_message(channel, f"What's up? (from <@{body['event']['user']}>)")

@app.event("app_mention")
async def event_test(body, say, logger):
    # check is message is a @mention to this bot. If so, ignore
    message = body['event']['text']
    channel = body['event']['channel']
    if message.find('rollcall') != -1:
        await send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
    elif message.find('reset') != -1:
        state[channel] = {"session_id": str(uuid.uuid4()), "context": []}
        await send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
    else:
        try:
            mylogger.info("calling LLM app")
            llm_res = await call_llm_app(message, channel)
            mylogger.info(f"Got response back from LLM app")
            message = llm_res["response"]["content"]
            await send_message(channel, message)
        except Exception as e:
            await send_message(channel, "error calling LLM app: " + str(e))
            
@app.command('/rollcall')
async def call_rollcall(ack, body, logger):
    await ack()
    await send_message(body['channel_id'], f"I'm here! (from <@{body['user_id']}>)")
    await send_message(body['channel_id'], f"@channel, rollcall! (from <@{body['user_id']}>)")




async def main():
    mylogger.info("Starting the app")
    # Create an app-level token with connections:write scope
    #handler = SocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    handler.start_async()


async def main():
    handler = AsyncSocketModeHandler(app, os.environ["SLACK_APP_TOKEN"])
    await handler.start_async()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())