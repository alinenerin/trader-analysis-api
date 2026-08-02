"""News veto for Binary V16. Analysis only; no order execution."""
import os
from datetime import datetime, timedelta, timezone
import requests

class NewsShieldV2:
    def __init__(self, window_minutes=30):
        self.window_minutes = int(window_minutes)
        self.calendar_url = os.getenv('FF_CALENDAR_URL', 'https://nfs.faireconomy.media/ff_calendar_thisweek.json')
        self.marketaux_url = 'https://api.marketaux.com/v1/news/all'
        self.marketaux_token = os.getenv('MARKETAUX_API_TOKEN', '')

    def _parse_time(self, value):
        if not value: return None
        try:
            return datetime.fromisoformat(str(value).replace('Z', '+00:00')).astimezone(timezone.utc)
        except Exception:
            return None

    def check(self, currencies, now=None):
        now = now or datetime.now(timezone.utc)
        try:
            data = requests.get(self.calendar_url, timeout=8).json()
            relevant=[]
            for event in data if isinstance(data, list) else []:
                impact=str(event.get('impact','')).lower()
                currency=str(event.get('country', event.get('currency',''))).upper()
                when=self._parse_time(event.get('date', event.get('datetime')))
                if impact in ('high','red') and when and currency in {str(x).upper() for x in currencies}:
                    if when-timedelta(minutes=self.window_minutes) <= now <= when+timedelta(minutes=self.window_minutes):
                        relevant.append({'currency':currency,'title':event.get('title','High impact event'),'time':when.isoformat()})
            if relevant:
                return {'veto':True,'status':'HIGH_IMPACT_WINDOW','source':'ForexFactory','events':relevant}
            return {'veto':False,'status':'CLEAR','source':'ForexFactory','events':[]}
        except Exception as exc:
            return {'veto':False,'status':'UNAVAILABLE','source':'ForexFactory','events':[], 'warning':'Calendário indisponível; confirmação manual necessária.'}

    def sentiment(self, symbol):
        if not self.marketaux_token:
            return {'status':'NOT_CONFIGURED','score':50,'news_count':0}
        pair=str(symbol).replace('/','').replace('-OTC','').upper()
        symbols=pair[:3]+','+pair[3:6]
        try:
            data=requests.get(self.marketaux_url, params={'symbols':symbols,'filter_entities':'true','language':'en','limit':5,'api_token':self.marketaux_token}, timeout=8).json()
            vals=[]
            for article in data.get('data',[]):
                for entity in article.get('entities',[]):
                    if entity.get('symbol','').upper() in symbols.split(',') and entity.get('sentiment_score') is not None:
                        vals.append(float(entity['sentiment_score']))
            avg=sum(vals)/len(vals) if vals else 0
            return {'status':'OK','score':round((avg+1)*50,1),'news_count':len(vals),'average':round(avg,4)}
        except Exception:
            return {'status':'UNAVAILABLE','score':50,'news_count':0}

    def validate(self, symbol, direction):
        currencies=[str(symbol).replace('/','')[:3],str(symbol).replace('/','')[3:6]]
        result=self.check(currencies)
        if result['veto']: return False, 'VETO_NOTICIA_ALTO_IMPACTO', result
        sent=self.sentiment(symbol)
        score=sent.get('score',50)
        if direction == 'CALL' and score < 30: return False, 'VETO_SENTIMENTO_CONTRARIO', {'calendar':result,'sentiment':sent}
        if direction == 'PUT' and score > 70: return False, 'VETO_SENTIMENTO_CONTRARIO', {'calendar':result,'sentiment':sent}
        return True, 'NEWS_OK' if result['status']=='CLEAR' else 'NEWS_UNAVAILABLE_MANUAL_CHECK', {'calendar':result,'sentiment':sent}
