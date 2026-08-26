# -*- coding: utf-8 -*-
"""
ماژول تخصیص: مدل برنامه‌ریزی خطی (Linear Programming) با PuLP برای تخصیص
شکایات به کارکنان بر اساس تخصص، در دسترس‌بودن و کمینه‌سازی فاصله.

مدل ریاضی
----------
متغیر تصمیم:
    x_ij = 1  اگر شکایت i به کارمند j تخصیص یابد، در غیر این صورت 0

تابع هدف:
    Minimize  Z = sum_i sum_j  d_ij * x_ij

محدودیت‌ها:
    1) هر شکایتی که حداقل یک کارمند واجد شرایط (هم‌تخصص و آزاد) دارد،
       دقیقاً به یک کارمند تخصیص یابد:      sum_j x_ij = 1
    2) هر کارمند حداکثر به یک شکایت تخصیص یابد:   sum_i x_ij <= 1
    3) تخصص: فقط زوج‌های (i, j) که تخصص کارمند j با دسته‌بندی شکایت i
       یکسان است، به‌عنوان متغیر ساخته می‌شوند (سایر زوج‌ها اصلاً وارد مدل نمی‌شوند)
    4) در دسترس‌بودن: فقط کارکنانی با وضعیت "آزاد" وارد مجموعه متغیرها می‌شوند

توجه: مدل به‌صورت عمومی برای چند شکایت هم‌زمان نوشته شده تا در نسخه‌های
بعدی (فراتر از Demo تک‌شکایتی) بدون تغییر ساختاری قابل استفاده باشد.
"""

import pulp


def assign_complaints(complaints, workers):
    """
    Parameters
    ----------
    complaints : list[dict]
        هر دیکشنری شامل حداقل {"id": ..., "category": ...}
    workers : list[dict]
        هر دیکشنری شامل {"worker_id", "skill", "distance", "available"}
        available باید مقدار "آزاد" یا "مشغول" باشد.

    Returns
    -------
    dict
        {"status": "assigned" | "no_eligible_worker",
         "assignments": {complaint_id: worker_id, ...}}
    """
    # ساخت زوج‌های مجاز: فقط هم‌تخصص و آزاد
    eligible_pairs = []
    for c in complaints:
        for w in workers:
            if w["skill"] == c["category"] and w["available"] == "آزاد":
                eligible_pairs.append((c["id"], w["worker_id"]))

    if not eligible_pairs:
        return {"status": "no_eligible_worker", "assignments": {}}

    prob = pulp.LpProblem("Complaint_Assignment", pulp.LpMinimize)

    x = {
        (cid, wid): pulp.LpVariable(f"x_{cid}_{wid}", cat="Binary")
        for (cid, wid) in eligible_pairs
    }

    distance_by_worker = {w["worker_id"]: w["distance"] for w in workers}

    # تابع هدف: کمینه‌سازی مجموع فاصله کارکنان تخصیص‌یافته تا محل شکایت
    prob += pulp.lpSum(
        distance_by_worker[wid] * x[(cid, wid)] for (cid, wid) in eligible_pairs
    )

    # محدودیت ۱: هر شکایتِ دارای گزینه واجد شرایط، دقیقاً به یک کارمند تخصیص یابد
    complaint_ids_with_option = {cid for (cid, wid) in eligible_pairs}
    for cid in complaint_ids_with_option:
        keys = [k for k in x if k[0] == cid]
        prob += pulp.lpSum(x[k] for k in keys) == 1

    # محدودیت ۲: هر کارمند حداکثر یک شکایت در آن واحد بپذیرد
    worker_ids = {wid for (cid, wid) in eligible_pairs}
    for wid in worker_ids:
        keys = [k for k in x if k[1] == wid]
        prob += pulp.lpSum(x[k] for k in keys) <= 1

    prob.solve(pulp.PULP_CBC_CMD(msg=0))

    assignments = {}
    if pulp.LpStatus[prob.status] == "Optimal":
        for (cid, wid), var in x.items():
            if var.value() == 1:
                assignments[cid] = wid

    status = "assigned" if assignments else "no_eligible_worker"
    return {"status": status, "assignments": assignments}


if __name__ == "__main__":
    # تست مستقل مطابق سناریوی مشخصات (بخش ۲۲ و ۳۴)
    demo_complaints = [{"id": "C001", "category": "تأسیسات"}]
    demo_workers = [
        {"worker_id": "W1", "skill": "برق", "distance": 5, "available": "آزاد"},
        {"worker_id": "W2", "skill": "تأسیسات", "distance": 2, "available": "آزاد"},
        {"worker_id": "W3", "skill": "نظافت", "distance": 8, "available": "آزاد"},
        {"worker_id": "W4", "skill": "عمومی", "distance": 4, "available": "آزاد"},
        {"worker_id": "W5", "skill": "تأسیسات", "distance": 3, "available": "آزاد"},
    ]
    result = assign_complaints(demo_complaints, demo_workers)
    print(result)
    # انتظار می‌رود: C001 -> W2 (چون بین W2 و W5 هم‌تخصص، W2 فاصله کمتری دارد: 2 < 3)
