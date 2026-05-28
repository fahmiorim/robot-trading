"""Live ticker / WebSocket widgets for the dashboard.

Two WS connections:
- Port 8767 — legacy ticker (price data only)
- Port 8765 — RPC WebSocket (account, status, positions, regime)
"""

# ── Compact live ticker bar (always visible at top) ──
_LIVE_WIDGET_HTML = r"""
<div style="background: linear-gradient(135deg, rgba(255,255,255,0.02), rgba(255,255,255,0.005)); border: 1px solid rgba(255,255,255,0.04); border-radius: 10px; padding: 0.3rem 0.8rem; margin-bottom: 0.5rem; display: flex; align-items: center; gap: 20px; font-size: 0.75rem; overflow: hidden;">
    <span class="live-dot red" style="flex-shrink:0;"></span>
    <span style="font-weight: 700; text-transform: uppercase; letter-spacing: 0.04em; font-size: 0.65rem; opacity: 0.5; flex-shrink:0;">LIVE</span>
    <span id="ticker-symbol" style="font-weight: 700; min-width: 60px;">—</span>
    <span id="ticker-bid" style="font-weight: 700; color: #2dd4bf; min-width: 80px;">—</span>
    <span id="ticker-ask" style="font-weight: 600; color: #f87171; min-width: 80px;">—</span>
    <span id="ticker-spread" style="opacity: 0.5; min-width: 50px;">—</span>
    <span id="ticker-change" style="min-width: 60px;">—</span>
</div>
<script>
(function(){
    let ws = null;
    let reconnectTimer = null;
    function connect(){
        try {
            ws = new WebSocket('ws://localhost:8767');
            ws.onmessage = function(e){
                try {
                    const d = JSON.parse(e.data);
                    document.getElementById('ticker-symbol').textContent = d.s || '\u2014';
                    document.getElementById('ticker-bid').textContent = d.b ? '$'+d.b.toFixed(5) : '\u2014';
                    document.getElementById('ticker-ask').textContent = d.a ? '$'+d.a.toFixed(5) : '\u2014';
                    document.getElementById('ticker-spread').textContent = d.spr ? d.spr.toFixed(1)+' pts' : '\u2014';
                    const chgEl = document.getElementById('ticker-change');
                    if(d.c !== undefined){
                        const sign = d.c >= 0 ? '+' : '';
                        chgEl.textContent = sign + d.c.toFixed(2) + '%';
                        chgEl.style.color = d.c >= 0 ? '#2dd4bf' : '#f87171';
                    }
                } catch(_){}
            };
            ws.onclose = function(){
                reconnectTimer = setTimeout(connect, 2000);
            };
        } catch(_){
            reconnectTimer = setTimeout(connect, 3000);
        }
    }
    if(typeof WebSocket !== 'undefined') connect();
})();
</script>
"""

# ── Real-time account/status strip (powered by WS RPC on port 8765) ──
REALTIME_DASHBOARD_HTML = r"""
<div id="realtime-dashboard" style="display:flex; gap:12px; flex-wrap:wrap; margin-bottom:0.5rem; background:rgba(255,255,255,0.02); border:1px solid rgba(255,255,255,0.04); border-radius:12px; padding:0.6rem 1rem; font-size:0.72rem; transition:opacity 0.3s;">
    <div style="display:flex; align-items:center; gap:6px;">
        <span style="opacity:0.4; font-size:0.6rem;">MT5</span>
        <span id="ws-mt5" style="font-size:0.85rem;">&ndash;</span>
    </div>
    <div class="vr" style="width:1px; background:rgba(255,255,255,0.06);"></div>
    <div><span style="opacity:0.4;">Balance</span> <strong id="ws-balance" style="color:#2dd4bf;">&ndash;</strong></div>
    <div><span style="opacity:0.4;">Equity</span> <strong id="ws-equity" style="color:#22c55e;">&ndash;</strong></div>
    <div><span style="opacity:0.4;">Margin</span> <strong id="ws-margin">&ndash;</strong></div>
    <div><span style="opacity:0.4;">Margin Lvl</span> <strong id="ws-margin-level">&ndash;</strong></div>
    <div class="vr" style="width:1px; background:rgba(255,255,255,0.06);"></div>
    <div><span style="opacity:0.4;">Regime</span> <strong id="ws-regime" style="font-weight:700;">&ndash;</strong></div>
    <div><span style="opacity:0.4;">Strategy</span> <strong id="ws-strategy">&ndash;</strong></div>
    <div><span style="opacity:0.4;">Positions</span> <strong id="ws-positions">&ndash;</strong></div>
</div>
<script>
(function(){
    var ws2 = null;
    var rtReconnect = null;
    function connectRT(){
        try {
            ws2 = new WebSocket('ws://localhost:8765');
            ws2.onmessage = function(e){
                try {
                    var d = JSON.parse(e.data);
                    if(d.account){
                        var el = document.getElementById('ws-balance');
                        if(el) el.textContent = d.account.balance ? '$'+Number(d.account.balance).toFixed(2) : '\u2014';
                        var el2 = document.getElementById('ws-equity');
                        if(el2) el2.textContent = d.account.equity ? '$'+Number(d.account.equity).toFixed(2) : '\u2014';
                        var el3 = document.getElementById('ws-margin');
                        if(el3) el3.textContent = d.account.free_margin ? '$'+Number(d.account.free_margin).toFixed(2) : '\u2014';
                        var el4 = document.getElementById('ws-margin-level');
                        if(el4) el4.textContent = d.account.margin_level ? Number(d.account.margin_level).toFixed(2)+'%' : '\u2014';
                    }
                    if(d.status){
                        var el = document.getElementById('ws-regime');
                        if(el){
                            el.textContent = d.status.regime || '\u2014';
                            var colors = {'TRENDING':'#22c55e','RANGING':'#f59e0b','CHOPPY':'#ef4444'};
                            el.style.color = colors[d.status.regime] || '#666';
                        }
                        var el2 = document.getElementById('ws-strategy');
                        if(el2) el2.textContent = d.status.best_strategy || '\u2014';
                        var el5 = document.getElementById('ws-mt5');
                        if(el5){
                            el5.textContent = d.status.mt5_connected ? '\u2705' : '\u274c';
                            el5.title = d.status.mt5_connected ? 'MT5 Connected' : 'MT5 Disconnected';
                        }
                    }
                    if(d.positions){
                        var el = document.getElementById('ws-positions');
                        if(el) el.textContent = d.positions.count != null ? d.positions.count : '0';
                    }
                } catch(_){}
            };
            ws2.onclose = function(){
                rtReconnect = setTimeout(connectRT, 2000);
            };
        } catch(_){
            rtReconnect = setTimeout(connectRT, 3000);
        }
    }
    if(typeof WebSocket !== 'undefined') connectRT();
})();
</script>
"""
