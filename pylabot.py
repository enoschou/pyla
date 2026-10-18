from io import BytesIO
import json
from time import strftime, time

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
    TextMessage,
    ImageMessage,
    AudioMessage,
    LocationMessage
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
import mutagen

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
    #reply_text = f'{event.message.latitude}\n{event.message.longitude}\n{event.message.address}'
    
    # coordinates to weather info
    coor = (event.message.latitude, event.message.longitude)
    key = env.get('CWA_KEY', '')
    name = cwa.nearest(coor, key)
    info = cwa.get_weather(name, key)
    reply_text = cwa.tostr(info, '\n')
    
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
    with ApiClient(configuration) as api_client:
        line_bot_api_blob = MessagingApiBlob(api_client)
        content = line_bot_api_blob.get_message_content(event.message.id)

        blob_name = f'{event.source.user_id}_echo.m4a'
        bucket_name = env.get('GOOGLE_CLOUD_STORAGE_BUCKET', '')
        blob = storage_client.bucket(bucket_name).blob(blob_name)
        blob.upload_from_string(content, content_type='audio/m4a')
        url = blob.generate_signed_url(int(time())+60)
        duration = int(mutagen.File(BytesIO(content)).info.length*1000)
        messages = [
            AudioMessage(original_content_url=url, duration=duration)
        ]
        
        # with open('test.m4a', 'wb') as f:
        #     f.write(content)
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            )
        )


@handler.add(MessageEvent, message=ImageMessageContent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api_blob = MessagingApiBlob(api_client)
        content = line_bot_api_blob.get_message_content(event.message.id)
        
        # U123423414132131235456465456456_echo.jpg
        blob_name = f'{event.source.user_id}_echo.jpg'
        bucket_name = env.get('GOOGLE_CLOUD_STORAGE_BUCKET', '')
        blob = storage_client.bucket(bucket_name).blob(blob_name)
        blob.upload_from_string(content, content_type='image/jpeg')
        url = blob.generate_signed_url(int(time())+60)
        print(url)
        messages = [
            ImageMessage(original_content_url=url, preview_image_url=url),
            TextMessage(text=url)
        ]
        
        #blob_name = f'{event.source.user_id}_{event.message.id}_{strftime('%Y%m%d%H%M%S')}.jpg'
        #bucket_name = env.get('GOOGLE_CLOUD_STORAGE_BUCKET', '')
        #storage_client.bucket(bucket_name).blob(blob_name).upload_from_string(content,
        #                                                                      content_type='image/jpeg')
        
        #with open('test.jpg', 'wb') as f:
        #    f.write(content)

        #image = Image.open(BytesIO(content))
        #image.show()
        
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
            )
        )


@handler.add(MessageEvent, message=TextMessageContent)
def handle_message(event):
    messages = [
        LocationMessage(title='test', address='台北市', latitude=25.123124, longitude=124.12345)  
    ]

    # with open('test.m4a', 'rb') as f:
    #     audio = f.read()
    # blob_name = 'test.m4a'
    # bucket_name = env.get('GOOGLE_CLOUD_STORAGE_BUCKET', '')
    # blob = storage_client.bucket(bucket_name).blob(blob_name)
    # blob.upload_from_string(audio, content_type='audio/m4a')
    # url = blob.generate_signed_url(int(time())+60)
    # duration = int(mutagen.File(BytesIO(audio)).info.length*1000)
    # messages = [
    #     AudioMessage(original_content_url=url, duration=duration)
    # ]
    
    # url1 = 'https://imgcdn.cna.com.tw/www/webphotos/cnaweekly/culture/2022/1080x764_974223471497.jpg'
    # url2 = 'https://ialive.bwnet.com.tw/AC_Gallery/2024/01/39330fc0-aa86-e227-05cf-d9d4fef7799a.jpg'
    # messages = [
    #     ImageMessage(original_content_url=url2, preview_image_url=url2),
    #     TextMessage(text='hello'),
    #     ImageMessage(original_content_url=url1, preview_image_url=url1)
    # ]
    
    # site = event.message.text
    # key = env.get('CWA_KEY', '')
    # reply_text = cwa.tostr(cwa.get_weather(site, key), '\n')

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
                messages=messages
            )
        )

if __name__ == "__main__":
    app.run()