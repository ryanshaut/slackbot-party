import logging
from bots.basebot import BaseBotAsync

class AsyncSlackBot(BaseBotAsync):
    def __init__(self, options, secrets):
        super().__init__(options, secrets)
        self._options = {**options, **secrets}
    

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

    async def send_startup_message(self, channel: str):
        await self.send_message(channel, self._options["online_message"])
        