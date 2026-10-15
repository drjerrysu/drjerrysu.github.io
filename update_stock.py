import json
import datetime
import os
import time
import sys
from zoneinfo import ZoneInfo

import requests


# =========================
# 基本設定
# =========================

OUTPUT_FILE = "stock_data.json"

TODAY = datetime.datetime.now(
    ZoneInfo("Asia/Taipei")
).date()

DATE_TEXT = TODAY.strftime("%Y-%m-%d")
API_DATE = TODAY.strftime("%Y%m%d")

API_URL = "https://www.twse.com.tw/rwd/zh/fund/T86"

HEADERS = {
    "User-Agent": "Mozilla/5.0 (compatible; StockDataBot/1.0)",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.twse.com.tw/"
}


# =========================
# 數值轉換
# =========================

def to_int(value):
    """安全轉換證交所回傳的股數。"""

    if value is None:
        return 0

    text = str(value).strip()
    text = text.replace(",", "").replace("+", "")

    if text in ("", "-", "--", "—", "－"):
        return 0

    try:
        return int(text)
    except (ValueError, TypeError):
        raise ValueError(f"無法解析股數：{value!r}")


# =========================
# 讀取舊資料
# =========================

def load_old_data():
    """只讀取舊資料，不在抓取失敗時覆蓋它。"""

    if not os.path.exists(OUTPUT_FILE):
        return None

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as file:
            result = json.load(file)

        if (
            isinstance(result, dict)
            and isinstance(result.get("data"), list)
        ):
            return result

    except (OSError, json.JSONDecodeError) as error:
        print(f"讀取舊資料失敗：{error}")

    return None


# =========================
# 抓取證交所資料
# =========================

def fetch_stock_data():
    params = {
        "date": API_DATE,
        "selectType": "ALL",
        "response": "json"
    }

    print(f"資料日期：{DATE_TEXT}")
    print(f"API 網址：{API_URL}")
    print(f"查詢參數：{params}")

    response = requests.get(
        API_URL,
        params=params,
        headers=HEADERS,
        timeout=30
    )

    print(f"HTTP 狀態碼：{response.status_code}")
    response.raise_for_status()

    body = response.text.strip()

    if not body:
        raise ValueError("證交所回傳空白內容")

    try:
        result = response.json()
    except ValueError as error:
        print(f"回應內容前 500 字：{body[:500]!r}")
        raise ValueError("證交所回應不是有效 JSON") from error

    if not isinstance(result, dict):
        raise ValueError("API 回傳格式不是 JSON 物件")

    status = result.get("stat", "")
    print(f"證交所回應狀態：{status}")

    if status != "OK":
        raise ValueError(
            f"證交所未提供有效資料：{status or '沒有狀態訊息'}"
        )

    fields = result.get("fields", [])
    rows = result.get("data", [])

    if not isinstance(fields, list):
        raise ValueError("API 欄位定義格式錯誤")

    if not isinstance(rows, list) or len(rows) == 0:
        raise ValueError(
            "API 沒有股票資料，可能是非交易日或資料尚未公布"
        )

    # 透過欄位名稱定位資料，不完全依賴固定位置
    print(f"欄位數量：{len(fields)}")
    print(f"原始資料筆數：{len(rows)}")

    def find_field(*keywords):
        for index, field in enumerate(fields):
            normalized = (
                str(field)
                .replace(" ", "")
                .replace("\u3000", "")
            )

            if all(word in normalized for word in keywords):
                return index

        return None

    code_index = find_field("證券代號")
    name_index = find_field("證券名稱")

    # 使用買賣超欄位，而非買進或賣出股數
    foreign_index = find_field(
        "外陸資買賣超股數(不含外資自營商)"
    )

    trust_index = find_field("投信買賣超股數")
    dealer_index = find_field("自營商買賣超股數")

    # 欄位名稱如有變動，印出實際欄位供除錯
    indexes = {
        "code": code_index,
        "name": name_index,
        "foreign": foreign_index,
        "trust": trust_index,
        "dealer": dealer_index
    }

    print(f"欄位對應：{indexes}")

    missing = [
        key for key, value in indexes.items()
        if value is None
    ]

    if missing:
        print("API 實際欄位：")
        for index, field in enumerate(fields):
            print(f"  [{index}] {field}")

        raise ValueError(
            f"找不到必要欄位：{', '.join(missing)}"
        )

    stock_list = []
    skipped = 0

    for row in rows:
        try:
            if not isinstance(row, (list, tuple)):
                skipped += 1
                continue

            required_indexes = [
                code_index,
                name_index,
                foreign_index,
                trust_index,
                dealer_index
            ]

            if max(required_indexes) >= len(row):
                skipped += 1
                continue

            code = str(row[code_index]).strip()
            name = str(row[name_index]).strip()

            # 只收四碼上市股票代號
            if not (code.isdigit() and len(code) == 4):
                skipped += 1
                continue

            if not name:
                skipped += 1
                continue

            stock_list.append({
                "code": code,
                "name": name,
                "foreign": to_int(row[foreign_index]),
                "trust": to_int(row[trust_index]),
                "self": to_int(row[dealer_index])
            })

        except (ValueError, TypeError, IndexError) as error:
            skipped += 1
            print(f"略過異常資料列：{error}")

    print(f"有效股票筆數：{len(stock_list)}")
    print(f"略過資料筆數：{skipped}")

    if not stock_list:
        raise ValueError("解析完成，但沒有有效的四碼上市股票")

    return stock_list


# =========================
# 更新 JSON
# =========================

def save_data(stock_list):
    output = {
        "date": DATE_TEXT,
        "data": stock_list
    }

    temp_file = OUTPUT_FILE + ".tmp"

    try:
        with open(temp_file, "w", encoding="utf-8") as file:
            json.dump(
                output,
                file,
                ensure_ascii=False,
                indent=4
            )
            file.write("\n")

        # 寫入成功後才取代原始檔案
        os.replace(temp_file, OUTPUT_FILE)

    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)


# =========================
# 主程式
# =========================

def main():
    old_data = load_old_data()

    for attempt in range(1, 4):
        try:
            print(f"\n===== 第 {attempt}/3 次抓取 =====")

            stock_list = fetch_stock_data()

            save_data(stock_list)

            print("\n✅ 股票資料更新成功")
            print(f"資料日期：{DATE_TEXT}")
            print(f"更新筆數：{len(stock_list)}")
            print(f"輸出檔案：{OUTPUT_FILE}")

            for item in stock_list[:5]:
                print(
                    f"{item['code']} {item['name']} | "
                    f"外資：{item['foreign']:,} | "
                    f"投信：{item['trust']:,} | "
                    f"自營商：{item['self']:,}"
                )

            return

        except (
            requests.RequestException,
            ValueError,
            TypeError,
            OSError
        ) as error:
            print(f"❌ 本次抓取失敗：{error}")

            if attempt < 3:
                wait_seconds = attempt * 5
                print(f"{wait_seconds} 秒後重試")
                time.sleep(wait_seconds)

    print("\n❌ 三次嘗試均失敗，沒有覆蓋舊資料。")

    if old_data is not None:
        print(f"保留舊資料日期：{old_data.get('date', '未知')}")
        print(f"保留舊資料筆數：{len(old_data.get('data', []))}")
    else:
        print("目前沒有可保留的舊資料。")

    sys.exit(1)


if __name__ == "__main__":
    main()
