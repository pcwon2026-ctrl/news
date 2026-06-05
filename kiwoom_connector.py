# -*- coding: utf-8 -*-
"""
한국정치경제신문 · 키움 API 연결 모듈 (v2)
────────────────────────────────────────────────
종목 시세 + 업종 지수(KOSPI, KOSDAQ 등) 조회 지원.

실행 환경:
    py -3.13-32   (반드시 32비트)
    PyQt5 필수
"""
import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QAxContainer import QAxWidget
from PyQt5.QtCore import QEventLoop


class KiwoomAPI:
    """키움 OpenAPI+ 연결 클래스."""

    def __init__(self):
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.ocx = QAxWidget("KHOPENAPI.KHOpenAPICtrl.1")
        self.ocx.OnEventConnect.connect(self._on_login)
        self.ocx.OnReceiveTrData.connect(self._on_receive_tr)

        self.login_loop = None
        self.tr_loop = None
        self.stock_data = {}        # 종목 시세
        self.index_data = {}        # 지수 시세
        self._last_index_code = None  # 응답 매칭용

    # ──────────────────────────────────
    # 로그인
    # ──────────────────────────────────
    def login(self):
        print("키움 서버에 로그인 시도 중...")
        self.ocx.dynamicCall("CommConnect()")
        self.login_loop = QEventLoop()
        self.login_loop.exec_()

    def _on_login(self, err_code):
        if err_code == 0:
            print("[OK] 키움 서버 로그인 성공")
        else:
            print(f"[X] 로그인 실패 (코드 {err_code})")
        if self.login_loop:
            self.login_loop.exit()

    # ──────────────────────────────────
    # 종목 시세 (기존)
    # ──────────────────────────────────
    def get_current_price(self, code):
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "종목코드", code)
        self.ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            "주식기본정보", "opt10001", 0, "0101"
        )
        self.tr_loop = QEventLoop()
        self.tr_loop.exec_()
        return self.stock_data.get(code, None)

    # ──────────────────────────────────
    # 업종 지수 조회 (신규)
    # ──────────────────────────────────
    def get_index_price(self, index_code):
        """
        업종 지수 조회.

        index_code:
            "001" = KOSPI
            "101" = KOSDAQ
            "201" = KOSPI200
        """
        self._last_index_code = index_code
        self.ocx.dynamicCall("SetInputValue(QString, QString)", "업종코드", index_code)
        self.ocx.dynamicCall(
            "CommRqData(QString, QString, int, QString)",
            "업종현재가", "opt20001", 0, "0102"
        )
        self.tr_loop = QEventLoop()
        self.tr_loop.exec_()
        return self.index_data.get(index_code, None)

    # ──────────────────────────────────
    # TR 응답 콜백
    # ──────────────────────────────────
    def _on_receive_tr(self, screen_no, rq_name, tr_code, record_name, prev_next):

        def get(field):
            return self.ocx.dynamicCall(
                "GetCommData(QString, QString, int, QString)",
                tr_code, rq_name, 0, field
            ).strip()

        if rq_name == "주식기본정보":
            code = get("종목코드")
            name = get("종목명")
            price = get("현재가")
            change_rate = get("등락율")

            try:
                price_num = abs(int(price))
            except ValueError:
                price_num = 0

            self.stock_data[code] = {
                "name": name,
                "price": price_num,
                "change_rate": float(change_rate) if change_rate else 0.0,
            }

        elif rq_name == "업종현재가":
            current = get("현재가")
            change = get("전일대비")
            sign = get("전일대비기호")  # 2=상승, 3=보합, 5=하락 등

            # 현재가: 부호 떼고 절댓값. 예) "-1176.93" → 1176.93
            try:
                price_val = abs(float(current.replace('+', '').replace('-', '').strip()))
            except (ValueError, AttributeError):
                price_val = 0.0

            # 전일대비: 부호 보존된 포인트 변화. 예) "-2.36"
            try:
                change_val = float(change) if change else 0.0
            except ValueError:
                change_val = 0.0

            # 등락률 직접 계산: (전일대비 / 전일종가) × 100
            #   전일종가 = 현재가 - 전일대비
            if price_val > 0 and change_val != 0:
                prev_close = price_val - change_val
                rate_val = (change_val / prev_close) * 100 if prev_close != 0 else 0.0
            else:
                rate_val = 0.0

            # 전일대비기호로 부호 보정 (5 = 하락이므로 음수)
            if sign in ("4", "5") and rate_val > 0:
                rate_val = -rate_val

            if self._last_index_code:
                self.index_data[self._last_index_code] = {
                    "price": price_val,
                    "change_rate": rate_val,
                }

        if self.tr_loop:
            self.tr_loop.exit()


# ──────────────────────────────────
# 단독 실행 테스트
# ──────────────────────────────────
if __name__ == "__main__":
    print("=" * 50)
    print("키움 API 테스트 - 종목 + 지수")
    print("=" * 50)

    kw = KiwoomAPI()
    kw.login()

    print("\n[종목] 삼성전자(005930)")
    r = kw.get_current_price("005930")
    if r:
        print(f"   {r['name']}  {r['price']:,}원  ({r['change_rate']:+.2f}%)")

    print("\n[지수] KOSPI (001)")
    r = kw.get_index_price("001")
    if r:
        print(f"   현재가 {r['price']:,.2f}  ({r['change_rate']:+.2f}%)")

    print("\n[지수] KOSDAQ (101)")
    r = kw.get_index_price("101")
    if r:
        print(f"   현재가 {r['price']:,.2f}  ({r['change_rate']:+.2f}%)")

    print("\n테스트 완료.")
