import requests

URLS = ['https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0003-001',
        'https://opendata.cwa.gov.tw/api/v1/rest/datastore/O-A0001-001']


_sitemaps = {}


def _load_sitemaps(key):
    sitemaps = {}
    
    params = {'Authorization': key}

    for url in URLS:
        r = requests.get(url, params=params)
        for s in r.json()['records']['Station']:
            sitemaps[s['StationName']] = url
    print('sitemaps built')

    return sitemaps

def cwa2(site, key):
    global _sitemaps

    if not _sitemaps:
        _sitemaps = _load_sitemaps(key)

    url = _sitemaps.get(site)
    if url:
        return _cwa(url, site, key)
    return {}

def cwa(site, key):
    # info = _cwa(URL[0], site, key)
    # if info:
    #     return info
    # return _cwa(URL[1], site, key)

    #return _cwa(URL[0], site, key) or _cwa(URL[1], site, key)

    for url in URLS:
        info = _cwa(url, site, key)
        if info:
            return info
    return {}

def _cwa(url, site, key):
    params = {'Authorization': key,
              'StationName': site
             }
    try:
        r = requests.get(url, params=params)
    except Exception as e:
        print(e)
        return {}

    if r.status_code != 200:
        print(r.text)
        return {}

    if not r.json()['records']['Station']:
        return {}

    raw = r.json()['records']['Station'][0]
    s = raw['StationName']
    o = raw['ObsTime']['DateTime'].replace('+08:00', '')
    c = (float(raw['GeoInfo']['Coordinates'][1]['StationLatitude']),
         float(raw['GeoInfo']['Coordinates'][1]['StationLongitude']))
    _r = float(raw['WeatherElement']['Now']['Precipitation'])
    t = float(raw['WeatherElement']['AirTemperature'])
    h = float(raw['WeatherElement']['RelativeHumidity']) / 100
    
    return {'S': s, 'O': o, 'C': c, 'R': _r, 'T': t, 'H': h}