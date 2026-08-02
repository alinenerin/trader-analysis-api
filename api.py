import os
from flask import Flask, jsonify, request
import pandas as pd

app = Flask(__name__)
EXECUTOR_ENABLED = False


def health_payload():
    return {
        "status": "ok",
        "service": "trader-analysis-api",
        "mode": "analysis-only",
        "executor_enabled": EXECUTOR_ENABLED,
        "binary_pipeline": "v16-supreme-stage-1",
    }


@app.get('/health')
def health():
    return jsonify(health_payload())


@app.get('/')
def root():
    return jsonify(health_payload())


def _json_safe(value):
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    if hasattr(value, 'item'):
        return _json_safe(value.item())
    if hasattr(value, 'isoformat'):
        return value.isoformat()
    return value


def scan_binary():
    body = request.get_json(silent=True) or {}
    candles = body.get('candles')
    symbol = str(body.get('symbol') or 'EURUSD').upper().replace('/', '')
    required = {'open', 'high', 'low', 'close', 'volume'}

    if not isinstance(candles, list) or len(candles) < 1000:
        return jsonify({
            'status': 'ok', 'type': 'binarias', 'decision': 'AGUARDAR',
            'score': 0, 'executor_enabled': False,
            'reason': 'O V16 Supreme precisa de pelo menos 1000 candles OHLCV para treinar o Anomaly Shield sem inventar dados.',
            'required_candles': 1000,
        })
    if not all(isinstance(c, dict) and required.issubset(c) for c in candles):
        return jsonify({
            'status': 'ok', 'type': 'binarias', 'decision': 'AGUARDAR',
            'score': 0, 'executor_enabled': False,
            'reason': 'Cada candle deve conter open, high, low, close e volume.',
        })

    try:
        from core.supreme_intelligence import SupremeIntelligence
        from core.sniper_filters import evaluate as evaluate_sniper_filters
        from core.news_shield_v2 import NewsShieldV2
        frame = pd.DataFrame(candles)
        for col in required:
            frame[col] = pd.to_numeric(frame[col], errors='coerce')
        frame = frame.dropna(subset=list(required)).reset_index(drop=True)
        if len(frame) < 1000:
            return jsonify({'status': 'ok', 'type': 'binarias', 'decision': 'AGUARDAR', 'score': 0,
                            'executor_enabled': False, 'reason': 'Candles OHLCV inválidos ou insuficientes após validação.'})
        result = SupremeIntelligence(symbol=symbol).get_full_analysis(frame)
        filters = evaluate_sniper_filters(
            candles, body.get('m5_candles'), body.get('payout'),
            symbol.endswith('-OTC') or bool(body.get('otc', False))
        )
        news_ok, news_reason, news_details = NewsShieldV2().validate(symbol, filters.get('direction', 'NEUTRAL'))
        result['news_shield'] = {'approved': news_ok, 'reason': news_reason, 'details': news_details}
        result['sniper_filters'] = filters
        result['type'] = 'binarias'
        result['executor_enabled'] = False
        if filters.get('veto') or not news_ok:
            result['decision'] = 'BLOQUEADO'
            result['veto'] = True
            reasons = list(filters.get('reasons', []))
            if not news_ok: reasons.append(news_reason)
            result['veto_reason'] = '; '.join(reasons)
        else:
            result['decision'] = 'VALIDADO' if result.get('score', 0) >= 90 else 'AGUARDAR'
        return jsonify(_json_safe(result))
    except Exception:
        app.logger.exception('binary analysis failed')
        return jsonify({'status': 'ok', 'type': 'binarias', 'decision': 'AGUARDAR', 'score': 0,
                        'executor_enabled': False, 'reason': 'Pipeline V16 em validação; nenhum sinal foi liberado.'})


@app.post('/api/binarias/scan')
def binarias():
    return scan_binary()


@app.post('/api/forex/scan')
def forex_not_enabled():
    return jsonify({'status': 'ok', 'type': 'forex', 'decision': 'AGUARDAR', 'score': 0,
                    'executor_enabled': False, 'reason': 'Integração Forex permanece na fase anterior.'})


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', '8080')))
