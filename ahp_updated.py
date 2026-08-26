# -*- coding: utf-8 -*-
"""
ماژول AHP با معیارهای جدید استاد:
- Safety (ایمنی)
- Class_Disruption (اختلال در کلاس)  
- Infrastructure_Criticality (بحرانی‌بودن خدمت)

وزن‌ها بر اساس نسبت‌های داده‌شده:
  Safety : Class_Disruption = 3:1
  Safety : Infrastructure_Criticality = 4:1
  Class_Disruption : Infrastructure_Criticality = 2:1
"""

import numpy as np

# شاخص تصادفی Saaty
RI_TABLE = {1: 0.00, 2: 0.00, 3: 0.58, 4: 0.90, 5: 1.12, 6: 1.24, 7: 1.32, 8: 1.41, 9: 1.45}

# معیارهای جدید
CRITERIA_NAMES = ["Safety", "Class_Disruption", "Infrastructure_Criticality"]

# ماتریس مقایسه زوجی بر اساس نسبت‌های استاد:
# S : CD = 3:1  →  S/CD = 3
# S : IC = 4:1  →  S/IC = 4
# CD : IC = 2:1 →  CD/IC = 2
PAIRWISE_MATRIX = [
    [1,     3,     4    ],   # Safety vs [S, CD, IC]
    [1/3,   1,     2    ],   # Class_Disruption vs [S, CD, IC]
    [1/4,   1/2,   1    ],   # Infrastructure_Criticality vs [S, CD, IC]
]


def compute_ahp_weights(matrix=None, criteria_names=None):
    """
    محاسبه وزن معیارها با روش NCS + بررسی سازگاری
    """
    if matrix is None:
        matrix = PAIRWISE_MATRIX
    if criteria_names is None:
        criteria_names = CRITERIA_NAMES

    A = np.array(matrix, dtype=float)
    n = A.shape[0]

    if A.shape[0] != A.shape[1]:
        raise ValueError("ماتریس مقایسه زوجی باید مربعی باشد.")
    if len(criteria_names) != n:
        raise ValueError("تعداد نام معیارها باید با ابعاد ماتریس برابر باشد.")

    # نرمال‌سازی
    col_sums = A.sum(axis=0)
    normalized = A / col_sums
    weights = normalized.mean(axis=1)

    # محاسبه سازگاری
    Aw = A @ weights
    lambdas = Aw / weights
    lambda_max = float(lambdas.mean())

    CI = (lambda_max - n) / (n - 1) if n > 1 else 0.0
    RI = RI_TABLE.get(n, 1.49)
    CR = (CI / RI) if RI != 0 else 0.0

    return {
        "weights": dict(zip(criteria_names, weights.tolist())),
        "lambda_max": lambda_max,
        "CI": CI,
        "CR": CR,
        "is_consistent": CR < 0.1,
    }


if __name__ == "__main__":
    result = compute_ahp_weights()
    print("وزن معیارها (جدید):")
    for name, w in result["weights"].items():
        print(f"  {name}: {w:.4f}")
    print(f"\nنسبت‌های تائید:")
    w = result["weights"]
    print(f"  Safety : Class_Disruption = {w['Safety']/w['Class_Disruption']:.2f}:1 (انتظار: 3:1)")
    print(f"  Safety : Infrastructure = {w['Safety']/w['Infrastructure_Criticality']:.2f}:1 (انتظار: 4:1)")
    print(f"  Class_Disruption : Infrastructure = {w['Class_Disruption']/w['Infrastructure_Criticality']:.2f}:1 (انتظار: 2:1)")
    print(f"\nCR: {result['CR']:.4f} (سازگار: {result['is_consistent']})")
