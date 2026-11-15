from google import genai
from google.oauth2 import service_account

_MODELS = {
    'gemini-3.5-flash-lite': 'minimal',
    'gemini-3.8-flash': 'low',
    'gemini-4-argon': 'low',
    'gemini-4-carbon': 'low',
    'gemini-4-hydrogen': 'low'
}

_CAR_SCHEMA = {
    "type": "object",
    "properties": {
        "plate": {"type": "string", "description": "車牌號碼，若找不到車牌此值為空字串"},
        "brand": {"type": "string", "description": "汽車品牌，若無法判斷此值為 N/A"},
        "color": {"type": "string", "description": "汽車顏色用英文表示，若無法判斷此值為 N/A"}
    },
    "required": ["plate", "brand", "color"]
}

def recognize_plate(
    image_bytes: bytes,
    model: str = 'gemini-3.5-flash-lite',
    service: str | None = None
) -> dict[str] | None:
    '''recoginze plate of image
    image_bytes - image to be recognized in bytes
    model
    service
    return      - plate, brand, color in dict for noraml, ex: {'plate': 'ABC-123', ...}
                - None for error
    '''
    if not image_bytes or not isinstance(image_bytes, bytes):
        print('bad image_bytes')
        return None
        
    if service and isinstance(service, str):
        try:
            # 處理金鑰
            credentials = service_account.Credentials.from_service_account_file(
                service,
                scopes=['https://www.googleapis.com/auth/cloud-platform']
            )
        
            # 初始化
            genai_client = genai.Client(
                enterprise=True,
                location='global',
                project=credentials.project_id,
                credentials=credentials
            )
        except Exception as e:
            print(e)
            return None
    else:
        print('bad service')
        return None
    
    # 準備內容
    contents = [
        {
            'role': 'user',
            'parts': [
                {'inline_data': {'data': image_bytes, 'mime_type': 'image/jpeg'}}
            ]
        }
    ]
    
    # 準備參數
    if model not in _MODELS:
        model = 'gemini-3.8-flash'
    
    config = {
        'max_output_tokens': 1000,
        'thinking_config': {'thinking_level': _MODELS[model]},
        'response_mime_type': 'application/json',
        'response_schema': _CAR_SCHEMA
    }
    
    # 執行 LLM
    try:
        r = genai_client.models.generate_content(
            model=model,
            contents=contents,
            config=config
        )
    except Exception as e:
        print(e)
        return None
    
    # 處理結果
    if r.candidates[0].finish_reason == 'STOP' and r.parsed:
        return r.parsed
    
    print(r.candidates[0].finish_reason)
    return None