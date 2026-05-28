"""Live ticker / WebSocket widgets for the dashboard.

Two WS connections:
- Port 8767 — legacy ticker (price data only)
- Port 8765 — RPC WebSocket (account, status, positions, regime)
"""

# ── Compact live ticker bar (always visible at top) ──
_LIVE_WIDGET_HTML = r"""
<div style="font-family: 'Outfit', sans-serif; background: linear-gradient(135deg, rgba(25, 25, 45, 0.4), rgba(15, 15, 26, 0.2)); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.5rem 1.2rem; margin-bottom: 0.8rem; display: flex; align-items: center; justify-content: space-between; gap: 20px; font-size: 0.8rem; box-shadow: 0 4px 15px rgba(0,0,0,0.15); backdrop-filter: blur(10px);">
    <div style="display: flex; align-items: center; gap: 10px;">
        <span class="live-dot red" style="flex-shrink:0;"></span>
        <span style="font-weight: 800; font-size: 0.65rem; color: #ef4444; letter-spacing: 0.1em; text-transform: uppercase;">LIVE FEED</span>
    </div>
    <div style="display: flex; align-items: center; gap: 24px; flex-wrap: wrap;">
        <div><span style="opacity: 0.45; font-size: 0.7rem; font-weight: 500;">SYMBOL</span> <strong id="ticker-symbol" style="font-weight: 700; color: #ffffff; margin-left: 4px;">—</strong></div>
        <div style="width: 1px; height: 12px; background: rgba(255,255,255,0.08);"></div>
        <div><span style="opacity: 0.45; font-size: 0.7rem; font-weight: 500;">BID</span> <strong id="ticker-bid" style="font-weight: 800; color: #10b981; margin-left: 4px;">—</strong></div>
        <div style="width: 1px; height: 12px; background: rgba(255,255,255,0.08);"></div>
        <div><span style="opacity: 0.45; font-size: 0.7rem; font-weight: 500;">ASK</span> <strong id="ticker-ask" style="font-weight: 800; color: #ef4444; margin-left: 4px;">—</strong></div>
        <div style="width: 1px; height: 12px; background: rgba(255,255,255,0.08);"></div>
        <div><span style="opacity: 0.45; font-size: 0.7rem; font-weight: 500;">SPREAD</span> <strong id="ticker-spread" style="font-weight: 600; opacity: 0.8; margin-left: 4px; color: #c7d2fe;">—</strong></div>
        <div style="width: 1px; height: 12px; background: rgba(255,255,255,0.08);"></div>
        <div><span style="opacity: 0.45; font-size: 0.7rem; font-weight: 500;">CHANGE</span> <strong id="ticker-change" style="font-weight: 700; margin-left: 4px;">—</strong></div>
    </div>
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
                        chgEl.style.color = d.c >= 0 ? '#10b981' : '#ef4444';
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
<div id="realtime-dashboard" style="font-family: 'Outfit', sans-serif; display:flex; justify-content:space-between; align-items:center; gap:16px; flex-wrap:wrap; margin-bottom:0.8rem; background:rgba(20,20,35,0.35); border:1px solid rgba(255,255,255,0.06); border-radius:14px; padding:0.7rem 1.2rem; font-size:0.78rem; transition:all 0.3s; box-shadow:0 4px 15px rgba(0,0,0,0.15); backdrop-filter: blur(10px);">
    <div style="display:flex; align-items:center; gap:8px;">
        <span style="opacity:0.45; font-size:0.65rem; font-weight:700; letter-spacing:0.05em;">PLATFORM</span>
        <span id="ws-mt5" style="font-size:0.9rem;">&ndash;</span>
    </div>
    <div class="vr" style="width:1px; height:18px; background:rgba(255,255,255,0.08);"></div>
    
    <div style="display: flex; gap: 24px; align-items: center; flex-wrap: wrap;">
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">BALANCE</span> <strong id="ws-balance" style="color:#ffffff; font-weight:700; margin-left:4px;">&ndash;</strong></div>
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">EQUITY</span> <strong id="ws-equity" style="color:#10b981; font-weight:700; margin-left:4px;">&ndash;</strong></div>
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">FREE MARGIN</span> <strong id="ws-margin" style="color:#ffffff; font-weight:600; margin-left:4px;">&ndash;</strong></div>
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">MARGIN LVL</span> <strong id="ws-margin-level" style="color:#ffffff; font-weight:600; margin-left:4px;">&ndash;</strong></div>
    </div>
    
    <div class="vr" style="width:1px; height:18px; background:rgba(255,255,255,0.08);"></div>
    
    <div style="display: flex; gap: 20px; align-items: center; flex-wrap: wrap;">
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">REGIME</span> <strong id="ws-regime" style="font-weight:800; text-transform:uppercase; margin-left:4px; padding: 2px 8px; border-radius: 6px; font-size: 0.68rem; background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.05);">&ndash;</strong></div>
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">STRATEGY</span> <strong id="ws-strategy" style="color:#a5b4fc; font-weight:700; margin-left:4px;">&ndash;</strong></div>
        <div><span style="opacity:0.45; font-weight:550; font-size:0.7rem;">POSITIONS</span> <span id="ws-positions" style="font-weight:700; background: rgba(99, 102, 241, 0.15); border: 1px solid rgba(99, 102, 241, 0.3); color: #a5b4fc; border-radius: 6px; padding: 2px 8px; font-size: 0.72rem; margin-left:4px;">&ndash;</span></div>
    </div>
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
                            var colors = {'TRENDING':'#10b981','RANGING':'#f59e0b','CHOPPY':'#ef4444'};
                            var bgColors = {'TRENDING':'rgba(16, 185, 129, 0.1)','RANGING':'rgba(245, 158, 11, 0.1)','CHOPPY':'rgba(239, 68, 68, 0.1)'};
                            var borderColors = {'TRENDING':'rgba(16, 185, 129, 0.25)','RANGING':'rgba(245, 158, 11, 0.25)','CHOPPY':'rgba(239, 68, 68, 0.25)'};
                            
                            el.style.color = colors[d.status.regime.toUpperCase()] || '#ffffff';
                            el.style.backgroundColor = bgColors[d.status.regime.toUpperCase()] || 'rgba(255,255,255,0.04)';
                            el.style.borderColor = borderColors[d.status.regime.toUpperCase()] || 'rgba(255,255,255,0.05)';
                        }
                        var el2 = document.getElementById('ws-strategy');
                        if(el2) el2.textContent = d.status.best_strategy || '\u2014';
                        var el5 = document.getElementById('ws-mt5');
                        if(el5){
                            el5.innerHTML = d.status.mt5_connected ? '<span style="color:#10b981; font-weight:700;">🟢 CONNECTED</span>' : '<span style="color:#ef4444; font-weight:700;">🔴 DISCONNECTED</span>';
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
