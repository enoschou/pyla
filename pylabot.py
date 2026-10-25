from io import BytesIO
import json
from time import strftime, time
from copy import deepcopy

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
    LocationMessage,
    FlexMessage,
    FlexContainer,
    Sender,
    QuickReply,
    QuickReplyItem,
    MessageAction,
    CameraAction,
    URIAction,
    PostbackAction
)
from linebot.v3.webhooks import (
    MessageEvent,
    TextMessageContent,
    ImageMessageContent,
    AudioMessageContent,
    FileMessageContent,
    LocationMessageContent,
    PostbackEvent,
    FollowEvent
)

from google.cloud import storage, firestore
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
firestore_client = firestore.Client.from_service_account_json(env.get('GOOGLE_CLOUD_SERVICE', ''))


users = {
    'U111': {'count': 107},
    'U222': {'count': 55},
    'U333': {'count': 280}
}


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


def create_weather_flex(info: str):
    tables = []
    name = 'NA'
    for item in info.split(';'):
        row = item.strip().split(':')
        if row[0] == '測站':
            name = row[1]
        else:
            tables.append(row)

    weather_flex = {
        'type': 'bubble',
        'body': {
            'type': 'box',
            'layout': 'vertical',
            'contents': [
                {'type': 'text', 'text': name, 'weight': 'bold', 'size': 'xl'},
                {'type': 'box', 'layout': 'vertical', 'margin': 'lg', 'spacing': 'sm', 'contents': []}
            ]
        }
    }
    
    item = {
        "type": "box",
        "layout": "baseline",
        "spacing": "sm",
        "contents": [
            {"type": "text", "text": "編號", "color": "#0000FF", "size": "sm", "flex": 1},
            {"type": "text", "text": "A123456", "wrap": True, "color": "#666666", "size": "sm", "flex": 5}
        ]
    }

    for t in tables:
        i = deepcopy(item)
        i['contents'][0]['text'] = t[0].strip()
        i['contents'][1]['text'] = t[1].strip()
        weather_flex['body']['contents'][1]['contents'].append(i)

    return FlexMessage(alt_text='weather info', contents=FlexContainer.from_dict(weather_flex))
    

