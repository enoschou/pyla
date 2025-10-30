'''real-time speech-to-text application'''

__version__ = '0.1.0'

# pip install google-cloud-speech pyaudio

import sys
import wave
from argparse import ArgumentParser
from io import BytesIO
from threading import Thread
from time import sleep
    
from google.cloud import speech
import pyaudio


def record(secs=None):
    CHUNK = 1024
    FORMAT = pyaudio.paInt16
    CHANNELS = 1 if sys.platform == 'darwin' else 2
    RATE = 44100
    
    def stop_recording():
        nonlocal stream

        input('ENTER to stop recording...')
        if stream and stream.is_active():
            stream.stop_stream()
    
    def countdown(secs):        
        nonlocal stream
        
        count = secs;
        print()
        while stream and stream.is_active() and count > 0:
            print(f'{count:2d} seconds left', end='\r')
            sleep(1)
            count -= 1
        if stream and stream.is_active():
            stream.stop_stream()
    
    arbitrary = (secs == None or secs <= 0) # arbitrary or fixed seconds
    
    p = pyaudio.PyAudio()
    stream = p.open(format=FORMAT, channels=CHANNELS, rate=RATE, input=True)
    if arbitrary:
        Thread(target=stop_recording).start()
    else:
        t1 = Thread(target=stop_recording, daemon=True)  # daemon mode, sys.exit() would cause t1 exit
        t1.start()
        Thread(target=countdown, args=(secs,)).start()

    bytesaudio = BytesIO()
    with wave.open(bytesaudio, 'wb') as wf:
        wf.setnchannels(CHANNELS)
        wf.setsampwidth(p.get_sample_size(FORMAT))
        wf.setframerate(RATE)
        while stream.is_active():
            wf.writeframes(stream.read(CHUNK, exception_on_overflow=False))

    stream.close()
    p.terminate()
    stream = None

    return bytesaudio.getvalue()

def transcript(bytesaudio, lang='zh-TW', service=None):
    if not bytesaudio:
        return 'not bytes audio'
    
    if not service:
        return 'no service'
    
    if not lang:
        lang = 'zh-TW'

    audio = speech.RecognitionAudio(content=bytesaudio)
    config = speech.RecognitionConfig(
        audio_channel_count=2,
        language_code=lang
    )
    try:
        speech_client = speech.SpeechClient.from_service_account_json(service)
    except Exception as e:
        print(e)
        return e.__class__.__name__
    response = speech_client.recognize(config=config, audio=audio)
    if (r1 := response.results) and (r2 := r1[0]) and (r3 := r2.alternatives):
        return max([(r.confidence, r.transcript) for r in r3])[1]
    return 'unrecognized'


parser = ArgumentParser()
parser.add_argument('-l', '--language', default='zh-TW', help='language, default zh-TW')
parser.add_argument('-s', '--seconds', type=int, help='seconds for recording, or arbitrary')
parser.add_argument('-k', '--service', default='gcpai.json',
                    help='key file of GCP service account, default gcpai.json')
args = parser.parse_args()

print(f'[yourturn-rstt-{__version__}]')
if args.seconds and args.seconds > 0:  # fixed
    print(f'recording for {args.seconds} seconds...')
else:  # arbitrary
    print('recording...')
bytesaudio = record(secs=args.seconds)
print('transcripting...')
r = transcript(bytesaudio=bytesaudio, lang=args.language, service=args.service)
print(r)

sys.exit()
