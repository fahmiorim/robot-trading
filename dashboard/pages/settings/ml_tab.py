"""
ML Settings Tab — premium glass cards with Indonesian descriptions.
"""
import streamlit as st
import textwrap

ML_INFO = {
    "model_type": {
        "icon": "🧠",
        "label": "Tipe Model",
        "help": "Pilih algoritma ML: Random Forest (serbaguna), Gradient Boosting (akurasi tinggi), atau LSTM (time-series).",
    },
    "retrain_interval_hours": {
        "icon": "🔄",
        "label": "Retrain (jam)",
        "min": 1, "max": 168, "step": 1,
        "help": "Frekuensi retrain model. Scalping M1: 6–12 jam. Timeframe tinggi: 24 jam.",
    },
    "n_estimators": {
        "icon": "🌲",
        "label": "Jumlah Pohon",
        "min": 10, "max": 500, "step": 10,
        "help": "Jumlah pohon untuk Random Forest / boosting. Lebih banyak = lebih akurat tapi lebih lambat.",
    },
    "max_depth": {
        "icon": "🌳",
        "label": "Max Depth",
        "min": 1, "max": 50, "step": 1,
        "help": "Kedalaman maksimum pohon. 5 = pohon pendek (generalize lebih baik). None (0) = unlimited (risiko overfit tinggi).",
    },
    "min_samples_split": {
        "icon": "🧩",
        "label": "Min Split",
        "min": 2, "max": 50, "step": 1,
        "help": "Jumlah sampel minimal untuk membelah node. 2 = sensitif, 20 = lebih smooth. Nilai 5-10 kurangi overfit.",
    },
    "classification_threshold": {
        "icon": "🎯",
        "label": "Min Threshold",
        "min": 0.0, "max": 0.02, "step": 0.0001, "format": "%.4f",
        "help": "Batas minimum return untuk label Buy/Sell. 0.0005 = 0.05%. Direkomendasikan 0.0 agar ATR adaptif bekerja optimal.",
    },
    "atr_multiplier": {
        "icon": "📐",
        "label": "ATR Multiplier",
        "min": 0.05, "max": 2.0, "step": 0.05, "format": "%.2f",
        "help": "Proporsi ATR untuk threshold adaptif. 0.2 = 20% dari ATR. Semakin kecil = semakin banyak sinyal BUY/SELL.",
    },
    "test_size": {
        "icon": "📊",
        "label": "Test Size",
        "min": 0.05, "max": 0.5, "step": 0.05,
        "help": "Proporsi data untuk validasi. 0.2 = 80% training, 20% testing.",
    },
    "random_state": {
        "icon": "🎲",
        "label": "Random Seed",
        "min": 0, "max": 9999, "step": 1,
        "help": "Seed untuk reproducibility. Ganti jika ingin variasi training.",
    },
}

LSTM_INFO = {
    "sequence_length": {
        "icon": "📏",
        "label": "Panjang Sequence",
        "min": 10, "max": 200, "step": 5,
        "help": "Jumlah candle lookback untuk LSTM. M1: 60 (1 jam). M15: 30 (7.5 jam).",
    },
    "hidden_size": {
        "icon": "🔲",
        "label": "Hidden Size",
        "min": 16, "max": 256, "step": 16,
        "help": "Ukuran hidden layer LSTM. Lebih besar = lebih kompleks.",
    },
    "num_layers": {
        "icon": "📚",
        "label": "Jumlah Layer",
        "min": 1, "max": 5, "step": 1,
        "help": "Jumlah stacked LSTM layers. 2–3 cukup untuk scalping.",
    },
    "epochs": {
        "icon": "🔁",
        "label": "Epochs",
        "min": 5, "max": 200, "step": 5,
        "help": "Jumlah epoch training. 50 cukup untuk dataset kecil.",
    },
    "batch_size": {
        "icon": "📦",
        "label": "Batch Size",
        "min": 8, "max": 256, "step": 8,
        "help": "Ukuran batch training. 32 standar, lebih kecil untuk dataset kecil.",
    },
    "learning_rate": {
        "icon": "⚡",
        "label": "Learning Rate",
        "min": 0.0001, "max": 0.1, "step": 0.0001, "format": "%.4f",
        "help": "Kecepatan learning. 0.001 standar Adam. Turunkan jika loss naik.",
    },
    "classification_threshold": {
        "icon": "🎯",
        "label": "Min Threshold",
        "min": 0.0, "max": 0.01, "step": 0.0001, "format": "%.4f",
        "help": "Batas minimum return untuk label Buy/Hold/Sell LSTM. 0.0 agar ATR adaptif bekerja.",
    },
    "atr_multiplier": {
        "icon": "📐",
        "label": "ATR Multiplier",
        "min": 0.05, "max": 2.0, "step": 0.05, "format": "%.2f",
        "help": "Proporsi ATR untuk threshold adaptif LSTM. Default 0.2 = 20% dari ATR.",
    },
}


