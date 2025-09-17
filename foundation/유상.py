# -*- coding: utf-8 -*-
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QTimer

class Kiwoom:
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self.login_slot)
        self.ocx.OnReceiveTrData.connect(self.receive_tr_data)
        self._printed = False  # 중복 출력 방지

        self.ocx.dynamicCall("CommConnect()")  # 로그인창
        self.app.exec_()

    def login_slot(self, err_code):
        if err_code == 0:
            print("로그인 성공")
            # 로그인 직후 약간의 여유를 두고 TR 호출
            QTimer.singleShot(300, lambda: self.request_broker_rank("005930"))  # 삼성전자
        else:
            print("로그인 실패")

    def request_broker_rank(self, code):
        # ★ 거래원 상위: opt10002 사용 (입력값: 종목코드만 필요)
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall("CommRqData(QString, QString, int, QString)",
                             "opt10002_req", "opt10002", 0, "0101")

    def receive_tr_data(self, screen_no, rqname, trcode, recordname, prev_next,
                        data_len, error_code, message, splm_msg):
        if rqname == "opt10002_req" and not self._printed:
            self._printed = True

            print("\n[매도 거래원 상위 5]")
            for i in range(1, 6):
                name = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    trcode, rqname, 0, f"매도거래원명{i}").strip()
                vol = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    trcode, rqname, 0, f"매도거래량{i}").strip()
                if name:  # 비어있으면 생략
                    print(f"{i}위: {name} - 거래량: {vol}")

            print("\n[매수 거래원 상위 5]")
            for i in range(1, 6):
                name = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    trcode, rqname, 0, f"매수거래원명{i}").strip()
                vol = self.ocx.dynamicCall(
                    "GetCommData(QString, QString, int, QString)",
                    trcode, rqname, 0, f"매수거래량{i}").strip()
                if name:
                    print(f"{i}위: {name} - 거래량: {vol}")

            self.app.quit()

if __name__ == "__main__":
    Kiwoom()