@handler.add(MessageEvent, message=LocationMessageContent)
def handle_message(event):
    #reply_text = f'{event.message.latitude}\n{event.message.longitude}\n{event.message.address}'
    
    # coordinates to weather info
    coor = (event.message.latitude, event.message.longitude)
    key = env.get('CWA_KEY', '')
    #name = cwa.nearest(coor, key)
    name, *nears = cwa.nearest(coor, key, 5)
    info = cwa.get_weather(name, key)
    reply_text = cwa.tostr(info, '\n')
    site_coor = info.get('C')
    messages = []
    if site_coor:
        messages.append(
            LocationMessage(
                title=info.get('S', 'N/A'),
                address=info.get('S', 'N/A'),
                latitude=site_coor[0],
                longitude=site_coor[1]
            )
        )    
    #messages.append(TextMessage(text=reply_text))
    items = [QuickReplyItem(action=MessageAction(label="📍"+n, text=n)) for n in nears]
    weather_flex = create_weather_flex(cwa.tostr(info, ';'))
    weather_flex.quick_reply = QuickReply(items=items)
    messages.append(weather_flex)
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=messages
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
    n = event.message.text
    if n == 'profile':
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            profile = dict(line_bot_api.get_profile(user_id=event.source.user_id))
            print(profile)
            return
    elif n == 'count':
        carousel = {
            "type": "carousel",
            "contents": []
        }
        with open('bubble.json', encoding='utf-8') as f:
            bubble = json.load(f)
        for u in users:
            b = deepcopy(bubble)
            b['body']['contents'][0]['contents'][0]['contents'][1]['text'] = u
            b['footer']['contents'][0]['action']['data'] = u
            carousel['contents'].append(b)

        messages = [
            FlexMessage(
                alt_text='count',
                contents=FlexContainer.from_dict(carousel)
            )
        ]
    elif n.isdigit():
        n = int(n)
        carousel = {
            "type": "carousel",
            "contents": []
        }
        with open('bubble.json', encoding='utf-8') as f:
            bubble = json.load(f)
        for i in range(n):
            carousel['contents'].append(bubble)

        messages = [
            FlexMessage(
                sender=Sender(name='Enos', icon_url='https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png'),
                alt_text=f'{n} bubbles',
                contents=FlexContainer.from_dict(carousel)
            )
        ]
    elif n == 'test':
        with open('actions.json', encoding='utf-8') as f:
            bubble = json.load(f)
        messages = [
            FlexMessage(
                alt_text=f'actions',
                contents=FlexContainer.from_dict(bubble)
            )
        ]
    elif n == 'action':
        items = [
            QuickReplyItem(action=MessageAction(label='hello', text='hello'), image_url='https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png'),
            QuickReplyItem(action=CameraAction(label='carema')),
            QuickReplyItem(action=URIAction(label='carema2', uri='https://line.me/R/nv/camera/')),
            QuickReplyItem(action=PostbackAction(label="postback", data="action postback"))
        ]
        quick_reply = QuickReply(items=items)
        messages = [
            TextMessage(text='請測試', quick_reply=quick_reply)
        ]
    else:
        key = env.get('CWA_KEY', '')
        text = cwa.tostr(cwa.get_weather(n, key), '\n')
        messages = [TextMessage(text=text)]
    
    # with open('carousel.json', encoding='utf-8') as f:
    #     json_str = f.read()
            
    # messages = [
    #     FlexMessage(
    #         alt_text='alt message',
    #         contents=FlexContainer.from_json(json_str)
    #     )
    # ]
    
    # if event.message.text == 'me':
    #     with open('bubble.json', encoding='utf-8') as f:
    #         json_str = f.read()
            
    #     messages = [
    #         FlexMessage(
    #             alt_text='alt message',
    #             contents=FlexContainer.from_json(json_str)
    #         )
    #     ]
    # else:
    #     return
    
    # messages = [
    #     LocationMessage(title='test', address='台北市', latitude=25.123124, longitude=124.12345)  
    # ]

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

@handler.add(PostbackEvent)
def handle_message(event):
    if event.postback.data == 'next':
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            line_bot_api.link_rich_menu_id_to_user(
                user_id=event.source.user_id,
                rich_menu_id='richmenu-39d09cac7fe91913a10fdaf44b0d6862'
            )
        return
    if  event.postback.data == 'back':
        with ApiClient(configuration) as api_client:
            line_bot_api = MessagingApi(api_client)
            # line_bot_api.link_rich_menu_id_to_user(
            #     user_id=event.source.user_id,
            #     rich_menu_id='richmenu-5f61eadfceb1aab4ae0b4efd2c14c65e'
            # )
            line_bot_api.unlink_rich_menu_id_from_user(user_id=event.source.user_id)
        return
    
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    TextMessage(text=f'{users[event.postback.data]['count']}')
                ]
            )
        )

@handler.add(FollowEvent)
def handle_message(event):
    with ApiClient(configuration) as api_client:
        line_bot_api = MessagingApi(api_client)

        profile = dict(line_bot_api.get_profile(user_id=event.source.user_id))
        display_name = profile.get('display_name')
        picture_url = profile.get('picture_url') or 'https://developers-resource.landpress.line.me/fx/img/review_gold_star_28.png'
        greeting = f'Welcome {display_name}!' if display_name else 'Welcome'
        
        line_bot_api.reply_message_with_http_info(
            ReplyMessageRequest(
                reply_token=event.reply_token,
                messages=[
                    ImageMessage(original_content_url=picture_url, preview_image_url=picture_url),
                    TextMessage(text=greeting)
                ]
            )
        )

        # add user
        data = {
            'user_id': event.source.user_id,
            'follow': strftime('%Y%m%d%H%M%S'),
            'count': 0
        }
        
        firestore_client.collection('pyla').add(
            document_id=event.source.user_id,
            document_data=data
        )
        
    
    
if __name__ == "__main__":
    app.run()