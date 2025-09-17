# kis_auth.py

import requests
import json
import time

# 🔐 [1] 고객님의 앱키(App Key)와 앱시크릿(App Secret)을 아래에 입력하세요
APP_KEY = "PSywwbc0qAsXFl6Hk6a7NkLSWJ6UYa5tD53D"
APP_SECRET = "OlmevTAZUArqfrUZISp0zVvMiLsJaDX1dXsEJYq5hxu9I485SRi0Znue9OlhL6SFQ32LgRkO6ySOLW0PfhDpI/R0tjMsK98KINa1nscsNQsBrBXSqTQPtq8KdZ8xssp/p45anHw5Vv6Ucvv57Vt6TEKMrS4UllwU19jPwjxXo09hPCBFX54="

# 🔑 [2] 발급된 토큰을 캐시해두는 전역 변수
_token = None
_token_expire = 0

# 🔁 [3] 토큰 발급 함수: 자동으로 1시간마다 갱신
def _get_token():
    global _token, _token_expire

    # 이미 발급받은 토큰이 유효하다면 그대로 사용
    if _token and time.time() < _token_expire:
        return _token

    url = "https://openapi.koreainvestment.com:9443/oauth2/tokenP"
    headers = {"Content-Type": "application/json"}
    body = {
        "grant_type": "client_credentials",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET
    }

    res = requests.post(url, headers=headers, data=json.dumps(body))
    if res.status_code == 200:
        data = res.json()
        _token = data["access_token"]
        _token_expire = time.time() + int(data["expires_in"]) - 60  # 갱신 여유시간
        return _token
    else:
        raise Exception(f"[토큰 발급 실패] {res.status_code}: {res.text}")

# 🌐 [4] 실제로 API 호출하는 함수 (GET)
def _url_fetch(api_url, tr_id, cust_type, params):
    url = f"https://openapi.koreainvestment.com:9443{api_url}"
    headers = {
        "Content-Type": "application/json",
        "authorization": f"Bearer {_get_token()}",
        "appkey": APP_KEY,
        "appsecret": APP_SECRET,
        "tr_id": tr_id,
        "custtype": cust_type or "P"  # 개인: P / 법인: B
    }

    res = requests.get(url, headers=headers, params=params)

    class _Res:
        def __init__(self, res):
            self.res = res
        def isOK(self):
            return res.status_code == 200
        def getBody(self):
            return res.json()
        def printError(self, url=""):
            print(f"[API 오류] {url} - {res.status_code}: {res.text}")

    return _Res(res)
