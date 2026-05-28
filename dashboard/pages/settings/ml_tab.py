import streamlit as st


def render(config) -> bool:
    edited = False

    st.subheader("🧠 Machine Learning")
    ml_keys = ["model_type", "retrain_interval_hours", "sequence_length",
               "lstm_epochs", "test_size", "random_state"]
    ml_cols = st.columns(3)
    for i, k in enumerate(ml_keys):
        v = config.get("ml", k)
        with ml_cols[i % 3]:
            if k == "test_size":
                nv = st.slider(k, 0.05, 0.5, v, key=f"ml_{k}")
            elif k == "model_type":
                opts = ["random_forest", "gradient_boosting", "lstm"]
                idx = opts.index(v) if v in opts else 0
                nv = st.selectbox(k, opts, idx, key=f"ml_{k}")
            elif isinstance(v, int):
                nv = st.number_input(k, value=v, key=f"ml_{k}")
            else:
                nv = st.text_input(k, value=str(v), key=f"ml_{k}")
            if nv != v:
                config.set("ml", k, nv)
                edited = True

    st.markdown("---")
    if st.button("🧠 Retrain ML Now", width='stretch'):
        data = st.session_state.get("_last_data")
        if data is not None:
            with st.spinner("Training..."):
                try:
                    acc = st.session_state.robot.ml_trainer.train(data)
                    st.success(f"Trained! Accuracy: {acc:.2%}")
                except Exception as e:
                    st.error(f"Train failed: {e}")
        else:
            st.warning("Fetch market data first on Dashboard")

    return edited
