print(f'my __name__ is: {__name__}')


import requests


OBS_API = 'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001'


def get_weather(name: str, key: str) -> dict:
    '''get weather information from CWA, include temperature, ...
    name   - CWA station name
    key    - CWA API key
    return - weather info, ex: {'S': '牛頭山', 'I': 'C0SD40', 'O': '2026-10-04 14:00', 'T': 30.4, 'H': 0.73, 'R': 0.0}
           - {} for error  
    '''
    
    if not name or not isinstance(name, str):
        print('bad name!')
        return {}

    if not key or not isinstance(key, str):
        print('bad key!')
        return {}
    
    params = {'Authorization': key}

    try:
        r = requests.get(OBS_API, params=params)
        if r.status_code != 200:
            print(f'bad status: {r.text}')
            return {}

        for s in r.json()['records']['Station']:
            if s['StationName'] == name:
                info = {}
                info['S'] = name
                info['I'] = s['StationId']
                info['O'] = s['ObsTime']['DateTime'].replace(':00+08:00', '').replace('T', ' ')
                info['T'] = float(s['WeatherElement']['AirTemperature'])
                info['H'] = float(s['WeatherElement']['RelativeHumidity']) / 100
                info['R'] = float(s['WeatherElement']['Now']['Precipitation'])
                return info

    except Exception as e:
        print(e)

    return {}

if __name__ == '__main__':
    import argparse
    
    parser = argparse.ArgumentParser()
    parser.add_argument('name', help='station name of CWA')
    parser.add_argument('key', help='API key of CWA')
    args = parser.parse_args()
    
    print(get_weather(args.name, args.key))