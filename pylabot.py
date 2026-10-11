from io import BytesIO
import json
from time import strftime

from flask import Flask, request, abort

from linebot.v3 import (
    WebhookHandler
)
from linebot.v3.exceptions import (
    InvalidSignatureError
)
from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    MessagingApiBlob,
    ReplyMessageRequest,
    TextMessage
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    FileMessageContent,
    LocationMessageContent
)

from google.cloud import storage

from PIL import Image

import cwa


app = Flask(__name__)

try:
    with open('env.json', encoding='utf-8') as f:
        env = json.load(f)
except Exception as e:
    print(e, flush=True)
    env = {}

configuration = Configuration(access_token=env.get('CHANNEL_ACCESS_TOKEN', ''))
handler = WebhookHandler(env.get('CHANNEL_SECRET', ''))
storage_client = storage.Client.from_service_account_json(env.get('GOOGLE_CLOUD_SERVICE', ''))


@app.route("/callback", methods=['POST'])
def callback():
    # get X-Line-Signature header value
    signature = request.headers['X-Line-Signature']

    # get request body as text
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    # handle webhook body
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        app.logger.info("Invalid signature. Please check your channel access token/channel secret.")
        abort(400)

    return 'OK'


@handler.add(MessageEvent, message=LocationMessageContent)
def handle_message(event):
    #print(event)
    reply_text = f'{event.message.latitude}\n{event.message.longitude}\n{event.message.address}'
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )


@handler.add(MessageEvent, message=FileMessageContent)
def handle_message(event):
    print(event)
    with ApiClient(configuration) as api_client:
        line_bot_api_blob = MessagingApiBlob(api_client)
        content = line_bot_api_blob.get_message_content(event.message.id)
        
        with open('test.pdf', 'wb') as f:
            f.write(content)
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f'got file {event.message.file_name}')]
            )
        )



@handler.add(MessageEvent, message=AudioMessageContent)
def handle_message(event):
    print(event)
    with ApiClient(configuration) as api_client:
        line_bot_api_blob = MessagingApiBlob(api_client)
        content = line_bot_api_blob.get_message_content(event.message.id)
        
        with open('test.m4a', 'wb') as f:
            f.write(content)
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f'got audio')]
            )
        )


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_message(event):
    print(event)
    with ApiClient(configuration) as api_client:
        line_bot_api_blob = MessagingApiBlob(api_client)
        content = line_bot_api_blob.get_message_content(event.message.id)
        #blob_name = f'{event.source.user_id}_{event.message.id}_{strftime('%Y%m%d%H%M%S')}.jpg'
        #bucket_name = env.get('GOOGLE_CLOUD_STORAGE_BUCKET', '')
        #storage_client.bucket(bucket_name).blob(blob_name).upload_from_string(content,
        #                                                                      content_type='image/jpeg')
        
        #with open('test.jpg', 'wb') as f:
        #    f.write(content)

        image = Image.open(BytesIO(content))
        #image.show()
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=f'got image {image.height} x {image.width}')]
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    site = event.message.text
    key = env.get('CWA_KEY', '')
    reply_text = cwa.tostr(cwa.get_weather(site, key), '\n')

    # user_ask = event.message.text
    # ask_map = {'hello': '我很好', 'hi': '您哪位？'}
    # reply_text = ask_map.get(user_ask, '我不知道你在說什麼')

    # if user_ask == 'hello':
    #     reply_text = '我很好'
    # elif user_ask == 'hi':
    #     reply_text = '您哪位？'
    # else:
    #     reply_text = '我不知道你在說什麼'
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[TextMessage(text=reply_text)]
            )
        )

if __name__ == "__main__":
    app.run()