# -*- coding: utf-8 -*-

import os
from datetime import datetime

import pandas as pd
import streamlit as st

from ahp_updated import (
    compute_ahp_weights,
    PAIRWISE_MATRIX,
    CRITERIA_NAMES
)

from scoring_updated import (
    SAFETY_OPTIONS,
    CLASS_DISRUPTION_OPTIONS,
    INFRASTRUCTURE_OPTIONS,
    CATEGORY_OPTIONS,
    compute_priority_score,
    compute_waiting_time_multiplier,
    priority_level
)

from optimization import assign_complaints


# =========================================================
# مسیر فایل‌ها
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

COMPLAINTS_FILE = os.path.join(BASE_DIR, "complaints.csv")
WORKERS_FILE = os.path.join(BASE_DIR, "workers.csv")


# =========================================================
# تنظیمات Streamlit
# =========================================================

st.set_page_config(
    page_title="سامانه هوشمند مدیریت شکایات",
    layout="wide"
)


# =========================================================
# توابع مربوط به شکایت‌ها
# =========================================================

def load_complaints():

    columns = [
        "id",
        "timestamp",
        "description",
        "location",
        "category",
        "safety_score",
        "disruption_score",
        "infrastructure_score",
        "waiting_multiplier",
        "priority_score",
        "priority_level",
        "status",
        "assigned_worker_id",
        "assigned_worker_name"
    ]

    empty_df = pd.DataFrame(columns=columns)

    if not os.path.exists(COMPLAINTS_FILE):
        return empty_df

    try:

        df = pd.read_csv(
            COMPLAINTS_FILE,
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

    except pd.errors.EmptyDataError:
        return empty_df

    # اگر بعضی ستون‌ها وجود نداشته باشند
    for col in columns:

        if col not in df.columns:
            df[col] = ""

    # ترتیب ستون‌ها
    df = df[columns]

    # حذف فاصله‌های اضافی
    for col in df.columns:

        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    # تبدیل ستون‌های عددی
    numeric_columns = [
        "safety_score",
        "disruption_score",
        "infrastructure_score",
        "waiting_multiplier",
        "priority_score"
    ]

    for col in numeric_columns:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    return df


def save_complaints(df):

    df.to_csv(
        COMPLAINTS_FILE,
        index=False,
        encoding="utf-8-sig"
    )


# =========================================================
# توابع مربوط به کارکنان
# =========================================================

def load_workers():

    columns = [
        "worker_id",
        "name",
        "skill",
        "distance",
        "available"
    ]

    empty_df = pd.DataFrame(columns=columns)

    if not os.path.exists(WORKERS_FILE):
        return empty_df

    try:

        df = pd.read_csv(
            WORKERS_FILE,
            encoding="utf-8-sig",
            dtype=str
        ).fillna("")

    except pd.errors.EmptyDataError:
        return empty_df

    # اطمینان از وجود ستون‌ها
    for col in columns:

        if col not in df.columns:
            df[col] = ""

    df = df[columns]

    # حذف فاصله‌های اضافی
    for col in df.columns:

        if df[col].dtype == object:
            df[col] = df[col].str.strip()

    # فاصله عددی
    df["distance"] = pd.to_numeric(
        df["distance"],
        errors="coerce"
    ).fillna(0)

    return df


def save_workers(df):

    df.to_csv(
        WORKERS_FILE,
        index=False,
        encoding="utf-8-sig"
    )


# =========================================================
# به‌روزرسانی امتیازهای زمانی
# =========================================================

def refresh_dynamic_scores(df, weights):

    if df.empty:
        return df

    now = datetime.now()

    changed = False

    for i, row in df.iterrows():

        waiting = compute_waiting_time_multiplier(
            row["timestamp"],
            now
        )

        score = compute_priority_score(
            row["safety_score"],
            row["disruption_score"],
            row["infrastructure_score"],
            weights,
            waiting
        )

        level, _ = priority_level(score)

        if (
            df.at[i, "waiting_multiplier"] != waiting
            or
            df.at[i, "priority_score"] != score
            or
            df.at[i, "priority_level"] != level
        ):

            df.at[i, "waiting_multiplier"] = waiting
            df.at[i, "priority_score"] = score
            df.at[i, "priority_level"] = level

            changed = True

    if changed:
        save_complaints(df)

    return df


# =========================================================
# نقش کاربر
# =========================================================

def get_role():

    role = st.query_params.get(
        "role",
        "user"
    ).lower()

    if role in ("user", "staff", "admin"):
        return role

    return "user"


# =========================================================
# صفحه کاربر
# =========================================================

def page_user():

    st.title(
        "🏫 سامانه هوشمند مدیریت شکایات دانشکده"
    )

    st.caption(
        "ثبت شکایت توسط کاربر"
    )

    st.caption(
        "Location: A11"
    )

    # -----------------------------------------------------
    # محاسبه وزن‌های AHP
    # -----------------------------------------------------

    ahp_result = compute_ahp_weights()

    weights = ahp_result["weights"]

    # -----------------------------------------------------
    # فرم ثبت شکایت
    # -----------------------------------------------------

    with st.form(
        "complaint_form",
        clear_on_submit=False
    ):

        description = st.text_area(
            "📝 توضیحات شکایت *",
            placeholder=(
                "لطفاً مشکل، خرابی یا درخواست "
                "خود را کامل توضیح دهید."
            ),
            height=140
        )

        col1, col2 = st.columns(2)

        with col1:

            location = "A11"

            st.text_input(
                "📍 مکان",
                value="A11",
                disabled=True
            )

        with col2:

            category = st.selectbox(
                "🔧 دسته‌بندی خدمات *",
                CATEGORY_OPTIONS
            )

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

        submitted = st.form_submit_button(
            "✅ ثبت شکایت",
            use_container_width=True
        )

    # =====================================================
    # بعد از ثبت شکایت
    # =====================================================

    if submitted:

        # -------------------------------------------------
        # بررسی توضیحات
        # -------------------------------------------------

        if not description.strip():

            st.error(
                "ثبت شکایت بدون توضیحات امکان‌پذیر نیست."
            )

            return

        # -------------------------------------------------
        # خواندن شکایت‌ها
        # -------------------------------------------------

        df = load_complaints()

        # -------------------------------------------------
        # ساخت ID جدید
        # -------------------------------------------------

        next_num = 1

        if not df.empty:

            nums = pd.to_numeric(
                df["id"]
                .astype(str)
                .str.extract(r"(\d+)$")[0],
                errors="coerce"
            )

            if nums.notna().any():

                next_num = int(
                    nums.max()
                ) + 1

        complaint_id = f"C{next_num:03d}"

        # -------------------------------------------------
        # زمان ثبت
        # -------------------------------------------------

        timestamp = datetime.now().isoformat(
            timespec="seconds"
        )

        # -------------------------------------------------
        # ضریب زمانی
        # -------------------------------------------------

        waiting = compute_waiting_time_multiplier(
            timestamp
        )

        # -------------------------------------------------
        # محاسبه امتیاز
        # -------------------------------------------------

        score = compute_priority_score(
            SAFETY_OPTIONS[safety_answer],
            CLASS_DISRUPTION_OPTIONS[disruption_answer],
            INFRASTRUCTURE_OPTIONS[infrastructure_answer],
            weights,
            waiting
        )

        level, emoji = priority_level(
            score
        )

        # -------------------------------------------------
        # ساخت رکورد شکایت
        # -------------------------------------------------

        row = {

            "id": complaint_id,

            "timestamp": timestamp,

            "description": description.strip(),

            "location": location,

            "category": category,

            "safety_score":
                SAFETY_OPTIONS[safety_answer],

            "disruption_score":
                CLASS_DISRUPTION_OPTIONS[
                    disruption_answer
                ],

            "infrastructure_score":
                INFRASTRUCTURE_OPTIONS[
                    infrastructure_answer
                ],

            "waiting_multiplier": waiting,

            "priority_score": score,

            "priority_level": level,

            "status": "ثبت‌شده",

            "assigned_worker_id": "",

            "assigned_worker_name": ""
        }

        # -------------------------------------------------
        # اضافه کردن شکایت
        # -------------------------------------------------

        df = pd.concat(
            [
                df,
                pd.DataFrame([row])
            ],
            ignore_index=True
        )

        # =================================================
        # ذخیره اولیه شکایت
        # =================================================

        save_complaints(df)

        # =================================================
        # تخصیص خودکار
        # =================================================

        workers = load_workers()

        # فقط کارکنان آزاد
        available_workers = workers[
            workers["available"]
            .astype(str)
            .str.strip()
            .str.lower()
            == "آزاد"
        ].copy()

        # رکورد شکایت برای مدل
        complaint_records = [
            row
        ]

        # اجرای مدل تخصیص
        result = assign_complaints(
            complaint_records,
            available_workers.to_dict("records")
        )

        # =================================================
        # اگر تخصیص موفق بود
        # =================================================

        if result["status"] == "assigned":

            assigned_worker_id = (
                result["assignments"]
                .get(complaint_id)
            )

            if assigned_worker_id:

                # پیدا کردن کارمند
                worker_match = workers[
                    workers["worker_id"]
                    .astype(str)
                    .str.strip()
                    .str.upper()
                    ==
                    assigned_worker_id
                    .strip()
                    .upper()
                ]

                if not worker_match.empty:

                    worker_name = (
                        worker_match
                        .iloc[0]["name"]
                    )

                    # -------------------------------------
                    # ثبت کارمند روی شکایت
                    # -------------------------------------

                    complaint_index = df.index[
                        df["id"] == complaint_id
                    ]

                    if len(complaint_index):

                        i = complaint_index[0]

                        df.at[
                            i,
                            "assigned_worker_id"
                        ] = assigned_worker_id

                        df.at[
                            i,
                            "assigned_worker_name"
                        ] = worker_name

                        df.at[
                            i,
                            "status"
                        ] = "تخصیص‌یافته"

                    # -------------------------------------
                    # تغییر وضعیت کارمند
                    # -------------------------------------

                    worker_index = worker_match.index[0]

                    workers.at[
                        worker_index,
                        "available"
                    ] = "مشغول"

                    # -------------------------------------
                    # ذخیره نهایی
                    # -------------------------------------

                    save_complaints(df)

                    save_workers(workers)

                    st.success(
                        f"✅ شکایت {complaint_id} "
                        f"با موفقیت به "
                        f"{worker_name} تخصیص یافت."
                    )

                else:

                    st.warning(
                        "شکایت ثبت شد، اما "
                        "کارمند تخصیص‌یافته پیدا نشد."
                    )

            else:

                st.warning(
                    "شکایت ثبت شد، اما "
                    "کارمندی به آن تخصیص نیافت."
                )

        # =================================================
        # اگر کارمند مناسب پیدا نشد
        # =================================================

        else:

            st.warning(
                "⚠️ شکایت ثبت شد، اما در حال حاضر "
                "کارمند آزاد و هم‌تخصصی برای "
                "تخصیص پیدا نشد."
            )

        # -------------------------------------------------
        # نمایش نتیجه
        # -------------------------------------------------

        st.metric(
            "سطح اولویت",
            f"{emoji} {level}"
        )

        st.metric(
            "امتیاز اولویت",
            f"{score:.2f}"
        )

        # -------------------------------------------------
        # رفرش برای نمایش وضعیت جدید
        # -------------------------------------------------

        st.rerun()


# =========================================================
# صفحه کارکنان
# =========================================================

def page_staff():

    st.title(
        "👷 صفحه کارکنان"
    )

    workers = load_workers()

    staff_id = st.text_input(
        "شناسه کارمند",
        placeholder="مثلاً W1"
    )

    if not staff_id:

        st.info(
            "شناسه کارمند خود را وارد کنید."
        )

        return

    # -----------------------------------------------------
    # پیدا کردن کارمند
    # -----------------------------------------------------

    staff = workers[
        workers["worker_id"]
        .astype(str)
        .str.strip()
        .str.upper()
        ==
        staff_id.strip().upper()
    ]

    if staff.empty:

        st.error(
            "شناسه کارمند پیدا نشد."
        )

        return

    worker = staff.iloc[0]

    worker_id = worker["worker_id"]

    st.subheader(
        f"مأموریت‌های {worker['name']}"
    )

    # =====================================================
    # وضعیت کارمند
    # =====================================================

    with st.container(border=True):

        st.write(
            f"**وضعیت فعلی شما:** "
            f"{worker['available']}"
        )

        new_status = st.selectbox(
            "ثبت وضعیت من",
            ["آزاد", "مشغول"],
            index=(
                0
                if worker["available"] == "آزاد"
                else 1
            ),
            key="staff_status_select"
        )

        if st.button(
            "💾 ثبت وضعیت",
            key="save_status_btn"
        ):

            all_workers = load_workers()

            widx = all_workers.index[
                all_workers["worker_id"]
                .astype(str)
                .str.strip()
                .str.upper()
                ==
                worker_id
                .strip()
                .upper()
            ]

            if len(widx):

                all_workers.at[
                    widx[0],
                    "available"
                ] = new_status

                save_workers(
                    all_workers
                )

                st.success(
                    f"وضعیت شما به "
                    f"«{new_status}» ثبت شد."
                )

                st.rerun()

    # =====================================================
    # بارگذاری شکایت‌ها
    # =====================================================

    ahp_result = compute_ahp_weights()

    df = load_complaints()

    df = refresh_dynamic_scores(
        df,
        ahp_result["weights"]
    )

    # =====================================================
    # فقط کارهای همین کارمند
    # =====================================================

    tasks = df[
        df["assigned_worker_id"]
        .astype(str)
        .str.strip()
        .str.upper()
        ==
        worker_id
        .strip()
        .upper()
    ].copy()

    if tasks.empty:

        st.info(
            "در حال حاضر کاری به شما تخصیص داده نشده است."
        )

        return

    # =====================================================
    # کارهای فعال و انجام‌شده
    # =====================================================

    active_tasks = tasks[
        tasks["status"] != "انجام‌شده"
    ]

    done_tasks = tasks[
        tasks["status"] == "انجام‌شده"
    ]

    # =====================================================
    # تعداد کارهای جدید
    # =====================================================

    new_count = (
        active_tasks["status"]
        == "تخصیص‌یافته"
    ).sum()

    if new_count > 0:

        st.warning(
            f"🔔 شما {new_count} کار جدید "
            f"تخصیص‌یافته دارید که هنوز "
            f"شروع نشده است."
        )

    # =====================================================
    # نمایش کارها
    # =====================================================

    if active_tasks.empty:

        st.info(
            "در حال حاضر کار فعالی برای شما ثبت نشده است."
        )

    for _, r in active_tasks.iterrows():

        with st.container(border=True):

            if r["status"] == "تخصیص‌یافته":

                badge = "🆕 جدید"

            else:

                badge = "🔧 در حال انجام"

            st.markdown(
                f"### {r['id']} — "
                f"{r['category']} "
                f"&nbsp; `{badge}`"
            )

            st.write(
                f"**چه کاری؟** "
                f"{r['description']}"
            )

            st.write(
                f"**کجا؟** "
                f"{r['location']}"
            )

            st.write(
                f"**اولویت:** "
                f"{r['priority_level']} — "
                f"{float(r['priority_score']):.2f}"
            )

            st.write(
                f"**وضعیت:** "
                f"{r['status']}"
            )

            col_a, col_b = st.columns(2)

            # -------------------------------------------------
            # شروع کار
            # -------------------------------------------------

            with col_a:

                if r["status"] == "تخصیص‌یافته":

                    if st.button(
                        "🔧 شروع کار",
                        key=f"start_{r['id']}",
                        use_container_width=True
                    ):

                        idx = df.index[
                            df["id"] == r["id"]
                        ]

                        if len(idx):

                            df.at[
                                idx[0],
                                "status"
                            ] = "در حال انجام"

                            save_complaints(df)

                        st.rerun()

            # -------------------------------------------------
            # اتمام کار
            # -------------------------------------------------

            with col_b:

                if st.button(
                    "✅ اتمام کار",
                    key=f"done_{r['id']}",
                    use_container_width=True
                ):

                    idx = df.index[
                        df["id"] == r["id"]
                    ]

                    if len(idx):

                        df.at[
                            idx[0],
                            "status"
                        ] = "انجام‌شده"

                        save_complaints(df)

                    # آزاد کردن کارمند
                    all_workers = load_workers()

                    widx = all_workers.index[
                        all_workers["worker_id"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        ==
                        worker_id
                        .strip()
                        .upper()
                    ]

                    if len(widx):

                        all_workers.at[
                            widx[0],
                            "available"
                        ] = "آزاد"

                        save_workers(
                            all_workers
                        )

                    st.success(
                        f"کار {r['id']} تکمیل شد "
                        f"و وضعیت شما به «آزاد» بازگشت."
                    )

                    st.rerun()

    # =====================================================
    # کارهای تکمیل‌شده
    # =====================================================

    if not done_tasks.empty:

        with st.expander(
            f"✅ کارهای تکمیل‌شده "
            f"({len(done_tasks)})"
        ):

            for _, r in done_tasks.iterrows():

                st.write(
                    f"**{r['id']}** — "
                    f"{r['category']} — "
                    f"{r['description']}"
                )


# =========================================================
# صفحه مدیر
# =========================================================

def page_admin():

    st.title(
        "👨‍💼 پنل مدیر"
    )

    password = st.text_input(
        "کد دسترسی مدیر",
        type="password"
    )

    if password != "1234":

        st.info(
            "برای ورود به پنل مدیر "
            "کد دسترسی را وارد کنید."
        )

        return

    # -----------------------------------------------------
    # داده‌ها
    # -----------------------------------------------------

    ahp_result = compute_ahp_weights()

    weights = ahp_result["weights"]

    complaints = load_complaints()

    complaints = refresh_dynamic_scores(
        complaints,
        weights
    )

    workers = load_workers()

    # -----------------------------------------------------
    # تب‌ها
    # -----------------------------------------------------

    tabs = st.tabs(
        [
            "📋 شکایات",
            "⚙️ تخصیص کار",
            "📐 AHP",
            "🧮 مدل ریاضی",
            "👷 کارکنان"
        ]
    )

    # =====================================================
    # تب شکایت‌ها
    # =====================================================

    with tabs[0]:

        st.subheader(
            "همه شکایت‌ها"
        )

        if complaints.empty:

            st.info(
                "هنوز شکایتی ثبت نشده است."
            )

        else:

            show = complaints[
                [
                    "id",
                    "description",
                    "location",
                    "category",
                    "priority_level",
                    "priority_score",
                    "status",
                    "assigned_worker_name"
                ]
            ].copy()

            show.columns = [
                "شناسه",
                "توضیحات",
                "مکان",
                "دسته",
                "اولویت",
                "امتیاز",
                "وضعیت",
                "کارمند"
            ]

            st.dataframe(
                show,
                use_container_width=True,
                hide_index=True
            )

    # =====================================================
    # تب تخصیص
    # =====================================================

    with tabs[1]:

        st.subheader(
            "تخصیص خودکار شکایت‌ها به کارکنان"
        )

        # -------------------------------------------------
        # شکایت‌های تخصیص‌نیافته
        # -------------------------------------------------

        unassigned = complaints[
            complaints["assigned_worker_id"]
            .astype(str)
            .str.strip()
            == ""
        ]

        if unassigned.empty:

            st.info(
                "شکایتی برای تخصیص وجود ندارد."
            )

        else:

            # ---------------------------------------------
            # کارکنان آزاد
            # ---------------------------------------------

            worker_records = workers[
                workers["available"]
                .astype(str)
                .str.strip()
                == "آزاد"
            ].to_dict("records")

            complaint_records = (
                unassigned
                .to_dict("records")
            )

            # ---------------------------------------------
            # اجرای مدل
            # ---------------------------------------------

            result = assign_complaints(
                complaint_records,
                worker_records
            )

            # ---------------------------------------------
            # تخصیص موفق
            # ---------------------------------------------

            if result["status"] == "assigned":

                st.success(
                    "✅ مدل تخصیص با موفقیت اجرا شد."
                )

                changed = False

                for cid, wid in result[
                    "assignments"
                ].items():

                    # پیدا کردن شکایت
                    idx = complaints.index[
                        complaints["id"] == cid
                    ]

                    # پیدا کردن کارمند
                    wrow = workers[
                        workers["worker_id"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        ==
                        wid
                        .strip()
                        .upper()
                    ]

                    if (
                        len(idx)
                        and
                        not wrow.empty
                    ):

                        i = idx[0]

                        complaints.at[
                            i,
                            "assigned_worker_id"
                        ] = wid

                        complaints.at[
                            i,
                            "assigned_worker_name"
                        ] = wrow.iloc[0]["name"]

                        complaints.at[
                            i,
                            "status"
                        ] = "تخصیص‌یافته"

                        changed = True

                    # -------------------------------------
                    # مشغول کردن کارمند
                    # -------------------------------------

                    widx = workers.index[
                        workers["worker_id"]
                        .astype(str)
                        .str.strip()
                        .str.upper()
                        ==
                        wid
                        .strip()
                        .upper()
                    ]

                    if len(widx):

                        workers.at[
                            widx[0],
                            "available"
                        ] = "مشغول"

                # -----------------------------------------
                # ذخیره
                # -----------------------------------------

                if changed:

                    save_complaints(
                        complaints
                    )

                    save_workers(
                        workers
                    )

                # -----------------------------------------
                # نمایش تخصیص‌ها
                # -----------------------------------------

                assigned = complaints[
                    complaints[
                        "assigned_worker_id"
                    ].astype(str).str.strip()
                    != ""
                ][
                    [
                        "id",
                        "description",
                        "location",
                        "category",
                        "assigned_worker_id",
                        "assigned_worker_name",
                        "status"
                    ]
                ]

                st.dataframe(
                    assigned,
                    use_container_width=True,
                    hide_index=True
                )

            # ---------------------------------------------
            # عدم وجود کارمند مناسب
            # ---------------------------------------------

            else:

                st.warning(
                    "⚠️ برای شکایت‌های موجود، "
                    "کارمند آزاد و هم‌تخصص پیدا نشد."
                )

                st.dataframe(
                    workers[
                        [
                            "worker_id",
                            "name",
                            "skill",
                            "distance",
                            "available"
                        ]
                    ],
                    use_container_width=True,
                    hide_index=True
                )

    # =====================================================
    # تب AHP
    # =====================================================

    with tabs[2]:

        st.subheader(
            "جدول AHP"
        )

        ahp_df = pd.DataFrame(
            PAIRWISE_MATRIX,
            index=CRITERIA_NAMES,
            columns=CRITERIA_NAMES
        )

        st.dataframe(
            ahp_df,
            use_container_width=True
        )

        weights_df = pd.DataFrame(
            {
                "معیار": list(
                    weights.keys()
                ),

                "وزن": [
                    round(v, 6)
                    for v in weights.values()
                ]
            }
        )

        st.dataframe(
            weights_df,
            use_container_width=True,
            hide_index=True
        )

        st.write(
            f"λmax = "
            f"{ahp_result['lambda_max']:.6f}"
        )

        st.write(
            f"CI = "
            f"{ahp_result['CI']:.6f}"
        )

        st.write(
            f"CR = "
            f"{ahp_result['CR']:.6f}"
        )

        if ahp_result["is_consistent"]:

            st.success(
                "سازگار"
            )

        else:

            st.error(
                "ناسازگار"
            )

    # =====================================================
    # تب مدل ریاضی
    # =====================================================

    with tabs[3]:

        st.subheader(
            "مدل ریاضی تخصیص"
        )

        st.markdown(
            """
**متغیر تصمیم:**  
`x_ij = 1` اگر شکایت i به کارمند j تخصیص یابد، در غیر این صورت 0.

**تابع هدف:**  
`Minimize Z = Σ d_ij x_ij`

**محدودیت‌ها:**

1. هر شکایت دارای کارمند واجد شرایط دقیقاً به یک کارمند تخصیص می‌یابد.
2. هر کارمند در یک زمان حداکثر یک شکایت می‌پذیرد.
3. فقط تطابق تخصص شکایت و کارمند مجاز است.
4. فقط کارکنان با وضعیت «آزاد» وارد مدل می‌شوند.
"""
        )

        st.code(
            """
min Σ d_ij x_ij

Σ_j x_ij = 1

Σ_i x_ij ≤ 1

x_ij ∈ {0,1}
""",
            language="text"
        )

    # =====================================================
    # تب کارکنان
    # =====================================================

    with tabs[4]:

        st.subheader(
            "فهرست کارکنان"
        )

        st.dataframe(
            workers[
                [
                    "worker_id",
                    "name",
                    "skill",
                    "distance",
                    "available"
                ]
            ],
            use_container_width=True,
            hide_index=True
        )


# =========================================================
# اجرای برنامه
# =========================================================

role = get_role()

if role == "staff":

    page_staff()

elif role == "admin":

    page_admin()

else:

    page_user()