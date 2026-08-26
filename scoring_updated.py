# -*- coding: utf-8 -*-
"""
ماژول امتیازدهی جدید:

معیار 1: Safety (ایمنی)
  - هیچ تأثیری بر ایمنی ندارد: 1
  - ممکن است در آینده باعث مشکل ایمنی شود: 5
  - در حال حاضر خطر ایمنی ایجاد می‌کند: 7
  - خطر ایمنی جدی و فوری ایجاد می‌کند: 9

معیار 2: Class_Disruption (اختلال در کلاس)
  - خیر، هیچ اختلالی ایجاد نکرده: 1
  - اختلال جزئی ایجاد کرده: 3
  - اختلال قابل توجه ایجاد کرده: 5
  - برگزاری کلاس را مختل یا متوقف کرده: 9

معیار 3: Infrastructure_Criticality (بحرانی‌بودن خدمت)
  - خدمت غیر بحرانی (نظافت، تزئین و تجمیل): 1
  - خدمت نسبتاً بحرانی (نظام‌های کمکی): 5
  - خدمت بسیار بحرانی (برق، آب، تأسیسات اساسی): 8
  - خدمت حیاتی (سیستم‌های فوری، ایمنی): 10

ضریب زمانی (Waiting Time Multiplier):
  - هر روز تاخیر افزایش میدهد
  - فرمول: multiplier = 1 + 0.1 * days_delayed
"""

from datetime import datetime

SAFETY_OPTIONS = {
    "هیچ تأثیری بر ایمنی ندارد": 1,
    "ممکن است در آینده باعث مشکل ایمنی شود": 5,
    "در حال حاضر خطر ایمنی ایجاد می‌کند": 7,
    "خطر ایمنی جدی و فوری ایجاد می‌کند": 9,
}

CLASS_DISRUPTION_OPTIONS = {
    "خیر، هیچ اختلالی ایجاد نکرده": 1,
    "اختلال جزئی ایجاد کرده": 3,
    "اختلال قابل توجه ایجاد کرده": 5,
    "برگزاری کلاس را مختل یا متوقف کرده": 9,
}

INFRASTRUCTURE_OPTIONS = {
    "خدمت غیر بحرانی (نظافت، تزئین و تجمیل)": 1,
    "خدمت نسبتاً بحرانی (نظام‌های کمکی)": 5,
    "خدمت بسیار بحرانی (برق، آب، تأسیسات اساسی)": 8,
    "خدمت حیاتی (سیستم‌های فوری، ایمنی)": 10,
}

CATEGORY_OPTIONS = ["برق", "تأسیسات", "نظافت", "عمومی"]

def compute_waiting_time_multiplier(timestamp_str: str, now: datetime = None) -> float:
    if now is None:
        now = datetime.now()
    try:
        ts = datetime.fromisoformat(timestamp_str)
    except (ValueError, TypeError):
        return 1.0
    days_delayed = (now - ts).days
    return max(1.0, 1.0 + (0.1 * days_delayed))

def compute_priority_score(safety: int, class_disruption: int, infrastructure: int,
                          weights: dict, waiting_multiplier: float = 1.0) -> float:
    base_score = (
        weights["Safety"] * safety +
        weights["Class_Disruption"] * class_disruption +
        weights["Infrastructure_Criticality"] * infrastructure
    )
    return base_score * waiting_multiplier

def priority_level(score: float) -> tuple:
    if score >= 7:
        return "بحرانی", "🔴"
    elif score >= 5:
        return "بالا", "🟠"
    elif score >= 3:
        return "متوسط", "🟡"
    else:
        return "پایین", "🟢"
