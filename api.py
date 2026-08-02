import os
from flask import Flask, jsonify, request
app=Flask(__name__)

@app.get('/health')
def health():
    return jsonify(status='ok', service='trader-analysis-api', mode='analysis-only', executor_enabled=False)

@app.get('/')
def root():
    return jsonify(service='trader-analysis-api', status='online', executor_enabled=False)

def scan(kind):
    body=request.get_json(silent=True) or {}
    candles=body.get('candles')
    if not isinstance(candles,list) or len(candles)<20:
        return jsonify(status='ok', type=kind, decision='AGUARDAR', score=0, executor_enabled=False, reason='API online; envie ao menos 20 candles OHLCV para análise.')
    required={'open','high','low','close','volume'}
    if not all(isinstance(c,dict) and required.issubset(c) for c in candles):
        return jsonify(status='ok', type=kind, decision='AGUARDAR', score=0, executor_enabled=False, reason='Candles devem conter open, high, low, close e volume.')
    return jsonify(status='ok', type=kind, decision='AGUARDAR', score=0, executor_enabled=False, reason='Pipeline técnico será habilitado após validação do serviço.')

@app.post('/api/forex/scan')
def forex(): return scan('forex')
@app.post('/api/binarias/scan')
def binarias(): return scan('binarias')

if __name__=='__main__': app.run(host='0.0.0.0',port=int(os.getenv('PORT','8080')))
