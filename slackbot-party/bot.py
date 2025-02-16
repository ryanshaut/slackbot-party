from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import logging
import aiohttp
import uuid
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

class ContextFilter(logging.Filter):
    def filter(self, record):
        record.team = getattr(record, 'team', 'unknown_team')
        record.channel = getattr(record, 'channel', 'unknown_channel')
        record.user = getattr(record, 'user', 'unknown_user')
        return True



class AsyncSlackBot():
    def __init__(self, options, secrets):
        self._options = {**options, **secrets}
        self.__token = self._options["SLACK_BOT_TOKEN"]
        self.state = {}
        self.name = self._options["name"]
        self.llm_app_url = 'https://chatapi.apps.shaut.us'
        self.mylogger = self.create_logger()
        self.__init()
        self.muted = False

    @staticmethod
    def should_process_event(event, bot):
        if bot.muted:
            return False
        # return bot.name == 'Dexter'
        return True


    def __init(self):
        self.client = WebClient(token=self.__token)
        self.app = AsyncApp(token=self.__token)
        self.handler = AsyncSocketModeHandler(app=self.app, app_token=self._options["SLACK_APP_TOKEN"])
        self.register_event_handlers()

    def create_logger(self):
        logger = logging.getLogger(self.name)
        logger.setLevel(logging.INFO)
        ch = logging.StreamHandler()
        ch.setLevel(logging.INFO)
        # add in a potential team name and channel and message user to the format
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)
        logger.addFilter(ContextFilter())
        return logger
    



    def register_event_handlers(self):
        @self.app.event("message")
        async def handle_message_events(body, logger):
            pass # don't do anything with regular messages, yet.
            if not AsyncSlackBot.should_process_event(body, self):
                return
            message = body['event']['text']
            channel = body['event']['channel']
            user = body['event']['user']
            team = body['team_id']

            extra = {'team': team, 'channel': channel, 'user': user}
            self.mylogger = logging.LoggerAdapter(self.mylogger, extra)

            self.mylogger.info(f"Received message: {message}")
            if message.find('rollcall') != -1:
                await self.send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
            elif message.find('reset') != -1:
                self.reset_state(channel)
                await self.send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
            else:
                await self.send_message(channel, f"What's up? (from <@{body['event']['user']}>)")

        @self.app.event("app_mention")
        async def event_test(body, say, logger):
            if not AsyncSlackBot.should_process_event(body, self):
                return
            message = body['event']['text']
            channel = body['event']['channel']
            user = body['event']['user']
            team = body['team_id']

            extra = {'team': team, 'channel': channel, 'user': user}
            self.mylogger = logging.LoggerAdapter(self.mylogger, extra)

            self.mylogger.info(f"Received app_mention: {message}")

            if message.find('rollcall') != -1:
                await self.send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
            elif message.find('reset') != -1:
                self.reset_state(channel)
                await self.send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
            else:
                try:
                    self.mylogger.info("calling LLM app")
                    llm_res = await self.call_llm_app(message, channel)
                    self.mylogger.info(f"Got response back from LLM app")
                    message = llm_res["response"]["content"]
                    await self.send_message(channel, message)
                except Exception as e:
                    await self.send_message(channel, "error calling LLM app: " + str(e))

        @self.app.command('/toggle')
        async def mute(ack, body, logger):
            await ack()
            self.muted = not self.muted
            status = "muted" if self.muted else "unmuted"
            await self.send_message(body['channel_id'], f"I'm now {status} ! (from <@{body['user_id']}>)")

        @self.app.command('/botstatus')
        async def check_status(ack, body, logger):
            await ack()
            status = "muted" if self.muted else "unmuted"
            await self.send_message(body['channel_id'], f"I'm {status} ! (from <@{body['user_id']}>)")


        @self.app.command('/ping')
        async def call_ping(ack, body, logger):
            await ack()
            await self.send_message(body['channel_id'], f"Pong! (from <@{body['user_id']}>)")

        @self.app.command('/rollcall')
        async def call_rollcall(ack, body, logger):
            await ack()
            
            message = body['event']['text']
            channel = body['event']['channel']
            user = body['event']['user']
            team = body['team_id']

            extra = {'team': team, 'channel': channel, 'user': user}
            self.mylogger = logging.LoggerAdapter(self.mylogger, extra)

            self.mylogger.info(f"Received command /rollcall: {message}")

            await self.send_message(body['channel_id'], f"I'm here! (from <@{body['user_id']}>)")
            await self.send_message(body['channel_id'], f"@channel, rollcall! (from <@{body['user_id']}>)")

    def reset_state(self, channel: str):
        self.state[channel] = {"session_id": str(uuid.uuid4()), "context": []}

    async def call_llm_app(self, message: str, channel: str):
        if channel not in self.state:
            self.reset_state(channel)
        req_body = {
            "message": message,
            "session_id": self.state[channel]["session_id"],
        }

        connector = aiohttp.TCPConnector(ssl=False)
        async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(self.llm_app_url + '/chat', json=req_body) as response:
                if response.status == 200:
                    if response.content_type == 'application/json':
                        result = await response.json()
                        return result
                    else:
                        return await response.text()
                else:
                    response.raise_for_status()

    async def send_message(self, channel: str, message: str):
        try:
            if type(message) is not str:
                message = str(message)
            self.mylogger.info(f" > {channel}: {message}")
            self.client.chat_postMessage(
                channel=channel,
                text=message
            )

        except SlackApiError as e:
            assert e.response["error"]

        except Exception as e:
            print(e)

    async def send_startup_message(self, channel: str):
        await self.send_message(channel, self._options["online_message"])
        

    async def start_async(self):
        self.mylogger.info(self._options["online_message"])
        await self.send_startup_message(self._options["default_channel"])
        await self.handler.start_async()