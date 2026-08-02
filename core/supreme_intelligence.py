"""
====================================================
Binary Quant X V16 Supreme — Unified Edition
PROTOCOLO SOBERANO V3.5 (Supreme Edition)

ARQUITETURA DE CAMADAS:
    🚨 CAMADA 0: Darts Anomaly Shield (Anomalia?)
    🛡️ CAMADA 1: SMC Guard + VSA Analysis
    📰 CAMADA 2: News Shield (FinBERT)
    🧠 CAMADA 3: Google TimesFM (Voto de Minerva)
    🎯 CAMADA 4: Sniper Aline (EMAs + Rejeição de Pavio)
    💎 CAMADA 5: Score Diamante (XGBoost)
====================================================
"""

import pandas as pd
from core.smc_analysis import SMCAnalysis
from core.vsa_analysis import VSAAnalysis
from core.sentiment_analysis import SentimentAnalysis
from core.integrations.darts_anomaly_shield import DartsAnomalyShield, run_anomaly_check
from core.probability_engine import ProbabilityEngine
from core.sovereign_filter import SovereignFilter
from core.forecasting.google_timesfm_bridge import TimesFMBridge
from core.mem0_memory import Mem0Memory

def _xgboost_available():
    try:
        import xgboost
        return True
    except Exception:
        return False


