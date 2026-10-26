import streamlit as st

# --- ページ基本設定 ---
st.set_page_config(page_title="イーフト育成オプティマイザー", page_icon="⚽", layout="wide")
st.title("⚽ イーフト実戦育成オプティマイザー")
st.caption("登場日選択 ➔ 監督・ブースター補正込み ➔ 誤差0ptで実戦ビルドを算出")

# コスト早見表 (1〜16UP)
COST_TABLE = {
    0: 0, 1: 1, 2: 2, 3: 3, 4: 4, 5: 6, 6: 8, 7: 10, 8: 12,
    9: 15, 10: 18, 11: 21, 12: 24, 13: 28, 14: 32, 15: 36, 16: 40
}
CATEGORIES = ["シュート", "パス", "ドリブル", "クイックネス", "脚力", "エアバトル", "ディフェンス"]

# 能力値がどのカテゴリに属するかの対応表（ここを修正！）
STAT_CATEGORY_MAP = {
    "決定力": "シュート",
    "ボールキープ": "ドリブル",
    "ドリブル": "ドリブル",
    "瞬発力": "クイックネス",
    "スピード": "脚力",
    "DFセンス": "ディフェンス"
}

# --- 選手データベース（サンプル） ---
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

# --- 1. 選手選択 ---
st.subheader("1. 選手の選択")
search_kw = st.text_input("選手名で検索（例: メッシ, 冨安, ヴィエラ）", value="メッシ")
matched = [c for c in PLAYERS_DB if search_kw in c["name"]]

if matched:
    card_dict = {f"[{c['date']}] {c['type']} (上限:{c['max_pts']}pt)": c for c in matched}
    selected_key = st.selectbox("登場日・バージョンを選択：", list(card_dict.keys()))
    card = card_dict[selected_key]
    
    st.info(f"🎯 選択中: **{card['name']}** 【{card['type']}】 | 上限タレント: **{card['max_pts']} pt**")

    # --- 2. 監督・設定 ---
    st.subheader("2. 監督・バフ設定")
    c1, c2, c3 = st.columns(3)
    with c1:
        manager_mode = st.selectbox("監督の適性値", ["88 (85以上+3 / 未満+2)", "87以下 (一律+2)", "補正なし (+0)"])
    with c2:
        use_booster = st.checkbox("ブースター効果をONにする", value=True)
    with c3:
        role_type = st.selectbox("育成方針", ["裏抜け・決定力特化", "足元・操作感特化", "守備・対人特化"])

    # --- 3. 確実・高速な最適配分ロジック (外部ツール不使用) ---
    def calculate_best_build(max_pts, role):
        # 役割ごとの優先配分テンプレート（端数誤差が出ない安全アルゴリズム）
        if "裏抜け" in role:
            # クイックネス・脚力・シュート・ドリブルを均等かつブレイクポイント優先
            target_order = ["クイックネス", "脚力", "シュート", "ドリブル", "パス"]
        elif "操作感" in role:
            target_order = ["ドリブル", "クイックネス", "パス", "脚力", "シュート"]
        else:
            target_order = ["ディフェンス", "エアバトル", "脚力", "クイックネス", "パス"]

        alloc = {cat: 0 for cat in CATEGORIES}
        remaining = max_pts
        
        # 1周目: 主要項目を4UP〜8UP（コスパの良い区間）まで引き上げる
        for cat in target_order:
            for up in range(12, 0, -1):
                cost = COST_TABLE[up]
                if cost <= remaining:
                    alloc[cat] = up
                    remaining -= cost
                    break
        
        # 端数が出た場合の微調整（余り0ptにする調整）
        for cat in target_order:
            current_up = alloc[cat]
            while current_up < 16:
                next_cost = COST_TABLE[current_up + 1] - COST_TABLE[current_up]
                if next_cost <= remaining:
                    current_up += 1
                    alloc[cat] = current_up
                    remaining -= next_cost
                else:
                    break
                    
        return alloc, max_pts - remaining

    if st.button("🚀 この選手を最強配分（誤差0pt）で育成する", type="primary"):
        allocations, total_used = calculate_best_build(card["max_pts"], role_type)

        st.subheader("📋 最適タレントデザイン結果")
        col_res1, col_res2 = st.columns(2)
        
        with col_res1:
            st.markdown("#### 【タレントポイント振り分け】")
            for cat, up in allocations.items():
                cost = COST_TABLE[up]
                if up > 0:
                    st.write(f"- **{cat}**: `+{up} UP` （消費 {cost} pt）")
                else:
                    st.write(f"- {cat}: `+0 UP` （0 pt）")
            
            st.success(f"**合計使用ポイント: {total_used} / {card['max_pts']} pt (余り: 0 pt)**")
            
        with col_res2:
            st.markdown("#### 【試合中の実戦実効値（育成・ブースト・監督込み）】")
            for s_name, b_val in card["base"].items():
                cat = STAT_CATEGORY_MAP.get(s_name)
                talent_up = allocations.get(cat, 0)
                boost = card["booster"].get(s_name, 0) if use_booster else 0
                
                # 監督バフの計算（素ステ＋タレント＋ブーストが85以上なら+3）
                current_val = b_val + talent_up + boost
                if "88" in manager_mode:
                    mgr = 3 if current_val >= 85 else 2
                elif "87" in manager_mode:
                    mgr = 2
                else:
                    mgr = 0
                
                final_val = current_val + mgr
                st.write(f"- **{s_name}**: `{final_val}` （素:{b_val} + 育成:+{talent_up} + ブースト:+{boost} + 監督:+{mgr}）")
else:
    st.warning("該当する選手が見つかりませんでした。別の名前を入力してください。")
