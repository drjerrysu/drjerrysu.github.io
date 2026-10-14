
"""
台股每日收盤選股資料系統
資料來源：TWSE OpenAPI、TWSE T86、TPEx OpenAPI
輸出：data/latest.json、data/history.csv、data/run.log

安裝：
    python -m pip install requests pandas

注意：
    1. TWSE 與 TPEx 分開下載及檢查。
    2. 若 TPEx 欄位與預期不同，程式會報錯，不會猜測欄位。
    3. 第一次執行只建立當日歷史；累積交易日後才有完整均線。
"""

import json
import logging
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

import pandas as pd
import requests

TZ = timezone(timedelta(hours=8))
BASE = Path("data")
BASE.mkdir(exist_ok=True)

TWSE_API = "https://openapi.twse.com.tw/v1"
TWSE_T86 = "https://www.twse.com.tw/rwd/zh/fund/T86"
TPEX_API = "https://www.tpex.org.tw/openapi/v1"

# TPEx 端點如有調整，請以官方 OpenAPI 文件為準。
TPEX_QUOTES = f"{TPEX_API}/tpex_mainboard_daily_close_quotes"

logging.basicConfig(
    filename=BASE / "run.log",
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    encoding="utf-8",
)

session = requests.Session()
session.headers.update({
    "User-Agent": "TaiwanStockDailyResearch/1.0",
    "Accept": "application/json",
})


def get_json(url, params=None, retries=3):
    """有逾時、重試及 HTTP 狀態檢查的 JSON 下載。"""
    last_error = None

    for attempt in range(retries):
        try:
            response = session.get(
                url, params=params, timeout=(10, 30)
            )
            response.raise_for_status()
            return response.json()
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            logging.warning(
                "下載失敗，第 %s 次：%s；%s",
                attempt + 1, url, exc
            )
            if attempt + 1 < retries:
                time.sleep(2 ** attempt)

    raise RuntimeError(f"下載失敗：{url}；{last_error}")


def number(value):
    """保留缺漏值為 None，避免將缺漏誤當成 0。"""
    if value is None:
        return None

    s = str(value).strip().replace(",", "").replace("+", "")

    if s in ("", "--", "-", "N/A", "null", "None"):
        return None

    try:
        return float(s)
    except (TypeError, ValueError):
        return None


def required_field(row, *names):
    """精確比對欄位名稱，找不到就明確報錯。"""
    for name in names:
        if name in row:
            return row[name]

    raise KeyError(
        f"找不到欄位 {names}；實際欄位為 {list(row.keys())}"
    )


def optional_field(row, *names):
    for name in names:
        if name in row:
            return row[name]
    return None


def get_twse_quotes():
    url = f"{TWSE_API}/exchangeReport/STOCK_DAY_ALL"
    rows = get_json(url)

    if not isinstance(rows, list) or not rows:
        raise RuntimeError("TWSE 每日成交資訊為空或格式異常")

    result = []

    for r in rows:
        code = str(required_field(r, "證券代號")).strip()
        name = str(required_field(r, "證券名稱")).strip()

        # 排除非一般股票代號格式以外的資料時，請自行調整規則。
        if not code or not name:
            continue

        result.append({
            "market": "上市",
            "code": code,
            "name": name,
            "open": number(required_field(r, "開盤價")),
            "high": number(required_field(r, "最高價")),
            "low": number(required_field(r, "最低價")),
            "close": number(required_field(r, "收盤價")),
            "volume_shares": number(required_field(r, "成交股數")),
            "trading_value": number(required_field(r, "成交金額")),
            "transactions": number(required_field(r, "成交筆數")),
        })

    if not result:
        raise RuntimeError("TWSE 沒有可用行情資料")

    return result