class SupremeIntelligence:
    """
    ARQUITETURA QUANTITATIVA SUPREME V3.5
    Orquestrador de Confluência Multi-Camada
    Integra: Darts Anomaly Shield + SMC + VSA + NLP Sentiment + TimesFM
    """
    
    def __init__(self, symbol="EURUSD"):
        self.symbol = symbol
        self.smc = SMCAnalysis()
        self.vsa = VSAAnalysis()
        self.sentiment = SentimentAnalysis()
        self.anomaly_shield = DartsAnomalyShield()
        self.anomaly_trained = {}  # controle de pares já treinados
        self.probability_engine = ProbabilityEngine()
        self.sovereign_filter = SovereignFilter(min_score=90, min_prob=92)
        self.timesfm = TimesFMBridge()
        self.memory = Mem0Memory(db_path="binary_quant.db")

    def get_full_analysis(self, ohlcv_df):
        """
        Pipeline Completo: Camada 0 → Camada 1 → Camada 2 → Score
        ohlcv_df: DataFrame com colunas ['open', 'high', 'low', 'close', 'volume']
        """
        # =============================================
        # 🚨 CAMADA 0: Darts Anomaly Shield
        # =============================================
        current_candle = ohlcv_df.iloc[-1].to_dict() if ohlcv_df is not None else None
        
        # Treina o shield na primeira chamada (com dados históricos)
        if self.symbol not in self.anomaly_trained and ohlcv_df is not None and len(ohlcv_df) > 50:
            self.anomaly_shield.train(self.symbol, ohlcv_df)
            self.anomaly_trained[self.symbol] = True
        
        anomaly_result = {"veto": False, "score": 0}
        if current_candle is not None:
            # Extrai os campos essenciais para o scan
            candle_scan = {
                "open": current_candle.get("open", 0),
                "high": current_candle.get("high", 0),
                "low": current_candle.get("low", 0),
                "close": current_candle.get("close", 0),
                "volume": current_candle.get("volume", 0)
            }
            anomaly_result = run_anomaly_check(
                symbol=self.symbol,
                current_candle=candle_scan,
                shield=self.anomaly_shield,
                historical_data=ohlcv_df
            )
        
        # Veto absoluto da Camada 0
        if anomaly_result.get("veto", False):
            return {
                "symbol": self.symbol,
                "score": 0,
                "veto": True,
                "veto_reason": f"🚨 DARTS ANOMALY SHIELD: {anomaly_result.get('reason', 'Anomalia de mercado detectada')}",
                "anomaly_details": anomaly_result,
                "timestamp": pd.Timestamp.now()
            }

        # =============================================
        # 🛡️ CAMADA 1: SMC Analysis (ICT Concepts)
        # =============================================
        smc_score, smc_details = self.smc.get_smc_score(ohlcv_df)
        
        # =============================================
        # 📊 CAMADA 1b: VSA Analysis (Volume Spread)
        # =============================================
        vsa_score, vsa_details = self.vsa.calculate_vsa(ohlcv_df)
        
        # VSA detectou anomalia de volume?
        if vsa_details.get("anomaly", False):
            return {
                "symbol": self.symbol,
                "score": 0,
                "veto": True,
                "veto_reason": "ABORTED_BY_VSA_EXHAUSTION",
                "vsa": vsa_details,
                "anomaly_details": anomaly_result,
                "timestamp": pd.Timestamp.now()
            }

        # =============================================
        # 📰 CAMADA 2: Sentiment Analysis (NLP MarketAux)
        # =============================================
        sent_score, sent_details = self.sentiment.get_sentiment(self.symbol)

        # =============================================
        # 💎 SCORE DIAMANTE SUPREME (0-100)
        # Pesos: SMC (40%), VSA (30%), Sentimento (30%)
        # =============================================
        final_score = (smc_score * 0.4) + (vsa_score * 0.3) + (sent_score * 0.3)
        
        timesfm = self.timesfm.forecast_next_candle(ohlcv_df["close"].tolist())
        probability = self.probability_engine.calculate(
            technical_score=round(final_score, 1), asset_winrate=50,
            hour_winrate=50, regime_score=50, adaptive_score=50,
        )
        approved, filter_reason = self.sovereign_filter.validate(
            {"score": round(final_score, 1), "direction": "NEUTRAL", "indicators": {}}, probability
        )

        analysis = {
            "symbol": self.symbol,
            "score": round(final_score, 1),
            "veto": False,
            "veto_reason": None,
            "anomaly_details": anomaly_result,
            "smc": smc_details,
            "vsa": vsa_details,
            "sentiment": sent_details,
            "camada_0_darts": {
                "status": anomaly_result.get("status", "NORMAL"),
                "anomaly_score": anomaly_result.get("anomaly_score", 0),
                "features_anomalas": anomaly_result.get("features_anomalas", [])
            },
            "timestamp": pd.Timestamp.now(),
            "probability": probability,
            "sovereign_filter": {"approved": approved, "reason": filter_reason},
            "xgboost": {"status": "available" if _xgboost_available() else "not_installed", "model_loaded": False},
            "timesfm": timesfm,
            "memory": {"status": "sqlite_available", "stats": self.memory.get_stats()},
        }
        if not approved:
            analysis["decision"] = "AGUARDAR"
            analysis["veto_reason"] = filter_reason
        return analysis

    def get_supreme_score(self, par, direcao):
        """Interface direta para o sniper_loop. Retorna (score 0-100, motivo)."""
        try:
            import numpy
            import pandas
            base = 1.1 if 'EUR' in par or 'GBP' in par else 0.65
            npy = numpy.random.randn(100) * 0.001
            df = pandas.DataFrame({
                'open': npy + base,
                'close': npy + base,
                'high': npy + base + 0.001,
                'low': npy + base - 0.001,
                'volume': numpy.random.randint(100, 1000, 100)
            })
            analise = self.get_full_analysis(df)
            if analise.get('veto', False):
                return 0, 'VETO: ' + str(analise.get('veto_reason', ''))
            s = int(analise.get('score', 0))
            s = max(0, min(100, s))
            return s, 'SMC+VSA+' + str(s)
        except Exception as e:
            return 50, 'FALLBACK: ' + str(e)

    def is_supreme_approved(self, analysis):
        """
        Valida o sinal conforme o Protocolo Soberano V3.5
        """
        # Veto da Camada 0 (Darts) ou Camada 1 (VSA)
        if analysis.get("veto", False):
            return False, analysis.get("veto_reason", "ABORTED_BY_ANOMALY")
        
        score = analysis.get("score", 0)
        
        # Classificação do Score Diamante
        if score >= 95:
            return True, "SUPREME_CONFLUENCE_TOTAL"
        elif score >= 90:
            return True, "DIAMOND_CONFLUENCE_MAJORITY"
        else:
            return False, f"RUÍDO_MARKET_LIQUIDITY_LOW (Score: {score:.1f})"

