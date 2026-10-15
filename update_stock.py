import json
import datetime
import os
import sys
import time
from zoneinfo import ZoneInfo

import requests

# 使用台灣時區，避免 GitHub Actions 的 UTC 日期造成日期錯誤
today = datetime.datetime.now(
    ZoneInfo("Asia/Taipei")
).date()

date_str = today.strftime("%Y%m%d")
display_date = today.strftime("%Y-%m-%d")

# 正確的證交所 T86 三大法人買賣超日報 API
url = "https://www.twse.com.tw/rwd/zh/fund/T86"

params = {
    "date": date_str,
    "selectType": "ALL",
    "response": "json"
}

headers = {
    "User-Agent": "Mozilla/5.0",
    "Accept": "application/json, text/plain, */*",
    "Referer": "https://www.twse.com.tw/"
}

OUTPUT_FILE = "stock_data.json"


def to_int(value):
    """將 API 數值轉成整數，保留負數。"""
    if value is None:
        return 0

    value = str(value).strip()
    value = value.replace(",", "").replace("+", "")

    if value in ("", "-", "--", "—", "－"):
        return 0

    try:
        return int(value)
    except ValueError:
        try:
            return int(float(value))
        except (ValueError, OverflowError):
            return 0


def load_old_data():
    """讀取既有資料，供失敗時保留原檔使用。"""
    if not os.path.exists(OUTPUT_FILE):
        return None

    try:
        with open(OUTPUT_FILE, "r", encoding="utf-8") as f:
            obj = json.load(f)

        if isinstance(obj, dict) and isinstance(obj.get("data"), list):
            return obj
    except (OSError, json.JSONDecodeError) as e:
        print(f"讀取舊資料失敗：{e}")

    return None


def fetch_stock_data():
    print(f"正在抓取證交所三大法人資料：{display_date}")
    print(f"API：{url}")

    response = requests.get(
        url,
        params=params,
        headers=headers,
        timeout=30
    )

    print(f"HTTP 狀態碼：{response.status_code}")
    response.raise_for_status()

    # 避免空回應或 HTML 錯誤頁面被當成 JSON
    text = response.text.strip()

    if not text:
        raise ValueError("API 回傳空內容")

    try:
        result = response.json()
    except requests.exceptions.JSONDecodeError as e:
        print("API 回傳內容不是有效 JSON。")
        print(f"回應前 300 字：{text[:300]!r}")
        raise ValueError("無法解析證交所 API 回應") from e

    if not isinstance(result, dict):
        raise ValueError("API 回傳格式不符合預期")

    print(f"證交所回應狀態：{result.get('stat', '未知')}")

    # 非交易日或查無資料時，不要覆蓋舊檔
    if result.get("stat") != "OK":
        raise ValueError(
            f"證交所沒有提供有效資料：{result.get('stat', '未知原因')}"
        )

    rows = result.get("data")

    if not isinstance(rows, list) or not rows:
        raise ValueError("API 沒有回傳股票資料列")

    print(f"取得原始資料：{len(rows)} 筆")

    stock_list = []

    for row in rows:
        try:
            # T86 回傳每筆資料是陣列，不是字典
            if not isinstance(row, (list, tuple)) or len(row) < 12:
                continue

            code = str(row[0]).strip()
            name = str(row[1]).strip()

            # 只保留四碼上市股票代號
            if not (code.isdigit() and len(code) == 4):
                continue

            if not name:
                continue

            # 官方 T86 欄位位置：
            # [4] 外陸資買賣超股數（不含外資自營商）
            # [10] 投信買賣超股數
            # [11] 自營商買賣超股數（合計）
            foreign = to_int(row[4])
            trust = to_int(row[10])
            dealer = to_int(row[11])

            stock_list.append({
                "code": code,
                "name": name,
                "foreign": foreign,
                "trust": trust,
                "self": dealer
            })

        except (ValueError, TypeError, IndexError) as e:
            print(f"略過格式異常的資料列：{e}")
            continue

    if not stock_list:
        raise ValueError("API 有回應，但沒有解析出有效股票資料")

    return stock_list


def main():
    old_data = load_old_data()

    try:
        # 最多嘗試 3 次，降低暫時性連線問題的影響
        stock_list = None

        for attempt in range(1, 4):
            try:
                stock_list = fetch_stock_data()
                break
            except (
                requests.RequestException,
                ValueError,
                TypeError
            ) as e:
                print(f"第 {attempt}/3 次抓取失敗：{e}")

                if attempt < 3:
                    wait_seconds = attempt * 5
                    print(f"{wait_seconds} 秒後重試...")
                    time.sleep(wait_seconds)

        if not stock_list:
            print("❌ 無法取得有效資料，保留原有 stock_data.json。")

            if old_data is not None:
                print(f"舊資料日期：{old_data.get('date', '未知')}")
                print(f"舊資料筆數：{len(old_data.get('data', []))}")

            # 讓 GitHub Actions 明確顯示失敗
            sys.exit(1)

        output = {
            "date": display_date,
            "data": stock_list
        }

        # 先寫入暫存檔，成功後才取代正式檔案
        temp_file = OUTPUT_FILE + ".tmp"

        with open(temp_file, "w", encoding="utf-8") as f:
            json.dump(output, f, ensure_ascii=False, indent=4)
            f.write("\n")

        os.replace(temp_file, OUTPUT_FILE)

        print("✅ 股票資料更新成功")
        print(f"資料日期：{display_date}")
        print(f"有效股票筆數：{len(stock_list)}")
        print(f"已寫入：{OUTPUT_FILE}")

        # 顯示幾筆資料，方便檢查
        for item in stock_list[:5]:
            print(
                f"{item['code']} {item['name']} | "
                f"外資：{item['foreign']:,} | "
                f"投信：{item['trust']:,} | "
                f"自營商：{item['self']:,}"
            )

    except Exception as e:
        print(f"❌ 更新程序發生錯誤：{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
