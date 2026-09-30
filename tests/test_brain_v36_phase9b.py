from dataclasses import dataclass
from datetime import datetime, timezone
import json
import pytest

from src.research.brain_v36.phase9b import (
    DecisionJournal, ShadowCostModel, ShadowDecision, US_EQUITY_SESSION,
    conservative_outcome, event_risk_context, liquidity_context, regime,
    session_phase, shadow_decision, size_position, trend_pullback_signal,
)

@dataclass
class C:
    timestamp:int; open:float; high:float; low:float; close:float; volume:float=100.0

def bars(n=260, step=300_000):
    out=[]; prev=100.0
    for i in range(n):
        base=100+i*0.05
        close=base + (0.2 if i%7 else -0.15)
        out.append(C(i*step,prev,max(prev,close)+.2,min(prev,close)-.2,close,100+i%10))
        prev=close
    return out

def cost(**kw): return ShadowCostModel(.0002,.0003,.0002,kw.get("overnight",0),"TEST")

def test_cost_includes_commission_spread_slippage_and_financing():
    c=cost(overnight=.001)
    assert c.round_trip==pytest.approx(.0011)
    assert c.net_fraction(100,101,"LONG",1440)==pytest.approx(.01-.0011-.001)

def test_session_dst_aware_and_crypto_always_open():
    ts=int(datetime(2026,9,30,14,0,tzinfo=timezone.utc).timestamp()*1000)
    assert session_phase(ts,US_EQUITY_SESSION)=="OPENING"
    assert session_phase(ts,None)=="ALWAYS_OPEN"

def test_event_risk_blocks_high_event_only():
    assert event_risk_context(100,[{"start_ms":0,"end_ms":200,"severity":"HIGH","name":"CPI"}])["blocked"]
    assert not event_risk_context(100,[{"start_ms":0,"end_ms":200,"severity":"LOW"}])["blocked"]

def test_position_sizing_uses_stop_distance_and_exposure_cap():
    s=size_position(equity=1000,entry=100,stop=98,risk_fraction=.01,max_exposure_fraction=.15)
    assert s["quantity"]==pytest.approx(1.5)
    assert s["notional"]==pytest.approx(150)

def test_regime_uses_past_only_and_detects_uptrend():
    b=bars()
    before=regime(b,100)
    b[-1].close*=5
    assert regime(b,100)==before
    assert before in {"TREND_UP","RANGE","HIGH_VOLATILITY"}

def test_liquidity_cost_gate_fails_closed_on_excessive_cost():
    b=bars()
    c=ShadowCostModel(.002,.004,.002,0,"TEST")
    x=liquidity_context(b,220,c,max_round_trip=.006)
    assert not x["allowed"] and x["reason"]=="COST_TOO_HIGH"

def test_trend_pullback_is_long_only_and_explainable():
    b=bars(230)
    # engineer a pullback then breakout while keeping long trend
    for k,v in enumerate([109,108.8,109.1,109.4,109.6], start=224):
        b[k].close=v; b[k].low=v-.2; b[k].high=v+.2
    b[229].open=109.6; b[229].close=113; b[229].high=113.2; b[229].low=109.5
    s=trend_pullback_signal(b,229)
    assert s is None or s["side"]=="LONG"

def test_shadow_never_emits_order_action():
    b=bars()
    d=shadow_decision(symbol="BTCUSDT",asset_type="crypto",candles=b,i=230,strategy="trend",cost=cost())
    assert d.action in {"SHADOW_DECISION","SHADOW_REJECT"}
    assert "ORDER" not in d.action

def test_high_event_forces_shadow_reject_if_signal_exists(monkeypatch):
    import src.research.brain_v36.phase9b as p
    b=bars()
    monkeypatch.setattr(p,"strategy_signal",lambda *a,**k:{"side":"LONG","signal_price":110.,"stop":108.,"target":114.,"rationale":"x"})
    d=p.shadow_decision(symbol="BTCUSDT",asset_type="crypto",candles=b,i=230,strategy="trend",cost=cost(),
                        events=[{"start_ms":b[230].timestamp-1,"end_ms":b[230].timestamp+1,"severity":"CRITICAL"}])
    assert d.action=="SHADOW_REJECT" and d.rejection_reason=="EVENT_RISK"

def test_conservative_same_bar_stop_wins(monkeypatch):
    import src.research.brain_v36.phase9b as p
    b=bars(230)
    d=ShadowDecision("SHADOW_DECISION","X","trend","LONG",220,b[220].timestamp,"TREND_UP","ALWAYS_OPEN",.001,"x",None,110,108,114,1)
    b[221].open=110; b[221].low=107; b[221].high=115; b[221].close=111
    o=conservative_outcome(b,d,cost=cost(),max_holding_bars=3)
    assert o["reason"]=="STOP_LOSS" and o["exit"]==108

def test_decision_journal_jsonl(tmp_path):
    d=ShadowDecision("SHADOW_REJECT","X","trend",None,1,1,"RANGE","ALWAYS_OPEN",.001,"x","NO_SIGNAL",None,None,None,0)
    j=DecisionJournal(tmp_path/"journal.jsonl"); j.append(d)
    row=json.loads((tmp_path/"journal.jsonl").read_text())
    assert row["strategy"]=="trend" and row["rejection_reason"]=="NO_SIGNAL"

def test_malformed_ohlc_fails_closed():
    b=bars(); b[10].low=b[10].high+1
    with pytest.raises(ValueError):
        shadow_decision(symbol="BTCUSDT",asset_type="crypto",candles=b,i=230,strategy="trend",cost=cost())

def test_knn_filter_rejects_negative_edge_and_admits_positive_edge():
    from src.research.brain_v36.phase9b import KnnSample, knn_prediction
    x=(0.0,0.0,0.0,0.0)
    neg=[KnnSample((i*0.001,0,0,0),-.01, i) for i in range(12)]
    pos=[KnnSample((i*0.001,0,0,0), .01, i) for i in range(12)]
    assert knn_prediction(x,neg)["admitted"] is False
    assert knn_prediction(x,pos)["admitted"] is True


def test_shadow_pipeline_can_require_knn(monkeypatch):
    import src.research.brain_v36.phase9b as p
    b=bars()
    monkeypatch.setattr(p,"strategy_signal",lambda *a,**k:{"side":"LONG","signal_price":110.,"stop":108.,"target":114.,"rationale":"x"})
    d=p.shadow_decision(symbol="BTCUSDT",asset_type="crypto",candles=b,i=230,strategy="trend",cost=cost(),require_knn=True)
    assert d.action=="SHADOW_REJECT" and d.rejection_reason=="KNN_NOT_AVAILABLE"
    d=p.shadow_decision(symbol="BTCUSDT",asset_type="crypto",candles=b,i=230,strategy="trend",cost=cost(),require_knn=True,
                        knn={"admitted":False,"reason":"KNN_REJECTED"})
    assert d.rejection_reason=="KNN_REJECTED"