def get_tpex_quotes():
    """
    TPEx 公開 API 欄位可能與 TWSE 不同。
    本函式刻意採用欄位別名清單，無法識別時停止而非猜值。
    """
    rows = get_json(TPEX_QUOTES)

    if not isinstance(rows, list) or not rows:
        raise RuntimeError(
            "TPEx 行情為空或格式異常；請檢查官方 API 端點"
        )

    result = []

    for r in rows:
        code = str(required_field(
            r, "SecuritiesCompanyCode", "SecuritiesCode",
            "Code", "證券代號"
        )).strip()

        name = str(required_field(
            r, "CompanyName", "CompanyAbbreviation",
            "Name", "證券名稱"
        )).strip()

        result.append({
            "market": "上櫃",
            "code": code,
            "name": name,
            "open": number(required_field(r, "Open", "OpeningPrice", "開盤")),
            "high": number(required_field(r, "High", "HighestPrice", "最高")),
            "low": number(required_field(r, "Low", "LowestPrice", "最低")),
            "close": number(required_field(r, "Close", "ClosingPrice", "收盤")),
            "volume_shares": number(required_field(
                r, "TradingShares", "TradingVolume",
                "TradingVolumeShares", "成交股數"
            )),
            "trading_value": number(required_field(
                r, "TransactionAmount", "TradingValue", "成交金額"
            )),
            "transactions": number(optional_field(
                r, "TransactionNumber", "Transactions", "成交筆數"
            )),
        })

    if not result:
        raise RuntimeError("TPEx 沒有可用行情資料")

    return result


def get_twse_valuation():
    url = f"{TWSE_API}/exchangeReport/BWIBBU_ALL"
    rows = get_json(url)

    if not isinstance(rows, list) or not rows:
        raise RuntimeError("TWSE 估值資料為空或格式異常")

    result = {}

    for r in rows:
        code = str(required_field(r, "Code")).strip()

        # Date 為民國年日期，例如 1151013。
        roc_date = str(optional_field(r, "Date") or "").strip()

        result[code] = {
            "valuation_date_roc": roc_date or None,
            "pe": number(optional_field(r, "PEratio")),
            "dividend_yield_pct": number(
                optional_field(r, "DividendYield")
            ),
            "pb": number(optional_field(r, "PBratio")),
        }

    return result


def get_twse_institutional(trade_date):
    """T86 欄位使用正式名稱，不用固定數字索引。"""
    date_str = trade_date.strftime("%Y%m%d")

    payload = get_json(
        TWSE_T86,
        params={
            "response": "json",
            "date": date_str,
            "selectType": "ALL",
        },
    )

    if payload.get("stat") != "OK":
        raise RuntimeError(
            "T86 尚無有效資料或 API 回傳異常："
            + str(payload.get("stat"))
        )

    fields = payload.get("fields", [])
    rows = payload.get("data", [])

    if not fields or not rows:
        raise RuntimeError("T86 欄位或資料為空")

    result = {}

    for row in rows:
        if len(row) != len(fields):
            logging.warning("略過欄位數不一致的 T86 資料列")
            continue

        r = dict(zip(fields, row))
        code = str(required_field(r, "證券代號")).strip()

        result[code] = {
            "foreign_net_shares": number(required_field(
                r, "外陸資買賣超股數(不含外資自營商)"
            )),
            "trust_net_shares": number(
                required_field(r, "投信買賣超股數")
            ),
            "dealer_net_shares": number(
                required_field(r, "自營商買賣超股數")
            ),
            "all_institutional_net_shares": number(
                required_field(r, "三大法人買賣超股數")
            ),
        }

    if not result:
        raise RuntimeError("T86 沒有可用法人資料")

    return result


