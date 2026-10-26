import streamlit as st
from pulp import LpMaximize, LpProblem, LpVariable, lpSum

# --- ページ基本設定 ---
st.set_page_config(page_title="イーフト育成オプティマイザー", page_icon="⚽", layout="wide")
st.title("⚽ イーフト実戦育成オプティマイザー")
st.caption("選手検索・登場日選択 ➔ 監督・ブースター補正込み ➔ 誤差0ptで実戦ブレイクポイント特化ビルドを算出")

# コスト早見表 (1〜16UP)
COST_TABLE = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8, 7: 10, 8: 12,
    9: 15, 10: 18, 11: 21, 12: 24, 13: 28, 14: 32, 15: 36, 16: 40
}
CATEGORIES = ["シュート", "パス", "ドリブル", "クイックネス", "脚力", "エアバトル", "ディフェンス"]

# --- データベース（サンプル：環境でよく使われるカード） ---
# ※後から選手データを自由に追加・拡張できます
PLAYERS_DB = [
    {
        "name": "リオネル メッシ",
        "date": "2024/06/20",
        "type": "Big Time (コパ・アメリカ)",
        "max_pts": 48,
        "base": {"決定力": 84, "瞬発力": 87, "スピード": 83, "ボールキープ": 88, "ドリブル": 86, "DFセンス": 45},
        "booster": {"瞬発力": 2, "ボールキープ": 2}
    },
    {
        "name": "リオネル メッシ",
        "date": "2023/11/02",
        "type": "Epic (バロンドール2015)",
        "max_pts": 44,
        "base": {"決定力": 86, "瞬発力": 90, "スピード": 86, "ボールキープ": 89, "ドリブル": 88, "DFセンス": 42},
        "booster": {"スピード": 2, "瞬発力": 2}
    },
    {
        "name": "リオネル メッシ",
        "date": "2023/06/15",
        "type": "Show Time (モメンタムドリブル)",
        "max_pts": 40,
        "base": {"決定力": 82, "瞬発力": 85, "スピード": 80, "ボールキープ": 86, "ドリブル": 85, "DFセンス": 40},
        "booster": {}
    },
    {
        "name": "冨安 健洋",
        "date": "2023/09/21",
        "type": "Big Time (CB特化)",
        "max_pts": 46,
        "base": {"決定力": 55, "瞬発力": 78, "スピード": 82, "ボールキープ": 68, "ドリブル": 65, "DFセンス": 85},
        "booster": {"DFセンス": 2, "スピード": 2}
    },
    {
        "name": "パトリック ヴィエラ",
        "date": "2024/01/18",
        "type": "Epic (フォートレス)",
        "max_pts": 42,
        "base": {"決定力": 65, "瞬発力": 79, "スピード": 84, "ボールキープ": 78, "ドリブル": 75, "DFセンス": 87},
        "booster": {"DFセンス": 2, "瞬発力": 2}
    }
]

# --- 1. 選手検索・選択エリア ---
st.subheader("1. 選手の選択")
search_keyword = st.text_input("選手名で検索（例: メッシ, 冨安, ヴィエラ）", value="メッシ")

# 検索ワードでヒットしたカードを絞り込み
matched_cards = [c for c in PLAYERS_DB if search_keyword in c["name"]]

if matched_cards:
    # 登場日・タイプで選択肢を作成
    card_dict = {f"[{c['date']}] {c['type']} (上限:{c['max_pts']}pt)": c for c in matched_cards}
    selected_key = st.selectbox("登場日・バージョンを選択してください：", list(card_dict.keys()))
    card = card_dict[selected_key]
    
    st.info(f"🎯 選択中: **{card['name']}** 【{card['type']}】 | 上限タレント: **{card['max_pts']} pt**")

    # --- 2. 監督・ブースター設定 ---
    st.subheader("2. 監督・ブースター設定")
    c1, c2, c3 = st.columns(3)
    with c1:
        manager_mode = st.selectbox("監督の適性値", ["88 (85以上は+3 / 未満は+2)", "87以下 (一律+2)", "なし (+0)"])
    with c2:
        apply_booster = st.checkbox("ブースター効果をONにする", value=True)
    with c3:
        role_type = st.selectbox("育成の狙い", ["裏抜け・突破特化（CF/WG）", "操作感・アシスト特化（OMF）", "守備・対人特化（CB/DMF）"])

    # 役割ごとの最適化ウェイト設定
    if "裏抜け" in role_type:
        weights = {"シュート": 3.0, "パス": 1.0, "ドリブル": 3.0, "クイックネス": 4.5, "脚力": 3.5, "エアバトル": 0.0, "ディフェンス": 0.0}
    elif "操作感" in role_type:
        weights = {"シュート": 2.0, "パス": 3.0, "ドリブル": 4.5, "クイックネス": 4.0, "脚力": 2.5, "エアバトル": 0.0, "ディフェンス": 0.0}
    else:
        weights = {"シュート": 0.0, "パス": 1.0, "ドリブル": 0.5, "クイックネス": 2.0, "脚力": 3.5, "エアバトル": 3.5, "ディフェンス": 5.0}

    # --- 3. 最適化実行 ---
    if st.button("🚀 この選手を最強配分（誤差0pt）で育成する", type="primary"):
        # 数理最適化 (Pulp)
        prob = LpProblem("eFootOpt", LpMaximize)
        x = {(cat, up): LpVariable(f"x_{cat}_{up}", cat="Binary") for cat in CATEGORIES for up in range(17)}
        
        # 目的関数
        prob += lpSum(x[cat, up] * (up * weights[cat]) for cat in CATEGORIES for up in range(17))
        for cat in CATEGORIES:
            prob += lpSum(x[cat, up] for up in range(17)) == 1
        # 制約：上限ptピッタリ
        prob += lpSum(x[cat, up] * COST_TABLE[up] for cat in CATEGORIES for up in range(17)) == card["max_pts"]
        
        # 重み0のカテゴリは0UP（無駄振り防止）
        for cat, w in weights.items():
            if w == 0.0:
                prob += x[cat, 0] == 1
                
        prob.solve()

        # 結果表示
        st.subheader("📋 最適タレントデザイン結果")
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            st.markdown("#### 【タレントポイント振り分け】")
            total_used = 0
            for cat in CATEGORIES:
                for up in range(17):
                    if x[cat, up].value() == 1.0:
                        cost = COST_TABLE[up]
                        total_used += cost
                        st.write(f"- **{cat}**: `+{up} UP` （消費 {cost} pt）")
            st.success(f"**合計使用ポイント: {total_used} / {card['max_pts']} pt (余り: 0 pt)**")
            
        with col_res2:
            st.markdown("#### 【試合中の実効値想定（バフ・ブースト込み）】")
            for s_name, b_val in card["base"].items():
                boost = card["booster"].get(s_name, 0) if apply_booster else 0
                mgr = 3 if (b_val + boost) >= 85 and "88" in manager_mode else (2 if "87" in manager_mode or "88" in manager_mode else 0)
                final_val = b_val + boost + mgr
                st.write(f"- **{s_name}**: `{final_val}` （素:{b_val} + ブースト:+{boost} + 監督:+{mgr}）")

else:
    st.warning("該当する選手が見つかりませんでした。別の名前を入力してください。")
