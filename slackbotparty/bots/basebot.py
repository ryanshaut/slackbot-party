from slack_bolt.app.async_app import AsyncApp
from slack_bolt.adapter.socket_mode.async_handler import AsyncSocketModeHandler
import logging
from logging.handlers import RotatingFileHandler
import aiohttp
import uuid
from slack_sdk.errors import SlackApiError
from slack_sdk import WebClient

from bot_utils import ContextFilter


class BaseBotAsync():
    def __init__(self, options, secrets):
        self._options = {**options, **secrets}
        self.__token = self._options["SLACK_BOT_TOKEN"]
        self.state = {}
        self.name = self._options["name"]
        self.logger = self.create_logger()
        self.__init()
        self.muted = False
        self.llm_app_url = 'https://chatapi.apps.shaut.us'


    @staticmethod
    def should_process_event(event, bot):
        if bot.muted:
            return False
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
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(team)s - %(channel)s - %(user)s - %(levelname)s - %(message)s')
        ch.setFormatter(formatter)
        logger.addHandler(ch)

        # add file logger to logs/{self.name}.log, rotate every 10mb and new file on every start
        fh = RotatingFileHandler(f'logs/{self.name}.log', maxBytes=10*1024*1024, backupCount=5)   
        fh.setLevel(logging.INFO)
        fh.setFormatter(formatter)
        logger.addHandler(fh)

        logger.addFilter(ContextFilter())
        return logger
    

    def mute(self):
        self.muted = True

    def unmute(self):
        self.muted = False


    def register_event_handlers(self):
        @self.app.event("message")
        async def handle_message(body, logger):
            message = body['event']['text']
            channel = body['event']['channel']
            user = body['event']['user']
            team = body['team_id']

            extra = {'team': team, 'channel': channel, 'user': user}
            adapter = logging.LoggerAdapter(self.logger, extra)

            adapter.info(f"Received message: {message}")
            if not AsyncSlackBot.should_process_event(body, self):
                return

            if message.find('rollcall') != -1:
                await self.send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
            elif message.find('reset') != -1:
                self.reset_state(channel)
                await self.send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
            else:
                await self.send_message(channel, f"What's up? (from <@{body['event']['user']}>)")

        @self.app.event("app_mention")
        async def handle_event(body, say, logger):
            message = body['event']['text']
            channel = body['event']['channel']
            user = body['event']['user']
            team = body['team_id']

            extra = {'team': team, 'channel': channel, 'user': user}
            adapter = logging.LoggerAdapter(self.logger, extra)

            adapter.info(f"Received app_mention: {message}")

            if not AsyncSlackBot.should_process_event(body, self):
                return

            if message.find('rollcall') != -1:
                await self.send_message(channel, f"I'm here! (from <@{body['event']['user']}>)")
            elif message.find('reset') != -1:
                self.reset_state(channel)
                await self.send_message(channel, f"State reset! (from <@{body['event']['user']}>)")
            else:
                try:
                    adapter.info("calling LLM app")
                    llm_res = await self.call_llm_app(message, channel)
                    adapter.info(f"Got response back from LLM app")
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
            logger = logging.LoggerAdapter(self.logger, extra)

            logger.info(f"Received command /rollcall: {message}")

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
        extra = {'team': "", 'channel': channel, 'user': self.name}
        self.logger = logging.LoggerAdapter(self.logger, extra)
        try:
            if type(message) is not str:
                message = str(message)
            self.logger.info(f" > {channel}: {message}")
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
        self.logger.info(self._options["online_message"])
        await self.send_startup_message(self._options["default_channel"])
        await self.handler.start_async()