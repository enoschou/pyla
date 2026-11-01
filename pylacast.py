import json

from linebot.v3.messaging import (
    Configuration,
    ApiClient,
    MessagingApi,
    PushMessageRequest,
    MulticastRequest,
    BroadcastRequest,
    TextMessage
)

from google.cloud import firestore


try:
    with open('env.json', encoding='utf-8') as f:
        env = json.load(f)
except Exception as e:
    print(e, flush=True)
    env = {}

configuration = Configuration(access_token=env.get('CHANNEL_ACCESS_TOKEN', ''))
firestore_client = firestore.Client.from_service_account_json(env.get('GOOGLE_CLOUD_SERVICE', ''))

with ApiClient(configuration) as api_client:
    line_bot_api = MessagingApi(api_client)

    # 篩選出符合資格的用戶，count > 10
    users = firestore_client.collection('pyla').where(filter=firestore.FieldFilter('count', '>', 1)).stream()
    to = [u.to_dict()['user_id'] for u in users]

    # 一致性推送 messages
    #messages = [TextMessage(text='You are VIP users')]
    #line_bot_api.multicast(MulticastRequest(messages=messages, to=to))

    # 因人而異推送
    for user_id in to:
        name = dict(line_bot_api.get_profile(user_id=user_id)).get('display_name', '尊貴的用戶')
        messages = [TextMessage(text=f'Hello {name}, you are VIP')]
        line_bot_api.push_message(PushMessageRequest(messages=messages, to=user_id))
        print(f'sent to {name} done')