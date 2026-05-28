"""Dashboard overview page — bot status, risk summary, strategy signals, MT5 status."""

import streamlit as st
import pandas as pd

from src.rpc.websocket import get_shared
from dashboard.components import render_auto_trade_controls


def render():
    st.title("📊 Dashboard Overview")
    robot = st.session_state.robot

    # ── Handle Close Position Action from URL query params ──
    query_params = st.query_params
    if "close_ticket" in query_params:
        ticket = query_params["close_ticket"]
        try:
            ticket_int = int(ticket)
            with st.spinner(f"Closing position {ticket_int}..."):
                result = robot.close_position(ticket_int)
                if result.get("success"):
                    st.success(f"✅ Position {ticket_int} closed successfully!")
                else:
                    st.error(f"❌ Failed to close position: {result.get('error', 'Unknown error')}")
        except Exception as e:
            st.error(f"⚠️ Error closing position: {e}")
        if "close_ticket" in st.query_params:
            del st.query_params["close_ticket"]
        st.rerun()

    # Get WebSocket port dynamically from shared state
    ws_port = get_shared("ws_port", 8765)

    # ── Embedded HTML/JS for 100% Real-Time Panel ──
    realtime_panel_html = """
    <div id="rt-dashboard-root" style="font-family: 'Outfit', sans-serif; display: flex; flex-direction: column; gap: 12px;">
        <!-- Grid 1: Bot Status & Account Info -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">
            <!-- Card 1: Bot Status -->
            <div class="glass-card" style="position: relative; overflow: hidden; background: rgba(18, 18, 32, 0.35); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.9rem; backdrop-filter: blur(20px); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);">
                <div style="position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: linear-gradient(180deg, #6366f1, #8b5cf6);"></div>
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #a5b4fc; font-size: 0.85rem; font-weight: 700; display: flex; align-items: center; gap: 8px; letter-spacing: 0.05em;">🤖 BOT STATUS</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;">
                    <div><span style="opacity:0.55;">Symbol:</span> <strong id="rt-bot-symbol">—</strong></div>
                    <div><span style="opacity:0.55;">Timeframe:</span> <strong id="rt-bot-tf">—</strong></div>
                    <div><span style="opacity:0.55;">Mode:</span> <strong id="rt-bot-mode">—</strong></div>
                    <div><span style="opacity:0.55;">Cycles:</span> <strong id="rt-bot-cycles">—</strong></div>
                    <div><span style="opacity:0.55;">Regime:</span> <strong id="rt-bot-regime" style="font-weight:800; text-transform:uppercase;">—</strong></div>
                    <div><span style="opacity:0.55;">Best Strategy:</span> <strong id="rt-bot-best-strat">—</strong></div>
                </div>
            </div>
            
            <!-- Card 2: Account Info -->
            <div class="glass-card" style="position: relative; overflow: hidden; background: rgba(18, 18, 32, 0.35); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.9rem; backdrop-filter: blur(20px); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);">
                <div style="position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: linear-gradient(180deg, #10b981, #34d399);"></div>
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #34d399; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em;">🏦 ACCOUNT INFO</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;">
                    <div><span style="opacity:0.55;">Balance:</span> <strong id="rt-acc-balance">—</strong></div>
                    <div><span style="opacity:0.55;">Equity:</span> <strong id="rt-acc-equity" style="color: #10b981;">—</strong></div>
                    <div><span style="opacity:0.55;">Free Margin:</span> <strong id="rt-acc-margin">—</strong></div>
                    <div><span style="opacity:0.55;">Margin Level:</span> <strong id="rt-acc-margin-lvl">—</strong></div>
                    <div style="grid-column: span 2;"><span style="opacity:0.55;">Daily P&L:</span> <strong id="rt-acc-pnl">—</strong></div>
                </div>
            </div>
        </div>

        <!-- Grid 2: Risk Snapshot & Strategy Signals -->
        <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(320px, 1fr)); gap: 12px;">
            <!-- Card 3: Risk Snapshot -->
            <div class="glass-card" style="position: relative; overflow: hidden; background: rgba(18, 18, 32, 0.35); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.9rem; backdrop-filter: blur(20px); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);">
                <div style="position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: linear-gradient(180deg, #f59e0b, #fbbf24);"></div>
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #fbbf24; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em;">🛡️ RISK SNAPSHOT</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;">
                    <div><span style="opacity:0.55;">Drawdown:</span> <strong id="rt-risk-dd">—</strong></div>
                    <div><span style="opacity:0.55;">Daily Loss:</span> <strong id="rt-risk-daily-loss">—</strong></div>
                    <div><span style="opacity:0.55;">Daily Trades:</span> <strong id="rt-risk-trades">—</strong></div>
                    <div><span style="opacity:0.55;">Open Positions:</span> <strong id="rt-risk-positions">—</strong></div>
                    <div><span style="opacity:0.55;">Can Trade:</span> <strong id="rt-risk-can-trade">—</strong></div>
                    <div><span style="opacity:0.55;">Circuit Breaker:</span> <strong id="rt-risk-cb">—</strong></div>
                </div>
            </div>
            
            <!-- Card 4: Strategy Signals -->
            <div class="glass-card" style="position: relative; overflow: hidden; background: rgba(18, 18, 32, 0.35); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.9rem; backdrop-filter: blur(20px); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);">
                <div style="position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: linear-gradient(180deg, #ec4899, #f472b6);"></div>
                <h3 style="margin-top: 0; margin-bottom: 10px; color: #f472b6; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em;">📡 ENSEMBLE SIGNALS</h3>
                <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 8px; font-size: 0.78rem;">
                    <div><span style="opacity:0.55;">Strategy:</span> <span id="rt-sig-base" style="font-weight:700;">—</span></div>
                    <div><span style="opacity:0.55;">ML Predictor:</span> <span id="rt-sig-ml" style="font-weight:700;">—</span></div>
                    <div><span style="opacity:0.55;">Agent Logic:</span> <span id="rt-sig-agent" style="font-weight:700;">—</span></div>
                    <div><span style="opacity:0.55;">Swarm Ensemble:</span> <span id="rt-sig-swarm" style="font-weight:700;">—</span></div>
                </div>
            </div>
        </div>

        <!-- Section 3: Open Positions -->
        <div class="glass-card" style="position: relative; overflow: hidden; background: rgba(18, 18, 32, 0.35); border: 1px solid rgba(255, 255, 255, 0.06); border-radius: 12px; padding: 0.9rem; backdrop-filter: blur(20px); box-shadow: 0 4px 20px 0 rgba(0, 0, 0, 0.25);">
            <div style="position: absolute; top: 0; left: 0; width: 3px; height: 100%; background: linear-gradient(180deg, #3b82f6, #60a5fa);"></div>
            <h3 style="margin-top: 0; margin-bottom: 10px; color: #60a5fa; font-size: 0.85rem; font-weight: 700; letter-spacing: 0.05em;">💼 ACTIVE POSITIONS</h3>
            <div style="overflow-x: auto;">
                <table style="width: 100%; border-collapse: collapse; font-size: 0.76rem; text-align: left;">
                    <thead>
                        <tr style="border-bottom: 1px solid rgba(255,255,255,0.08); opacity: 0.6; height: 28px;">
                            <th style="padding: 6px 10px;">Ticket</th>
                            <th style="padding: 6px 10px;">Symbol</th>
                            <th style="padding: 6px 10px;">Type</th>
                            <th style="padding: 6px 10px;">Volume</th>
                            <th style="padding: 6px 10px;">Price</th>
                            <th style="padding: 6px 10px;">SL / TP</th>
                            <th style="padding: 6px 10px; text-align: right;">Profit ($)</th>
                            <th style="padding: 6px 10px; text-align: center;">Action</th>
                        </tr>
                    </thead>
                    <tbody id="rt-positions-table-body">
                        <tr>
                            <td colspan="8" style="padding: 24px; text-align: center; opacity: 0.5;">No active positions</td>
                        </tr>
                    </tbody>
                </table>
            </div>
        </div>
    </div>

    <script>
    (function(){
        const wsPort = {ws_port};
        let ws = null;
        let reconnectTimer = null;
        
        function mapSignal(sig) {
            const val = Number(sig);
            if (val === 1) return '<span style="color:#10b981; font-weight:700; background:rgba(16,185,129,0.1); padding:2px 8px; border-radius:4px; border:1px solid rgba(16,185,129,0.2);">BUY</span>';
            if (val === -1) return '<span style="color:#ef4444; font-weight:700; background:rgba(239,68,68,0.1); padding:2px 8px; border-radius:4px; border:1px solid rgba(239,68,68,0.2);">SELL</span>';
            return '<span style="color:#9ca3af; font-weight:700; background:rgba(255,255,255,0.04); padding:2px 8px; border-radius:4px; border:1px solid rgba(255,255,255,0.05);">HOLD</span>';
        }
        
        function connect(){
            try {
                ws = new WebSocket('ws://' + window.location.hostname + ':' + wsPort);
                ws.onmessage = function(e){
                    try {
                        const d = JSON.parse(e.data);
                        
                        // Update Bot Status
                        if (d.status) {
                            document.getElementById('rt-bot-symbol').textContent = d.price.symbol || '—';
                            document.getElementById('rt-bot-tf').textContent = d.status.timeframe || '—';
                            document.getElementById('rt-bot-mode').textContent = d.status.paper_trading ? '📝 Paper' : '💵 Real';
                            document.getElementById('rt-bot-cycles').textContent = d.status.cycles || '0';
                            
                            const regimeEl = document.getElementById('rt-bot-regime');
                            regimeEl.textContent = d.status.regime || '—';
                            const colors = {'TRENDING':'#10b981','RANGING':'#f59e0b','CHOPPY':'#ef4444'};
                            regimeEl.style.color = colors[d.status.regime.toUpperCase()] || '#ffffff';
                            
                            document.getElementById('rt-bot-best-strat').textContent = d.status.best_strategy || '—';
                        }
                        
                        // Update Account Info
                        if (d.account) {
                            document.getElementById('rt-acc-balance').textContent = '$' + Number(d.account.balance).toFixed(2);
                            document.getElementById('rt-acc-equity').textContent = '$' + Number(d.account.equity).toFixed(2);
                            document.getElementById('rt-acc-margin').textContent = '$' + Number(d.account.free_margin).toFixed(2);
                            document.getElementById('rt-acc-margin-lvl').textContent = Number(d.account.margin_level).toFixed(2) + '%';
                            
                            // Compute Daily P&L (Equity - Balance)
                            const pnl = Number(d.account.equity) - Number(d.account.balance);
                            const pnlEl = document.getElementById('rt-acc-pnl');
                            pnlEl.textContent = (pnl >= 0 ? '+' : '-') + '$' + Math.abs(pnl).toFixed(2);
                            pnlEl.style.color = pnl >= 0 ? '#10b981' : '#ef4444';
                        }
                        
                        // Update Risk Snapshot
                        if (d.risk) {
                            const dd = Number(d.risk.drawdown_pct || 0);
                            const maxDd = Number(d.risk.max_drawdown_pct || 5.0);
                            document.getElementById('rt-risk-dd').textContent = dd.toFixed(2) + '% (Limit: ' + maxDd + '%)';
                            
                            const dl = Number(d.risk.daily_loss_pct || 0);
                            const maxDl = Number(d.risk.max_daily_loss_pct || 3.0);
                            document.getElementById('rt-risk-daily-loss').textContent = dl.toFixed(2) + '% (Limit: ' + maxDl + '%)';
                            
                            document.getElementById('rt-risk-trades').textContent = d.risk.daily_trades || '0';
                            document.getElementById('rt-risk-positions').textContent = d.risk.open_positions || '0';
                            
                            const canTrade = d.risk.can_trade;
                            document.getElementById('rt-risk-can-trade').innerHTML = canTrade ? '<span style="color:#10b981; font-weight:700;">✅ YES</span>' : '<span style="color:#ef4444; font-weight:700;">❌ NO</span>';
                            
                            const cb = d.risk.circuit_breaker_active;
                            document.getElementById('rt-risk-cb').innerHTML = cb ? '<span style="color:#ef4444; font-weight:700;">🔴 ACTIVE</span>' : '<span style="color:#10b981; font-weight:700;">✅ OK</span>';
                        }
                        
                        // Update Signals
                        if (d.signals) {
                            document.getElementById('rt-sig-base').innerHTML = mapSignal(d.signals.strategy);
                            document.getElementById('rt-sig-ml').innerHTML = mapSignal(d.signals.ml);
                            document.getElementById('rt-sig-agent').innerHTML = mapSignal(d.signals.agent);
                            document.getElementById('rt-sig-swarm').innerHTML = mapSignal(d.signals.swarm);
                        }
                        
                        // Update Open Positions Table
                        if (d.positions) {
                            const tbody = document.getElementById('rt-positions-table-body');
                            const plist = d.positions.list || [];
                            if (plist.length === 0) {
                                tbody.innerHTML = '<tr><td colspan="8" style="padding: 16px; text-align: center; opacity: 0.5;">No active positions</td></tr>';
                            } else {
                                let html = '';
                                plist.forEach(function(p){
                                    const profit = Number(p.profit || 0);
                                    const profitColor = profit >= 0 ? '#10b981' : '#ef4444';
                                    const profitSign = profit >= 0 ? '+' : '';
                                    const typeText = String(p.type).toUpperCase() === 'BUY' || p.type === 0 ? '<span style="color:#10b981; font-weight:700;">BUY</span>' : '<span style="color:#ef4444; font-weight:700;">SELL</span>';
                                    
                                    html += `<tr style="border-bottom: 1px solid rgba(255,255,255,0.04); height: 32px;">`;
                                    html += `<td style="padding: 4px 10px; font-weight:600;">#${p.ticket}</td>`;
                                    html += `<td style="padding: 4px 10px;">${p.symbol}</td>`;
                                    html += `<td style="padding: 4px 10px;">${typeText}</td>`;
                                    html += `<td style="padding: 4px 10px; font-weight:600;">${Number(p.volume).toFixed(2)}</td>`;
                                    html += `<td style="padding: 4px 10px;">$${Number(p.price).toFixed(2)}</td>`;
                                    html += `<td style="padding: 4px 10px; font-size:0.7rem; opacity:0.6;">SL: ${p.sl ? Number(p.sl).toFixed(2) : '—'} | TP: ${p.tp ? Number(p.tp).toFixed(2) : '—'}</td>`;
                                    html += `<td style="padding: 4px 10px; text-align:right; font-weight:800; color:${profitColor};">${profitSign}$${profit.toFixed(2)}</td>`;
                                    html += `<td style="padding: 4px 10px; text-align:center;"><button onclick="closePosition(${p.ticket})" style="background:rgba(239,68,68,0.12); border:1px solid rgba(239,68,68,0.25); color:#f87171; border-radius:6px; padding:2px 8px; font-size:0.68rem; cursor:pointer; font-weight:600; font-family:'Outfit',sans-serif; transition:all 0.2s;">CLOSE</button></td>`;
                                    html += `</tr>`;
                                });
                                tbody.innerHTML = html;
                            }
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
        
        // Parent window query parameter action trigger
        window.closePosition = function(ticket) {
            if (confirm("Close position #" + ticket + "?")) {
                const url = new URL(window.parent.location.href);
                url.searchParams.set("close_ticket", ticket);
                window.parent.location.href = url.toString();
            }
        };
        
        if(typeof WebSocket !== 'undefined') connect();
    })();
    </script>
    """.replace("{ws_port}", str(ws_port))

    st.markdown(realtime_panel_html, unsafe_allow_html=True)

    # ── Trading & Execution Controls ──
    st.subheader("💱 Trading & Execution")
    config = st.session_state.config
    col1, col2 = st.columns(2)
    with col1:
        with st.container(border=True):
            st.markdown("### 🤖 Auto Trading Controls")
            render_auto_trade_controls()
            
    with col2:
        with st.container(border=True):
            st.markdown("### 💱 Manual Order Execution")
            mc1, mc2 = st.columns(2)
            with mc1:
                manual_symbol = st.text_input("Symbol", value=config.get("general", "symbol"), key="manual_symbol")
            with mc2:
                manual_volume = st.number_input("Volume", min_value=0.01, max_value=100.0, value=0.1, step=0.01, key="manual_vol")
            
            mb1, mb2 = st.columns(2)
            with mb1:
                if st.button("BUY", type="primary", use_container_width=True):
                    try:
                        result = robot.open_trade(manual_symbol, "buy", manual_volume)
                        if result.get("success"):
                            st.success(f"BUY order placed! Ticket: {result.get('ticket')}")
                            st.rerun()
                        else:
                            st.error(f"BUY failed: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Error: {e}")
            with mb2:
                if st.button("SELL", type="secondary", use_container_width=True):
                    try:
                        result = robot.open_trade(manual_symbol, "sell", manual_volume)
                        if result.get("success"):
                            st.success(f"SELL order placed! Ticket: {result.get('ticket')}")
                            st.rerun()
                        else:
                            st.error(f"SELL failed: {result.get('error')}")
                    except Exception as e:
                        st.error(f"Error: {e}")

    # ── Recent Trades (Static history component, perfect for manual reviews) ──
    st.subheader("📜 Recent Trades (History)")
    with st.container(border=True):
        dc = st.session_state.get("dashboard_ctrl")
        if dc:
            try:
                trades = dc.get_trade_history(limit=10)
                if trades:
                    df = pd.DataFrame(trades)
                    st.dataframe(df, use_container_width=True, hide_index=True)
                else:
                    st.info("No recent trades in database")
            except Exception as e:
                st.info(f"Could not load trades: {e}")
        else:
            st.info("Dashboard controller not available")
