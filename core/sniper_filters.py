"""Binary V16 operational filters: candle rejection, marubozu, EMA cascade and M5 confirmation."""
import math
import pandas as pd


def _ema(s, n):
    return s.ewm(span=n, adjust=False).mean()


def evaluate(candles, m5_candles=None, payout=None, otc=False):
    df = pd.DataFrame(candles).copy()
    for c in ["open", "high", "low", "close", "volume"]:
        df[c] = pd.to_numeric(df[c], errors="coerce")
    df = df.dropna(subset=["open", "high", "low", "close"]).reset_index(drop=True)
    result = {"veto": False, "reasons": [], "warnings": [], "force": 0, "m5_confirmation": 0,
              "ema": {}, "candle": {}, "payout": payout, "otc": bool(otc)}
    if len(df) < 200:
        result["veto"] = True; result["reasons"].append("DADOS_INSUFICIENTES_EMA_200"); return result

    last = df.iloc[-1]
    body = abs(last.close-last.open); rng = max(last.high-last.low, 1e-12)
    upper = last.high-max(last.open,last.close); lower = min(last.open,last.close)-last.low
    body_ratio = body/rng
    marubozu = body_ratio >= 0.90 and upper/rng <= .05 and lower/rng <= .05
    rejection = max(upper, lower)/rng >= (.35 if otc else .40)
    opposite = (last.close < last.open) or (last.close > last.open)
    result["candle"] = {"body_ratio": round(float(body_ratio),4), "upper_wick_ratio": round(float(upper/rng),4),
                         "lower_wick_ratio": round(float(lower/rng),4), "rejection": bool(rejection), "marubozu": bool(marubozu)}
    if marubozu:
        result["veto"] = True; result["reasons"].append("VETO_MARUBOZU")
    if not rejection and not opposite:
        result["veto"] = True; result["reasons"].append("SEM_CONFIRMACAO_DE_VELA")

    close = df.close
    emas = {n: float(_ema(close,n).iloc[-1]) for n in [7,9,21,50,200]}
    result["ema"] = emas
    bullish = emas[7] > emas[9] > emas[21] > emas[50] > emas[200]
    bearish = emas[7] < emas[9] < emas[21] < emas[50] < emas[200]
    result["direction"] = "CALL" if bullish else ("PUT" if bearish else "NEUTRAL")
    result["force"] = int(bullish or bearish) + int(emas[7] > emas[21] if bullish else emas[7] < emas[21]) + int(emas[21] > emas[50] if bullish else emas[21] < emas[50]) + int((last.close > emas[7]) if bullish else (last.close < emas[7]))
    if result["force"] < 4:
        result["veto"] = True; result["reasons"].append(f"FORCA_INSUFICIENTE_{result['force']}_DE_4")

    if payout is not None:
        try:
            payout_n = float(payout)
            if payout_n > 1: payout_n /= 100
            if payout_n < .80:
                result["veto"] = True; result["reasons"].append("PAYOUT_ABAIXO_DE_80_PORCENTO")
        except (TypeError, ValueError):
            result["warnings"].append("PAYOUT_NAO_VALIDADO")
    else:
        result["warnings"].append("PAYOUT_NAO_INFORMADO")

    if m5_candles:
        m5 = pd.DataFrame(m5_candles).copy()
        for c in ["open","high","low","close"]: m5[c]=pd.to_numeric(m5[c], errors="coerce")
        m5=m5.dropna(subset=["close"])
        if len(m5) >= 50:
            m5c=m5.close; e21=float(_ema(m5c,21).iloc[-1]); e50=float(_ema(m5c,50).iloc[-1])
            m5dir = "CALL" if m5c.iloc[-1]>e21>e50 else ("PUT" if m5c.iloc[-1]<e21<e50 else "NEUTRAL")
            result["m5_confirmation"] = 5 if m5dir == result["direction"] and m5dir != "NEUTRAL" else 0
            result["m5_direction"] = m5dir
            if result["m5_confirmation"] < 5:
                result["veto"] = True; result["reasons"].append("M5_SEM_CONFIRMACAO_5_DE_5")
        else: result["warnings"].append("M5_INSUFICIENTE")
    else: result["warnings"].append("M5_NAO_INFORMADO")
    result["decision"] = "BLOQUEADO" if result["veto"] else "VALIDAR_COM_SCORE"
    return result
