import os
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
import dotenv

dotenv.load_dotenv()

slack_token = os.environ["SLACK_BOT_TOKEN"]
client = WebClient(token=slack_token)

try:
    response = client.chat_postMessage(
        channel="#bots-dev",
        text="Hello world! :tada:"
    )
except SlackApiError as e:
    assert e.response["error"]

except Exception as e:
    print(e)
