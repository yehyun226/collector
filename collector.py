import os
import sys
import time
import datetime
import logging

# ===== 경로 설정 =====
sys.path.extend(['../..', '.'])
import kis_auth as ka  # KIS 인증 모듈

# ===== 로깅 설정 =====
logging.basicConfig(level=logging.INFO)

# ===== 종목코드 → 종목명 매핑 =====
ticker_name_map = {
    "373220": "LG에너지솔루션",
    "329180": "HD현대중공업",
    "034020": "두산에너빌리티",
    "042660": "한화오션",
    "035420": "NAVER",
    "035720": "카카오",
    "005490": "POSCO홀딩스",
    "064350": "현대로템",
    "010130": "고려아연",
    "096770": "SK이노베이션",
    "034730": "SK",
    "051910": "LG화학",
    "006400": "삼성SDI",
    "018260": "삼성에스디에스",
    "033780": "KT&G",
    "247540": "에코프로비엠",
    "272210": "한화시스템",
    "003490": "대한항공",
    "010120": "LS ELECTRIC",
    "004020": "현대제철",
    "036570": "엔씨소프트",
    "452260": "두산로보틱스",
    "010620": "HD현대미포",
    "326030": "SK바이오팜",
    "011070": "LG이노텍",
    "052690": "한전기술",
    "017800": "현대엘리베이터"
}

tickers = list(ticker_name_map.keys())

# ===== API 정보 =====
API_MEMBER_URL = "/uapi/domestic-stock/v1/quotations/inquire-member"
API_PRICE_URL  = "/uapi/domestic-stock/v1/quotations/inquire-price"

TR_ID_MEMBER   = "FHKST01010600"
TR_ID_PRICE    = "FHKST01010100"

BASE_PATH = "/Users/yehyun/Desktop/한국투자증권"

# ===== 이전 누적 거래량 저장 =====
prev_volume = {}

# ===== 유틸 함수 =====
def get_today_folder():
    today = datetime.datetime.now().strftime("%Y%m%d")
    folder = os.path.join(BASE_PATH, today)
    os.makedirs(folder, exist_ok=True)
    return folder

def save_txt(ticker, content):
    folder = get_today_folder()
    name = ticker_name_map.get(ticker, ticker)
    path = os.path.join(folder, f"{name}.txt")
    with open(path, 'a', encoding='utf-8') as f:
        f.write(content + "\n")

# ===== API 호출 함수 =====
def get_member_data(ticker):
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    res = ka._url_fetch(API_MEMBER_URL, TR_ID_MEMBER, "", params)
    if res.isOK():
        return res.getBody().get("output", {})
    else:
        logging.warning(f"[{ticker}] member API 실패: {res.getErrorMsg()}")
        return {}

def get_price_data(ticker):
    params = {"FID_COND_MRKT_DIV_CODE": "J", "FID_INPUT_ISCD": ticker}
    res = ka._url_fetch(API_PRICE_URL, TR_ID_PRICE, "", params)
    if res.isOK():
        body = res.getBody().get("output", {})
        return {
            "price": body.get("stck_prpr", "-"),            # 현재가
            "cumulative_volume": int(body.get("acml_vol", "0")),  # 누적 거래량
            "strength": body.get("prdy_vrss_vol_rt", "-")   # 체결강도 (%)
        }
    else:
        logging.warning(f"[{ticker}] price API 실패: {res.getErrorMsg()}")
        return {"price": "-", "cumulative_volume": 0, "strength": "-"}

# ===== 데이터 파싱 =====
def parse_member_top5(body):
    result_buy, result_sell = [], []
    total_buy, total_sell = 0, 0

    # 매도 TOP5
    for i in range(1, 6):
        name = body.get(f"seln_mbcr_name{i}", "")
        qty  = int(body.get(f"total_seln_qty{i}", "0"))
        if name:
            result_sell.append((name, qty))
            total_sell += qty

    # 매수 TOP5
    for i in range(1, 6):
        name = body.get(f"shnu_mbcr_name{i}", "")
        qty  = int(body.get(f"total_shnu_qty{i}", "0"))
        if name:
            result_buy.append((name, qty))
            total_buy += qty

    return result_buy, total_buy, result_sell, total_sell

# ===== 실행 함수 =====
def run_once():
    now = datetime.datetime.now().strftime("%H:%M:%S")

    for ticker in tickers:
        member_body = get_member_data(ticker)
        price_info  = get_price_data(ticker)

        if member_body:
            top5_buy, total_buy, top5_sell, total_sell = parse_member_top5(member_body)
        else:
            top5_buy, total_buy, top5_sell, total_sell = [], 0, [], 0

        # 주가/거래량/체결강도
        price    = price_info["price"]
        cum_vol  = price_info["cumulative_volume"]

        # === 체결강도 (API 값 + fallback 계산) ===
        strength = price_info["strength"]
        try:
            strength_val = float(strength)
            if strength_val < 1 or strength_val > 1000:  # 이상치 제거
                raise ValueError
        except:
            if total_sell > 0:
                strength = round((total_buy / total_sell) * 100, 2)
            else:
                strength = "-"

        # === 순간 거래량 ===
        prev_cum = prev_volume.get(ticker, cum_vol)
        inst_vol = max(cum_vol - prev_cum, 0)
        prev_volume[ticker] = cum_vol

        # 출력 포맷
        buy_str  = " / ".join([f"{i+1}. {n} {q}" for i, (n, q) in enumerate(top5_buy)])
        sell_str = " / ".join([f"{i+1}. {n} {q}" for i, (n, q) in enumerate(top5_sell)])

        content = f"[{now}] 종목: {ticker_name_map.get(ticker, ticker)}\n"
        content += f"주가: {price} / 거래량(순간): {inst_vol} / 거래량(누적): {cum_vol} / 체결강도: {strength}\n"
        content += f"매수상위: {buy_str}   (총합 {total_buy})\n"
        content += f"매도상위: {sell_str}   (총합 {total_sell})\n"
        content += "-" * 60

        save_txt(ticker, content)
        time.sleep(0.3)

def run_schedule():
    logging.info("자동 수집 시작")
    start = datetime.datetime.combine(datetime.date.today(), datetime.time(9, 0))
    end   = datetime.datetime.combine(datetime.date.today(), datetime.time(15, 30))

    while True:
        now = datetime.datetime.now()
        if start <= now <= end:
            run_once()
            time.sleep(60)  # 1분 간격
        elif now > end:
            logging.info("수집 종료 (장 마감)")
            break
        else:
            time.sleep(10)

# ===== 메인 실행 =====
if __name__ == "__main__":
    run_schedule()