def _render_card(config, section: str, key: str, info: dict) -> bool:
    """Compact parameter card: description on left, input on right."""
    edited = False
    v = config.get(section, key)
    is_int = info.get("min") is not None and isinstance(info["min"], int)
    fmt = info.get("format", None)

    with st.container(border=True):
        c1, c2 = st.columns([1.8, 1.2], vertical_alignment="center")
        with c1:
            st.markdown(f"**{info['icon']} {info['label']}**")
            st.caption(info.get("help", ""))
        with c2:
            if key == "model_type":
                opts = ["random_forest", "gradient_boosting", "lstm"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox("", opts, idx, key=f"{section}_{key}", label_visibility="collapsed")
                if nv != v:
                    config.set(section, key, nv)
                    edited = True
            elif is_int:
                nv = st.number_input("", info["min"], info["max"], int(v), int(info.get("step", 1)),
                                     key=f"{section}_{key}", label_visibility="collapsed")
                if nv != v:
                    config.set(section, key, nv)
                    edited = True
            else:
                step = info.get("step", 0.001)
                nv = st.number_input("", info["min"], info["max"], float(v), step,
                                     format=fmt, key=f"{section}_{key}", label_visibility="collapsed")
                if nv != v:
                    config.set(section, key, nv)
                    edited = True

    return edited


def _render_training_history(config):
    """Render ML training history visualizations from ml_training_log table.
    Supports auto-refresh every 30 seconds when toggled.
    """
    from src.controllers.dashboard_controller import DashboardController
    import plotly.graph_objects as go
    import plotly.express as px
    import pandas as pd

    dc = st.session_state.get("dashboard_ctrl", DashboardController())

    # ── Real-time via WebSocket toggle ──
    ws_realtime = st.checkbox(
        "🔵 Real-time via WebSocket",
        value=st.session_state.get("ml_ws_realtime", False),
        key="ml_ws_realtime",
        help="Aktifkan untuk refresh otomatis via WebSocket saat training selesai — tanpa polling periodik.",
    )
    if ws_realtime:
        from src.rpc.websocket import get_shared
        _ws_port = get_shared("ws_port", 8765)
        st.markdown('<div id="ml-ws-sentinel"></div>', unsafe_allow_html=True)
        st.markdown(f"""
        <script>
        (function() {{
            if (window._mlWsInit) return;
            window._mlWsInit = true;
            var port = {_ws_port};
            var host = window.location.hostname;
            if (!host || host === "null" || host === "") host = "localhost";
            function connect() {{
                var ws = new WebSocket('ws://' + host + ':' + port);
                ws.onmessage = function(e) {{
                    try {{
                        var d = JSON.parse(e.data);
                        if (!document.getElementById('ml-ws-sentinel')) {{ ws.close(); return; }}
                        if (d.ml_training && d.ml_training.timestamp) {{ window.location.reload(); }}
                    }} catch(err) {{}}
                }};
                ws.onclose = function() {{ setTimeout(connect, 3000); }};
            }}
            connect();
        }})();
        </script>
        """, unsafe_allow_html=True)
        st.caption("🔵 Real-time via WebSocket • Halaman refresh otomatis saat training selesai — tanpa polling")

    # ── Concept Drift Warning ──
    try:
        drift = dc.check_concept_drift(threshold_pct=5.0)
        if drift.get("drifted"):
            st.warning(
                f"⚠️ **Concept Drift Terdeteksi**\n\n"
                f"Akurasi terbaru **{drift['latest_acc']:.2%}** turun **{drift['drop_pct']:.1f}%** "
                f"dibanding rata-rata 3 training sebelumnya (**{drift['avg_prev_3']:.2%}**)."
            )
        elif drift.get("n_available", 0) >= 4:
            st.success(f"✅ **Tidak ada concept drift.** Akurasi stabil ({drift['latest_acc']:.2%} vs rata-rata {drift['avg_prev_3']:.2%}).")
    except Exception:
        pass

    try:
        logs = dc.get_ml_training_log(limit=30)
    except Exception as e:
        st.info(f"Tidak dapat memuat riwayat training dari DB: {e}")
        return

    if not logs:
        st.info("Belum ada riwayat training. Jalankan **Retrain ML Now** di atas untuk memulai.")
        return

    # Convert to DataFrame
    df = pd.DataFrame(logs)
    for col in ["accuracy", "precision", "recall", "f1_score"]:
        if col in df.columns:
            df[col] = df[col].astype(float)
    if "trained_at" in df.columns:
        df["trained_at"] = pd.to_datetime(df["trained_at"])
        df = df.sort_values("trained_at")

    # ── Metrics bar ──
    latest = df.iloc[-1]
    latest_acc = latest.get("accuracy", 0) or 0
    avg_acc = df["accuracy"].mean() if "accuracy" in df.columns else 0
    n_runs = len(df)
    best_idx = df["accuracy"].idxmax() if "accuracy" in df.columns else -1
    best_acc = df.loc[best_idx, "accuracy"] if best_idx >= 0 else 0
    # Trend: compare latest to previous
    trend = "▲" if len(df) > 1 and latest_acc > df.iloc[-2].get("accuracy", 0) else "▼"
    trend_color = "#10b981" if trend == "▲" else "#ef4444"

    acc_color = "#10b981" if latest_acc >= avg_acc else "#f59e0b"
    sep = '<div style="width:1px; height:26px; background:rgba(255,255,255,0.06);"></div>'
    cells = "".join([
        f'<div style="flex:1; text-align:center; min-width:0;">'
        f'<div style="font-size:0.55rem; opacity:0.45; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;">Training</div>'
        f'<div style="font-size:1.1rem; font-weight:800; color:#ffffff; margin-top:2px;">{n_runs}</div></div>',
        sep,
        f'<div style="flex:1; text-align:center; min-width:0;">'
        f'<div style="font-size:0.55rem; opacity:0.45; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;">Accuracy</div>'
        f'<div style="font-size:1.1rem; font-weight:800; color:{acc_color}; margin-top:2px;">{latest_acc:.2%}'
        f' <span style="font-size:0.7rem; color:{trend_color};">{trend}</span></div></div>',
        sep,
        f'<div style="flex:1; text-align:center; min-width:0;">'
        f'<div style="font-size:0.55rem; opacity:0.45; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;">Rata-rata</div>'
        f'<div style="font-size:1.1rem; font-weight:800; color:#a5b4fc; margin-top:2px;">{avg_acc:.2%}</div></div>',
        sep,
        f'<div style="flex:1; text-align:center; min-width:0;">'
        f'<div style="font-size:0.55rem; opacity:0.45; font-weight:700; text-transform:uppercase; letter-spacing:0.1em;">Terbaik</div>'
        f'<div style="font-size:1.1rem; font-weight:800; color:#10b981; margin-top:2px;">{best_acc:.2%}</div></div>',
    ])
    st.markdown(
        f'<div class="glass-card" style="padding:0.5rem 0.8rem; margin-bottom:0.8rem;">'
        f'<div style="display:flex; align-items:center; justify-content:space-around;">{cells}</div></div>',
        unsafe_allow_html=True,
    )

    col_chart1, col_chart2 = st.columns(2)

    # ── Chart 1: Accuracy Line ──
    with col_chart1:
        fig_acc = go.Figure()
        fig_acc.add_trace(go.Scatter(
            x=df["trained_at"],
            y=df["accuracy"],
            mode="lines+markers",
            name="Accuracy",
            line=dict(color="#6366f1", width=2.5, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(99, 102, 241, 0.08)",
            marker=dict(
                color=df["accuracy"],
                colorscale="Viridis",
                size=8,
                showscale=False,
                line=dict(width=1, color="rgba(255,255,255,0.3)"),
            ),
            hovertemplate="<b>%{x|%d %b %H:%M}</b><br>Accuracy: %{y:.2%}<extra></extra>",
        ))
        fig_acc.add_hline(
            y=avg_acc,
            line_dash="dash",
            line_color="rgba(165, 180, 252, 0.25)",
            annotation_text=f"Avg {avg_acc:.2%}",
            annotation_font_size=10,
            annotation_font_color="rgba(165, 180, 252, 0.4)",
        )
        fig_acc.update_layout(
            title=dict(text="🎯 Akurasi per Training", font=dict(size=13, color="#e0e7ff")),
            height=270,
            margin=dict(l=10, r=10, t=35, b=10),
            template="plotly_dark",
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            xaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                title="", type="date",
            ),
            yaxis=dict(
                showgrid=True, gridcolor="rgba(255,255,255,0.03)",
                title="", tickformat=".0%", range=[0, df["accuracy"].max() * 1.2 or 1],
            ),
            hovermode="x unified",
        )
        st.plotly_chart(fig_acc, width='stretch')

    # ── Chart 2: Class Distribution Stacked Bar ──
    with col_chart2:
        dist_data = []
        class_labels = {-1: "SELL", 0: "HOLD", 1: "BUY"}
        class_colors = {-1: "#ef4444", 0: "#6b7280", 1: "#10b981"}
        for _, row in df.iterrows():
            cd = row.get("class_distribution", {})
            if isinstance(cd, dict):
                total = sum(cd.values()) or 1
                # JSON serialization converts int keys to strings, so use str() lookup
                for cls_id in [-1, 0, 1]:
                    dist_data.append({
                        "trained_at": row["trained_at"],
                        "kelas": class_labels.get(cls_id, str(cls_id)),
                        "persentase": cd.get(str(cls_id), 0) / total * 100,
                    })

        if dist_data:
            df_dist = pd.DataFrame(dist_data)
            fig_dist = px.bar(
                df_dist,
                x="trained_at",
                y="persentase",
                color="kelas",
                color_discrete_map=class_colors,
                title="📊 Distribusi Kelas per Training",
                labels={"trained_at": "", "persentase": "%", "kelas": "Sinyal"},
            )
            fig_dist.update_traces(hovertemplate="<b>%{x|%d %b %H:%M}</b><br>%{y:.1f}%<extra></extra>")
            fig_dist.update_layout(
                height=270,
                margin=dict(l=10, r=10, t=35, b=10),
                template="plotly_dark",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                barmode="stack",
                xaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)", title=""),
                yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.03)", title="", ticksuffix="%"),
                legend=dict(
                    orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1,
                    font=dict(size=10),
                ),
                hovermode="x unified",
            )
            st.plotly_chart(fig_dist, width='stretch')
        else:
            st.info("Data distribusi kelas tidak tersedia")

    # ── Feature Importance Evolution Table ──
    with st.expander("🔬 Feature Importance Evolution", expanded=False):
        st.caption("Top 5 fitur paling berpengaruh di setiap sesi training. Membantu melihat apakah fitur dominan berubah seiring waktu.")

        all_features = set()
        run_data = []
        for _, row in df.iterrows():
            fi = row.get("feature_importance", [])
            if isinstance(fi, list) and fi:
                run_label = row["trained_at"].strftime("%d/%m %H:%M") if hasattr(row["trained_at"], "strftime") else str(row["trained_at"])
                top5 = fi[:5]
                feats = {item["name"]: item["importance"] for item in top5}
                run_data.append({"label": run_label, "features": feats, "accuracy": row.get("accuracy", 0)})
                all_features.update(feats.keys())

        if run_data:
            sorted_features = sorted(
                all_features,
                key=lambda f: sum(r["features"].get(f, 0) for r in run_data),
                reverse=True,
            )

            tbl_md = "| # | " + " | ".join(r["label"] for r in run_data) + " |\n"
            tbl_md += "|---|" + "---|" * len(run_data) + "\n"

            for rank_idx, feat in enumerate(sorted_features[:6]):
                cells = []
                for r in run_data:
                    imp = r["features"].get(feat)
                    cells.append(f"{imp:.4f}" if imp is not None else "—")
                tbl_md += f"| {feat} | " + " | ".join(cells) + " |\n"

            st.markdown(tbl_md)
            tbl_md2 = "| **Accuracy** | " + " | ".join(f"**{r['accuracy']:.2%}**" for r in run_data) + " |\n"
            st.markdown(tbl_md2)

            if sorted_features:
                st.info(f"💡 **Fitur paling dominan:** `{sorted_features[0]}` — muncul di semua training sebagai fitur teratas.")
        else:
            st.info("Data feature importance tidak tersedia untuk training ini.")