def main():
    now = datetime.now(TZ)
    trade_date = now.date()
    fetched_at = now.isoformat(timespec="seconds")

    logging.info("開始執行；抓取時間=%s", fetched_at)

    # 任一必要資料來源失敗時，不產生新的 latest.json。
    quotes = get_twse_quotes()
    time.sleep(1)

    tpex_quotes = get_tpex_quotes()
    time.sleep(1)

    valuation = get_twse_valuation()
    time.sleep(1)

    institutional = get_twse_institutional(trade_date)

    all_quotes = quotes + tpex_quotes
    seen = set()

    for row in all_quotes:
        key = (row["market"], row["code"])

        if key in seen:
            raise RuntimeError(f"重複股票資料：{key}")

        seen.add(key)

        row["trade_date"] = trade_date.isoformat()
        row["fetched_at"] = fetched_at
        row["source"] = (
            "TWSE OpenAPI" if row["market"] == "上市"
            else "TPEx OpenAPI"
        )

        if row["market"] == "上市":
            row.update(valuation.get(row["code"], {
                "valuation_date_roc": None,
                "pe": None,
                "dividend_yield_pct": None,
                "pb": None,
            }))
            row.update(institutional.get(row["code"], {
                "foreign_net_shares": None,
                "trust_net_shares": None,
                "dealer_net_shares": None,
                "all_institutional_net_shares": None,
            }))
        else:
            # 不把上市市場的估值或法人資料套到上櫃股票。
            row.update({
                "valuation_date_roc": None,
                "pe": None,
                "dividend_yield_pct": None,
                "pb": None,
                "foreign_net_shares": None,
                "trust_net_shares": None,
                "dealer_net_shares": None,
                "all_institutional_net_shares": None,
            })

    df = pd.DataFrame(all_quotes)

    # 核心行情欄位不能全部為空。
    if df.empty or df["close"].notna().sum() == 0:
        raise RuntimeError("沒有有效收盤價，拒絕輸出")

    # 當日來源資料快照：保留原始數字，方便追查。
    daily_file = BASE / f"quotes_{trade_date.isoformat()}.csv"
    df.to_csv(daily_file, index=False, encoding="utf-8-sig")

    # 歷史檔以市場、代號、日期去重。
    history_file = BASE / "history.csv"

    if history_file.exists():
        history = pd.read_csv(
            history_file, dtype={"code": str}
        )
        history["code"] = history["code"].astype(str)
        history = history[
            ~(
                (history["trade_date"] == trade_date.isoformat())
                & history["code"].isin(df["code"].astype(str))
                & history["market"].isin(df["market"])
            )
        ]
        history = pd.concat([history, df], ignore_index=True)
    else:
        history = df.copy()

    history["code"] = history["code"].astype(str)
    history["trade_date"] = pd.to_datetime(history["trade_date"])
    history = history.sort_values(
        ["market", "code", "trade_date"]
    )

    group = history.groupby(["market", "code"], sort=False)

    history["ma5"] = group["close"].transform(
        lambda s: s.rolling(5, min_periods=5).mean()
    )
    history["ma20"] = group["close"].transform(
        lambda s: s.rolling(20, min_periods=20).mean()
    )
    history["ma60"] = group["close"].transform(
        lambda s: s.rolling(60, min_periods=60).mean()
    )
    history["return_20d_pct"] = group["close"].transform(
        lambda s: s.pct_change(20) * 100
    )

    history.to_csv(
        history_file, index=False, encoding="utf-8-sig"
    )

    # 僅當資料來源下載及基本驗證成功，才更新 latest.json。
    latest = {
        "trade_date": trade_date.isoformat(),
        "fetched_at": fetched_at,
        "row_count": len(df),
        "markets": sorted(df["market"].unique().tolist()),
        "data": df.where(pd.notna(df), None).to_dict(
            orient="records"
        ),
    }

    temp_file = BASE / "latest.tmp"
    with open(temp_file, "w", encoding="utf-8") as f:
        json.dump(latest, f, ensure_ascii=False, indent=2, default=str)

    temp_file.replace(BASE / "latest.json")

    logging.info(
        "成功；上市=%s，上櫃=%s，總筆數=%s",
        len(quotes), len(tpex_quotes), len(df)
    )
    print("更新成功")
    print("抓取時間：", fetched_at)
    print("上市股票：", len(quotes))
    print("上櫃股票：", len(tpex_quotes))
    print("總筆數：", len(df))
    print("當日快照：", daily_file)
    print("歷史資料：", history_file)
    print("最新資料：", BASE / "latest.json")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        logging.exception("本次更新失敗")
        print("更新失敗：", exc)
        print("請檢查 data/run.log；不要把舊資料當成最新資料。")
        raise
