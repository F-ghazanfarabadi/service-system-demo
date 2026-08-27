# -*- coding: utf-8 -*-

import pulp


def normalize_text(value):
    """
    نرمال‌سازی متن فارسی برای جلوگیری از خطاهای تطبیق
    ناشی از فاصله، نیم‌فاصله و حروف عربی/فارسی.
    """
    if value is None:
        return ""

    text = str(value).strip()

    # حروف عربی → فارسی
    text = text.replace("ي", "ی")
    text = text.replace("ى", "ی")
    text = text.replace("ك", "ک")

    # نیم‌فاصله و فاصله‌های اضافی
    text = text.replace("\u200c", "")
    text = text.replace("\u200d", "")
    text = " ".join(text.split())

    return text


def assign_complaints(complaints, workers):
    """
    تخصیص شکایت‌ها به کارکنان با استفاده از برنامه‌ریزی خطی.

    معیارهای تخصیص:
    1. تطابق تخصص کارمند با دسته‌بندی شکایت
    2. آزاد بودن کارمند
    3. کمینه‌سازی فاصله
    """

    eligible_pairs = []

    for c in complaints:

        complaint_category = normalize_text(c.get("category", ""))

        for w in workers:

            worker_skill = normalize_text(w.get("skill", ""))
            worker_status = normalize_text(w.get("available", ""))

            if (
                worker_skill == complaint_category
                and worker_status == "آزاد"
            ):
                eligible_pairs.append(
                    (c["id"], w["worker_id"])
                )

    # اگر هیچ زوج واجد شرایطی وجود نداشت
    if not eligible_pairs:
        return {
            "status": "no_eligible_worker",
            "assignments": {}
        }

    # ایجاد مدل
    prob = pulp.LpProblem(
        "Complaint_Assignment",
        pulp.LpMinimize
    )

    # متغیرهای تصمیم
    x = {
        (cid, wid): pulp.LpVariable(
            f"x_{cid}_{wid}",
            cat="Binary"
        )
        for cid, wid in eligible_pairs
    }

    # فاصله هر کارمند
    distance_by_worker = {}

    for w in workers:
        try:
            distance_by_worker[w["worker_id"]] = float(w["distance"])
        except (ValueError, TypeError):
            distance_by_worker[w["worker_id"]] = 0.0

    # تابع هدف: کمینه‌سازی مجموع فاصله
    prob += pulp.lpSum(
        distance_by_worker[wid] * x[(cid, wid)]
        for cid, wid in eligible_pairs
    )

    # هر شکایت واجد شرایط دقیقاً یک کارمند بگیرد
    complaint_ids = {
        cid for cid, wid in eligible_pairs
    }

    for cid in complaint_ids:

        variables = [
            x[(ccid, wid)]
            for ccid, wid in eligible_pairs
            if ccid == cid
        ]

        prob += pulp.lpSum(variables) == 1

    # هر کارمند حداکثر یک شکایت بگیرد
    worker_ids = {
        wid for cid, wid in eligible_pairs
    }

    for wid in worker_ids:

        variables = [
            x[(cid, wwid)]
            for cid, wwid in eligible_pairs
            if wwid == wid
        ]

        prob += pulp.lpSum(variables) <= 1

    # حل مدل
    prob.solve(
        pulp.PULP_CBC_CMD(msg=0)
    )

    # استخراج جواب
    assignments = {}

    if pulp.LpStatus[prob.status] == "Optimal":

        for (cid, wid), variable in x.items():

            if variable.value() == 1:
                assignments[cid] = wid

    if assignments:
        return {
            "status": "assigned",
            "assignments": assignments
        }

    return {
        "status": "no_eligible_worker",
        "assignments": {}
    }


if __name__ == "__main__":

    demo_complaints = [
        {
            "id": "C001",
            "category": "تأسیسات"
        }
    ]

    demo_workers = [
        {
            "worker_id": "W1",
            "skill": "برق",
            "distance": 5,
            "available": "آزاد"
        },
        {
            "worker_id": "W2",
            "skill": "تأسیسات",
            "distance": 2,
            "available": "آزاد"
        },
        {
            "worker_id": "W3",
            "skill": "نظافت",
            "distance": 8,
            "available": "آزاد"
        },
        {
            "worker_id": "W4",
            "skill": "عمومی",
            "distance": 4,
            "available": "آزاد"
        },
        {
            "worker_id": "W5",
            "skill": "تأسیسات",
            "distance": 3,
            "available": "آزاد"
        },
    ]

    result = assign_complaints(
        demo_complaints,
        demo_workers
    )

    print(result)