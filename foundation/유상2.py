# -*- coding: utf-8 -*-
import sys, time
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QTimer

SCREEN_INFO = "9001"   # opt10001(기본정보, 시총)
SCREEN_BRKR = "9101"   # opt10002(거래원)
RQNAME_INFO = "basic_info_req"
RQNAME_BRKR = "opt10002_req"

def to_int(s: str) -> int:
    if s is None: return 0
    s = s.replace(',', '').replace('+', '').replace('-', '').strip()
    try: return int(s or "0")
    except: return 0

class KiwoomTop50Brokers:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._on_login)
        self.ocx.OnReceiveTrData.connect(self._on_tr)

        # 상태 저장
        self.kospi_codes = []          # 코스피 코드 전체
        self.cap_queue = []            # 시총 조회할 코드 큐
        self.cap_results = {}          # {code: market_cap}
        self.sorted_top50 = []         # [(code, cap)]
        self.brkr_queue = []           # 거래원 조회할 코드 큐

        # 안전장치
        self.req_busy = False          # TR 진행 중 플래그
        self.timer = QTimer()
        self.timer.timeout.connect(self._pump)  # 주기적으로 다음 작업 실행

        # 로그인
        self.ocx.dynamicCall("CommConnect()")
        self.app.exec_()

    # ================= 로그인 =================
    def _on_login(self, err_code):
        if err_code != 0:
            print("로그인 실패")
            self.app.quit(); return
        print("로그인 성공")

        # 1) 코스피 전체 코드 가져오기 ("0"=코스피, "10"=코스닥)
        codes_str = self.ocx.dynamicCall("GetCodeListByMarket(QString)", "0")
        self.kospi_codes = [c for c in codes_str.split(';') if c]
        print(f"코스피 종목 수: {len(self.kospi_codes)}")

        # 2) 시가총액 조회 큐 세팅(전체 코스피 대상)
        self.cap_queue = list(self.kospi_codes)

        # 3) 타이머 시작: 300ms 간격으로 TR 작업 펌핑
        self.timer.start(300)

    # ================= 작업 루프 =================
    def _pump(self):
        """
        - 먼저 opt10001(기본정보)로 시가총액 수집 완료할 때까지 진행
        - 완료되면 상위 50 선별 후 opt10002(거래원) 순차 호출
        """
        if self.req_busy:
            return

        # 아직 시총을 다 못 모았으면 opt10001부터
        if self.cap_queue:
            code = self.cap_queue.pop(0)
            self._rq_basic_info(code)
            return

        # 시총 수집이 끝났고, 아직 top50을 안 뽑았다면 선별
        if not self.sorted_top50:
            if not self.cap_results:
                print("시가총액 결과가 비어 있습니다. 잠시 후 재시도.")
                return
            # 시총 상위 50 선별
            self.sorted_top50 = sorted(self.cap_results.items(),
                                       key=lambda x: x[1], reverse=True)[:50]
            # 거래원 큐 구성
            self.brkr_queue = [code for code, _ in self.sorted_top50]
            print("\n=== 코스피 시가총액 상위 50 종목 ===")
            for rank, (code, cap) in enumerate(self.sorted_top50, 1):
                name = self.ocx.dynamicCall("GetMasterCodeName(QString)", code)
                print(f"{rank:2d}. {code} {name} - 시총: {cap:,}원")
            print("====================================\n")
            return

        # 거래원 큐 진행
        if self.brkr_queue:
            code = self.brkr_queue.pop(0)
            self._rq_broker_rank(code)
            return

        # 모든 작업 완료
        print("\n작업 완료")
        self.timer.stop()
        self.app.quit()

    # ================= TR 요청 =================
    def _rq_basic_info(self, code):
        """opt10001: 주식기본정보요청 → '시가총액' 파싱"""
        self.req_busy = True
        self.curr_info_code = code
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             RQNAME_INFO, "opt10001", 0, SCREEN_INFO)

    def _rq_broker_rank(self, code):
        """opt10002: 주식거래원요청 → 매수/매도 거래원 상위 출력"""
        self.req_busy = True
        self.curr_brkr_code = code
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             RQNAME_BRKR, "opt10002", 0, SCREEN_BRKR)

    # ================= 수신 핸들러 =================
    def _on_tr(self, screen_no, rqname, trcode, recordname, prev_next,
               data_len, error_code, message, splm_msg):
        try:
            if rqname == RQNAME_INFO:
                # opt10001 응답: 시가총액
                mcap_str = self._get(trcode, rqname, 0, "시가총액")
                mcap = to_int(mcap_str)
                self.cap_results[self.curr_info_code] = mcap
                # 진행률 가끔 보여주기
                if len(self.cap_results) % 100 == 0:
                    print(f"시총 수집: {len(self.cap_results)} / {len(self.kospi_codes)}")
                self.req_busy = False

            elif rqname == RQNAME_BRKR:
                code = self.curr_brkr_code
                name = self.ocx.dynamicCall("GetMasterCodeName(QString)", code)
                print(f"\n[{code} {name}] 거래원 상위 5")

                print("[매도 상위]")
                for i in range(1, 6):
                    s_name = self._get(trcode, rqname, 0, f"매도거래원명{i}")
                    s_vol  = self._get(trcode, rqname, 0, f"매도거래량{i}")
                    if s_name:
                        print(f"{i}위: {s_name} - 거래량: {s_vol}")

                print("[매수 상위]")
                for i in range(1, 6):
                    b_name = self._get(trcode, rqname, 0, f"매수거래원명{i}")
                    b_vol  = self._get(trcode, rqname, 0, f"매수거래량{i}")
                    if b_name:
                        print(f"{i}위: {b_name} - 거래량: {b_vol}")

                self.req_busy = False

            else:
                # 다른 RQ가 들어오면 그냥 플래그만 해제
                self.req_busy = False

        except Exception as e:
            print("에러:", e)
            self.req_busy = False

    # ================= 유틸 =================
    def _get(self, trcode, rqname, idx, field):
        return self.ocx.dynamicCall(
            "GetCommData(QString, QString, int, QString)",
            trcode, rqname, idx, field
        ).strip()

if __name__ == "__main__":
    KiwoomTop50Brokers()
