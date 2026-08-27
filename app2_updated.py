# -*- coding: utf-8 -*-
import os
from urllib.parse import parse_qs
from datetime import datetime
import pandas as pd
import streamlit as st

from ahp_updated import compute_ahp_weights, PAIRWISE_MATRIX, CRITERIA_NAMES
from scoring_updated import (
    SAFETY_OPTIONS, CLASS_DISRUPTION_OPTIONS, INFRASTRUCTURE_OPTIONS,
    CATEGORY_OPTIONS, compute_priority_score, compute_waiting_time_multiplier,
    priority_level
)
from optimization import assign_complaints

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
COMPLAINTS_FILE = os.path.join(BASE_DIR, "complaints.csv")
WORKERS_FILE = os.path.join(BASE_DIR, "workers.csv")

st.set_page_config(page_title="سامانه هوشمند مدیریت شکایات", layout="wide")

def load_complaints():
    if not os.path.exists(COMPLAINTS_FILE):
        return pd.DataFrame(columns=[
            "id","timestamp","description","location","category","safety_score",
            "disruption_score","infrastructure_score","waiting_multiplier",
            "priority_score","priority_level","status","assigned_worker_id",
            "assigned_worker_name"
        ])
    df = pd.read_csv(COMPLAINTS_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    for c in ["safety_score","disruption_score","infrastructure_score",
              "waiting_multiplier","priority_score"]:
        df[c] = pd.to_numeric(df[c], errors="coerce").fillna(0)
    return df

def save_complaints(df):
    df.to_csv(COMPLAINTS_FILE, index=False, encoding="utf-8-sig")

def load_workers():
    df = pd.read_csv(WORKERS_FILE, encoding="utf-8-sig", dtype=str).fillna("")
    df["distance"] = pd.to_numeric(df["distance"], errors="coerce").fillna(0)
    return df

def save_workers(df):
    df.to_csv(WORKERS_FILE, index=False, encoding="utf-8-sig")

def refresh_dynamic_scores(df, weights):
    """
    امتیاز اولویت را هر بار بر اساس زمان فعلی (نه فقط لحظه ثبت) دوباره
    محاسبه می‌کند تا ضریب افزایش تأخیر (waiting_multiplier) واقعاً اثر بگذارد.
    نتیجه در همان دیتافریم به‌روزرسانی و در فایل ذخیره می‌شود.
    """
    if df.empty:
        return df
    now = datetime.now()
    changed = False
    for i, row in df.iterrows():
        waiting = compute_waiting_time_multiplier(row["timestamp"], now)
        score = compute_priority_score(
            row["safety_score"], row["disruption_score"], row["infrastructure_score"],
            weights, waiting
        )
        level, _ = priority_level(score)
        if (df.at[i, "waiting_multiplier"] != waiting or
                df.at[i, "priority_score"] != score or
                df.at[i, "priority_level"] != level):
            df.at[i, "waiting_multiplier"] = waiting
            df.at[i, "priority_score"] = score
            df.at[i, "priority_level"] = level
            changed = True
    if changed:
        save_complaints(df)
    return df

def get_role():
    role = st.query_params.get("role", "user").lower()
    return role if role in ("user", "staff", "admin") else "user"
def page_user():
    st.title("🏫 سامانه هوشمند مدیریت شکایات دانشکده")
    st.caption("ثبت شکایت توسط کاربر  ")
    st.caption("location : A11")
    ahp_result = compute_ahp_weights()
    weights = ahp_result["weights"]

    with st.form("complaint_form", clear_on_submit=False):
        description = st.text_area(
            "📝 توضیحات شکایت *",
            placeholder="لطفاً مشکل، خرابی یا درخواست خود را کامل توضیح دهید.",
            height=140
        )
        col1, col2 = st.columns(2)
        with col1:
            location = "A11"
        with col2:
            category = st.selectbox("🔧 دسته‌بندی خدمات *", CATEGORY_OPTIONS)

        safety_answer = st.radio(
            "این مشکل چه میزان بر ایمنی اثر دارد؟",
            list(SAFETY_OPTIONS.keys())
        )
        disruption_answer = st.radio(
            "این مشکل چه میزان بر برگزاری کلاس اثر دارد؟",
            list(CLASS_DISRUPTION_OPTIONS.keys())
        )
        infrastructure_answer = st.radio(
            "این مشکل چه میزان برای زیرساخت و خدمت حیاتی است؟",
            list(INFRASTRUCTURE_OPTIONS.keys())
        )

        submitted = st.form_submit_button("✅ ثبت شکایت", use_container_width=True)

    if submitted:
        if not description.strip():
            st.error("ثبت شکایت بدون توضیحات امکان‌پذیر نیست.")
            return
       

        df = load_complaints()
        next_num = 1
        if not df.empty:
            nums = pd.to_numeric(df["id"].astype(str).str.extract(r"(\d+)$")[0], errors="coerce")
            if nums.notna().any():
                next_num = int(nums.max()) + 1
        complaint_id = f"C{next_num:03d}"
        timestamp = datetime.now().isoformat(timespec="seconds")
        waiting = compute_waiting_time_multiplier(timestamp)

        score = compute_priority_score(
            SAFETY_OPTIONS[safety_answer],
            CLASS_DISRUPTION_OPTIONS[disruption_answer],
            INFRASTRUCTURE_OPTIONS[infrastructure_answer],
            weights, waiting
        )
        level, emoji = priority_level(score)

        row = {
            "id": complaint_id,
            "timestamp": timestamp,
            "description": description.strip(),
            "location": location.strip(),
            "category": category,
            "safety_score": SAFETY_OPTIONS[safety_answer],
            "disruption_score": CLASS_DISRUPTION_OPTIONS[disruption_answer],
            "infrastructure_score": INFRASTRUCTURE_OPTIONS[infrastructure_answer],
            "waiting_multiplier": waiting,
            "priority_score": score,
            "priority_level": level,
            "status": "ثبت‌شده",
            "assigned_worker_id": "",
            "assigned_worker_name": ""
        }
        df = pd.concat([df, pd.DataFrame([row])], ignore_index=True)
        save_complaints(df)

        st.success(f"شکایت {complaint_id} با موفقیت ثبت شد.")
        st.metric("سطح اولویت", f"{emoji} {level}")
        st.metric("امتیاز اولویت", f"{score:.2f}")

def page_staff():
    st.title("👷 صفحه کارکنان")
    workers = load_workers()
    staff_id = st.text_input("شناسه کارمند", placeholder="مثلاً W1")

    if not staff_id:
        st.info("شناسه کارمند خود را وارد کنید.")
        return

    staff = workers[workers["worker_id"].str.upper() == staff_id.strip().upper()]
    if staff.empty:
        st.error("شناسه کارمند پیدا نشد.")
        return

    worker = staff.iloc[0]
    st.subheader(f"مأموریت‌های {worker['name']}")

    ahp_result = compute_ahp_weights()
    df = load_complaints()
    df = refresh_dynamic_scores(df, ahp_result["weights"])
    tasks = df[df["assigned_worker_id"].str.upper() == worker["worker_id"].upper()].copy()

    if tasks.empty:
        st.info("در حال حاضر کاری به شما تخصیص داده نشده است.")
        return

    for _, r in tasks.iterrows():
        with st.container(border=True):
            st.markdown(f"### {r['id']} — {r['category']}")
            st.write(f"**چه کاری؟** {r['description']}")
            st.write(f"**کجا؟** {r['location']}")
            st.write(f"**اولویت:** {r['priority_level']} — {float(r['priority_score']):.2f}")
            st.write(f"**وضعیت:** {r['status']}")

def page_admin():
    st.title("👨‍💼 پنل مدیر")
    password = st.text_input("کد دسترسی مدیر", type="password")
    if password != "1234":
        st.info("برای ورود به پنل مدیر کد دسترسی را وارد کنید.")
        return

    ahp_result = compute_ahp_weights()
    weights = ahp_result["weights"]
    complaints = load_complaints()
    complaints = refresh_dynamic_scores(complaints, weights)
    workers = load_workers()

    tabs = st.tabs(["📋 شکایات", "⚙️ تخصیص کار", "📐 AHP", "🧮 مدل ریاضی", "👷 کارکنان"])

    with tabs[0]:
        st.subheader("همه شکایت‌ها")
        if complaints.empty:
            st.info("هنوز شکایتی ثبت نشده است.")
        else:
            show = complaints[[
                "id","description","location","category","priority_level",
                "priority_score","status","assigned_worker_name"
            ]].copy()
            show.columns = ["شناسه","توضیحات","مکان","دسته","اولویت","امتیاز","وضعیت","کارمند"]
            st.dataframe(show, use_container_width=True, hide_index=True)

    with tabs[1]:
        st.subheader("تخصیص خودکار شکایت‌ها به کارکنان")
        # فقط شکایاتی که هنوز به کارمندی تخصیص نیافته‌اند وارد مدل شوند
        unassigned = complaints[complaints["assigned_worker_id"] == ""]
        if unassigned.empty:
            st.info("شکایتی برای تخصیص وجود ندارد.")
        else:
            # فقط کارکنانی که هم‌اکنون «آزاد» هستند وارد مدل شوند
            worker_records = workers[workers["available"] == "آزاد"].to_dict("records")
            complaint_records = unassigned.to_dict("records")
            result = assign_complaints(complaint_records, worker_records)

            if result["status"] == "assigned":
                st.success("مدل تخصیص با موفقیت اجرا شد.")
                changed = False
                for cid, wid in result["assignments"].items():
                    idx = complaints.index[complaints["id"] == cid]
                    wrow = workers[workers["worker_id"] == wid]
                    if len(idx) and not wrow.empty:
                        i = idx[0]
                        complaints.at[i, "assigned_worker_id"] = wid
                        complaints.at[i, "assigned_worker_name"] = wrow.iloc[0]["name"]
                        complaints.at[i, "status"] = "تخصیص‌یافته"
                        changed = True
                    # کارمند تخصیص‌یافته را «مشغول» علامت بزن تا دوباره انتخاب نشود
                    widx = workers.index[workers["worker_id"] == wid]
                    if len(widx):
                        workers.at[widx[0], "available"] = "مشغول"
                if changed:
                    save_complaints(complaints)
                    save_workers(workers)

                assigned = complaints[complaints["assigned_worker_id"] != ""][[
                    "id","description","location","category",
                    "assigned_worker_id","assigned_worker_name","status"
                ]]
                st.dataframe(assigned, use_container_width=True, hide_index=True)
            else:
                st.warning("برای شکایت‌های موجود، کارمند آزاد و هم‌تخصص پیدا نشد.")
                st.dataframe(
                    workers[["worker_id","name","skill","distance","available"]],
                    use_container_width=True, hide_index=True
                )

    with tabs[2]:
        st.subheader("جدول AHP")
        ahp_df = pd.DataFrame(PAIRWISE_MATRIX, index=CRITERIA_NAMES, columns=CRITERIA_NAMES)
        st.dataframe(ahp_df, use_container_width=True)
        weights_df = pd.DataFrame({
            "معیار": list(weights.keys()),
            "وزن": [round(v, 6) for v in weights.values()]
        })
        st.dataframe(weights_df, use_container_width=True, hide_index=True)
        st.write(f"λmax = {ahp_result['lambda_max']:.6f}")
        st.write(f"CI = {ahp_result['CI']:.6f}")
        st.write(f"CR = {ahp_result['CR']:.6f}")
        st.success("سازگار" if ahp_result["is_consistent"] else "ناسازگار")

    with tabs[3]:
        st.subheader("مدل ریاضی تخصیص")
        st.markdown("""
**متغیر تصمیم:** `x_ij = 1` اگر شکایت i به کارمند j تخصیص یابد، در غیر این صورت 0.

**تابع هدف:**
`Minimize Z = Σ d_ij x_ij`

**محدودیت‌ها:**
1. هر شکایت دارای کارمند واجد شرایط دقیقاً به یک کارمند تخصیص می‌یابد.
2. هر کارمند در یک زمان حداکثر یک شکایت می‌پذیرد.
3. فقط تطابق تخصص شکایت و کارمند مجاز است.
4. فقط کارکنان با وضعیت «آزاد» وارد مدل می‌شوند.
        """)
        st.code("min Σ d_ij x_ij\nΣ_j x_ij = 1\nΣ_i x_ij ≤ 1\nx_ij ∈ {0,1}", language="text")

    with tabs[4]:
        st.subheader("فهرست کارکنان")
        st.dataframe(
            workers[["worker_id","name","skill","distance","available"]],
            use_container_width=True, hide_index=True
        )

role = get_role()
if role == "staff":
    page_staff()
elif role == "admin":
    page_admin()
else:
    page_user()