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