def render(config) -> bool:
    edited = False

    st.markdown(
        textwrap.dedent("""
        <div class="info-banner">
            <div class="title">🧠 Machine Learning</div>
            <div class="desc">Konfigurasi model ML dan LSTM untuk prediksi arah harga. Parameter otomatis disesuaikan untuk scalping timeframe M1–M15.</div>
        </div>
        """),
        unsafe_allow_html=True,
    )

    st.markdown("### 🤖 Model ML")
    st.caption("Random Forest, Gradient Boosting, atau LSTM — atur arsitektur dan hyperparameter.")

    ml_keys = ["model_type", "retrain_interval_hours", "n_estimators",
               "max_depth", "min_samples_split",
               "classification_threshold", "atr_multiplier", "test_size", "random_state"]
    cols = st.columns(2)
    for i, k in enumerate(ml_keys):
        with cols[i % 2]:
            edited |= _render_card(config, "ml", k, ML_INFO[k])

    st.markdown("---")
    st.markdown("### 🔬 LSTM (Deep Learning)")
    st.caption("Arsitektur LSTM untuk analisis time-series — sequence, layer, dan hyperparameter.")

    lstm_keys = ["sequence_length", "hidden_size", "num_layers",
                 "epochs", "batch_size", "learning_rate",
                 "classification_threshold", "atr_multiplier"]
    cols = st.columns(2)
    for i, k in enumerate(lstm_keys):
        with cols[i % 2]:
            edited |= _render_card(config, "lstm", k, LSTM_INFO[k])

    st.markdown("<hr style='margin:1.6rem 0 0.8rem;'>", unsafe_allow_html=True)
    st.markdown("### 📈 Riwayat Training")
    st.caption("Visualisasi riwayat training dari database — akurasi, distribusi kelas, dan feature importance evolution.")

    _render_training_history(config)

    st.markdown("<hr style='margin:1.6rem 0 0.8rem;'>", unsafe_allow_html=True)
    
    # ── Local Training section wrapped in a card ──
    with st.container(border=True):
        st.markdown("### 🚂 Local Training")
        st.caption("Latih model ML dengan data historis tanpa memengaruhi konfigurasi global bot.")

        col_tf, col_c = st.columns(2)
        with col_tf:
            from src.constants.timeframes import TIMEFRAME_MAP
            tf_keys = list(TIMEFRAME_MAP.keys())
            default_tf = st.session_state.robot.timeframe
            default_idx = tf_keys.index(default_tf) if default_tf in tf_keys else 1
            train_tf = st.selectbox(
                "⏱️ Timeframe Data", tf_keys,
                index=default_idx,
                key="train_ml_timeframe",
                help="Timeframe lilin data historis untuk melatih model ML."
            )
        with col_c:
            train_candles = st.number_input(
                "🕯️ Candle Count", 500, 50000, 10000, 500,
                key="train_ml_candles",
                help="Jumlah lilin data historis untuk melatih model ML."
            )

        st.markdown("<div style='height: 4px;'></div>", unsafe_allow_html=True)

        btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
        with btn_col2:
            start_training = st.button("🧠 Retrain ML Now", width='stretch', type="primary")

    result_container = st.container()

    if start_training:
        from src.data.provider import DataProvider
        data = None
        with st.spinner(f"🔄 Mengunduh {train_candles} candle data market {train_tf} dari MetaTrader 5..."):
            try:
                local_provider = DataProvider(
                    exchange=st.session_state.robot.exchange,
                    symbol=st.session_state.robot.symbol,
                    timeframe=train_tf,
                    default_count=int(train_candles)
                )
                data = local_provider.fetch(force_refresh=True)
                st.toast(f"✅ Data market {train_tf} ({len(data)} candle) berhasil diambil!", icon="✅")
            except Exception as e:
                st.error(f"❌ Gagal mengambil data market: {e}")

        if data is not None:
            with st.spinner("Training..."):
                try:
                    acc = st.session_state.robot.ml_trainer.train(data)
                    with result_container:
                        st.success(f"Trained! Accuracy: {acc:.2%}")

                        stats = st.session_state.robot.ml_trainer.last_train_stats
                        if stats:
                            with st.expander("📊 Analisis Hasil & Distribusi Kelas Latih", expanded=True):
                                col_t, col_w = st.columns([4, 5])
                                with col_t:
                                    st.markdown("**Distribusi Sinyal:**")
                                    class_labels = {-1: "🔴 SELL", 0: "⚪ HOLD", 1: "🟢 BUY"}
                                    tbl_md = "| Sinyal | Jumlah | Rasio |\n| :--- | :---: | :---: |\n"
                                    for c in [-1, 0, 1]:
                                        count = stats["class_distribution"].get(c, 0)
                                        pct = stats["class_percentages"].get(c, 0.0)
                                        tbl_md += f"| {class_labels[c]} | {count} | {pct:.2%} |\n"
                                    st.markdown(tbl_md)

                                with col_w:
                                    max_class = None
                                    max_pct = 0.0
                                    for c, pct in stats["class_percentages"].items():
                                        if pct > max_pct:
                                            max_pct = pct
                                            max_class = c

                                    class_labels_long = {
                                        -1: "🔴 SELL (Jual)", 0: "⚪ HOLD (Flat/Tahan)", 1: "🟢 BUY (Beli)"
                                    }

                                    if max_pct > 0.85:
                                        st.warning(
                                            f"⚠️ **Peringatan Imbalans Kelas Parah ({max_pct:.1%})**\n\n"
                                            f"Kelas **{class_labels_long.get(max_class, max_class)}** terlalu mendominasi data latih. "
                                            f"Model cenderung mengalami akurasi semu karena hanya menebak kelas mayoritas secara pasif.\n\n"
                                            f"**Solusi:**\n"
                                            f"1. Turunkan **ATR Multiplier** (pengaturan di atas, misal ke `0.05`–`0.1`) agar threshold adaptif lebih sensitif\n"
                                            f"2. Turunkan **Min Threshold** ke `0.0` agar ATR adaptif bekerja optimal\n"
                                            f"3. Gunakan **Timeframe** lebih besar (M15, H1, H4) untuk variasi pergerakan harga lebih baik"
                                        )
                                    else:
                                        st.success(
                                            "✅ **Distribusi Sehat:** Penyebaran sinyal seimbang. Model memiliki variasi label yang memadai untuk belajar memprediksi pergerakan market."
                                        )
                except Exception as e:
                    st.error(f"Train failed: {e}")
        else:
            st.warning("Gagal mengambil data market. Pastikan MetaTrader 5 terhubung.")

    return edited
