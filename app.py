import streamlit as st
import pandas as pd
import requests

# ===============================
# CONFIG
# ===============================
import os
API_KEY = st.secrets["GOOGLE_API_KEY"]

# ===============================
# GOOGLE MAPS API
# ===============================
MAX_CALLS = 100

if "api_calls" not in st.session_state:
    st.session_state.api_calls = 0

def get_commute_time(origin, destination, mode="driving"):
    
    # ✅ 限制调用
    if st.session_state.api_calls >= MAX_CALLS:
        st.warning("⚠️ Daily API limit reached")
        return None

    if not destination or mode == "Select...":
        return None

    url = "https://maps.googleapis.com/maps/api/distancematrix/json"
    params = {
        "origins": origin,
        "destinations": destination,
        "mode": mode.lower(),
        "key": API_KEY
    }

    try:
        res = requests.get(url, params=params).json()

        element = res["rows"][0]["elements"][0]

        if element["status"] != "OK":
            return None

        # ✅ 每次成功调用 +1
        st.session_state.api_calls += 1

        seconds = element["duration"]["value"]
        return round(seconds / 60, 1)

    except:
        return None

# ===============================
# SCORING FUNCTIONS
# ===============================
def commute_score(x):
    if x is None:
        return 0
    return 100 if x <= 20 else 70 if x <= 40 else 40

def price_score(x):
    if x is None:
        return 0

    try:
        x = float(x)
    except:
        return 0

    if x <= 700:
        return 100
    elif x <= 1000:
        return 70
    else:
        return 40

def yes_no_score(x):
    return 100 if x else 40

def roommate_score(x):
    if x is None:
        return 0

    try:
        x = int(x)   # ✅ 强制转成数字
    except:
        return 0

    if x == 1:
        return 100
    elif x == 2:
        return 80
    elif x >= 3:
        return 60
    else:
        return 40

def environment_score(row):

    values = []

    for col in ["Quiet (0-100)", "Safety (0-100)", "Cleanliness (0-100)"]:
        x = row[col]

        if x is not None:
            try:
                values.append(float(x))
            except:
                pass

    if len(values) == 0:
        return 0

    return sum(values) / len(values)

# ===============================
# UI
# ===============================
st.title("🏠 Smart Rental Decision System")
st.caption(f"API calls used: {st.session_state.api_calls} / {MAX_CALLS}")
st.caption(
    "Transit times may be significantly longer at night due to limited service."
)

st.markdown("""
<style>
header {
    visibility: hidden;
}
</style>
""", unsafe_allow_html=True)

st.markdown(
    """
    <style>
    .stApp {
        background-image: url("https://images.unsplash.com/photo-1560185007-cde436f6a4d0");
        background-size: cover;
        background-position: center;
    }

    /* ✅ 关键：内容区域加白色半透明背景 */
    .block-container {
        background-color: rgba(255, 255, 255, 0.9);
        padding: 30px;
        border-radius: 15px;
    }
    </style>
    """,
    unsafe_allow_html=True
)

st.markdown("""
<style>

/* ✅ 只改“已选部分”（蓝色线） */
.stSlider div[data-baseweb="slider"] > div > div {
    background-color: #4A90E2 !important;
}

/* ✅ 滑块按钮 */
.stSlider [role="slider"] {
    background-color: #4A90E2 !important;
    border: 2px solid white !important;
}

/* ✅ 数值颜色（小红字） */
.stSlider span {
    color: #4A90E2 !important;
}

</style>
""", unsafe_allow_html=True)

work_mode = st.selectbox(
    "Transport mode to Work",
    ["Select...", "driving", "transit", "walking"]
)

study_mode = st.selectbox(
    "Transport mode to Study",
    ["Select...", "driving", "transit", "walking"]
)

work_address = st.text_input("Work location (optional)")
study_address = st.text_input("Study location (optional)")

st.subheader("Enter rental information")
st.caption("Optional: Leave blank if not applicable")

# ✅ 用户填写真实房源信息
data = st.data_editor(
    pd.DataFrame({
        "Address": [""],
        "Price": [None],
        "Private_bathroom": [False],
        "Can_Cook": [False],
        "Parking": [False],
        "Roommates": [None],
        "Quiet (0-100)": [None],
        "Safety (0-100)": [None],
        "Cleanliness (0-100)": [None],

    }),
    num_rows="dynamic",
    use_container_width=True
)

st.subheader("Select factors & weights (total = 100)")

weights = {
    "price": st.slider("Price", 0, 100, 0),
    "work": st.slider("Work commute", 0, 100, 0),
    "study": st.slider("Study commute", 0, 100, 0),
    "bathroom": st.slider("Private bathroom", 0, 100, 0),
    "cook": st.slider("Cooking allowed", 0, 100, 0),
    "parking": st.slider("Parking", 0, 100, 0),
    "roommate": st.slider("Roommate Count", 0, 100, 0),
    "environment": st.slider("Environment", 0, 100, 0)
}

if sum(weights.values()) != 100:
    st.warning("Total weight must be 100")
    st.stop()

# ===============================
# CALCULATION
# ===============================
if st.button("Calculate"):

    df = data.copy()
    
    if work_address and work_mode != "Select...":
        df["Work_Commute"] = df["Address"].apply(
        lambda x: get_commute_time(x, work_address, work_mode)
    )
    else:
        df["Work_Commute"] = None
    

    if study_address and study_mode != "Select...":
        df["Study_Commute"] = df["Address"].apply(
        lambda x: get_commute_time(x, study_address, study_mode)
    )
    else:
        df["Study_Commute"] = None 
    
    df["price_score"] = df["Price"].apply(price_score)
    df["work_score"] = df["Work_Commute"].apply(commute_score)
    df["study_score"] = df["Study_Commute"].apply(commute_score)
    df["bathroom_score"] = df["Private_bathroom"].apply(yes_no_score)
    df["cook_score"] = df["Can_Cook"].apply(yes_no_score)
    df["parking_score"] = df["Parking"].apply(yes_no_score)
    df["roommate_score"] = df["Roommates"].apply(roommate_score)
    df["environment_score"] = df.apply(environment_score, axis=1)

    df["total_score"] = (
        df["price_score"] * weights["price"]
        + df["work_score"] * weights["work"]
        + df["study_score"] * weights["study"]
        + df["bathroom_score"] * weights["bathroom"]
        + df["cook_score"] * weights["cook"]
        + df["parking_score"] * weights["parking"]
        + df["roommate_score"] * weights["roommate"]
        + df["environment_score"] * weights["environment"]
    ) / 100
    
    df["total_score"] = df["total_score"].round(2)
    df["environment_score"] = df["environment_score"].round(2)

    st.subheader("Results")
    st.dataframe(df.sort_values("total_score", ascending=False))
