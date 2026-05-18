from datetime import datetime, timedelta
from enum import Enum

class SubscriptionStatus(str, Enum):
    ACTIVE = "active"
    PAUSED = "paused"
    CANCELLED = "cancelled"
    EXPIRED = "expired"

SUBSCRIPTIONS = {}  # In-memory store; use DB in production

def create_subscription(user_id, product, budget, frequency_days=30):
    """
    Create a recurring subscription
    frequency_days: 30 for monthly, 7 for weekly, etc.
    """
    sub_id = f"sub_{user_id}_{datetime.now().timestamp()}"
    subscription = {
        "id": sub_id,
        "user_id": user_id,
        "product": product,
        "budget": budget,
        "frequency_days": frequency_days,
        "status": SubscriptionStatus.ACTIVE,
        "created_at": datetime.now().isoformat(),
        "next_renewal": (datetime.now() + timedelta(days=frequency_days)).isoformat(),
        "total_charged": 0,
        "charge_count": 0
    }
    SUBSCRIPTIONS[sub_id] = subscription
    return subscription

def get_subscription(sub_id):
    """Retrieve subscription by ID"""
    return SUBSCRIPTIONS.get(sub_id)

def cancel_subscription(sub_id):
    """Cancel an active subscription"""
    if sub_id in SUBSCRIPTIONS:
        SUBSCRIPTIONS[sub_id]["status"] = SubscriptionStatus.CANCELLED
        return True
    return False

def pause_subscription(sub_id):
    """Pause a subscription temporarily"""
    if sub_id in SUBSCRIPTIONS:
        SUBSCRIPTIONS[sub_id]["status"] = SubscriptionStatus.PAUSED
        return True
    return False

def resume_subscription(sub_id):
    """Resume a paused subscription"""
    if sub_id in SUBSCRIPTIONS:
        SUBSCRIPTIONS[sub_id]["status"] = SubscriptionStatus.ACTIVE
        SUBSCRIPTIONS[sub_id]["next_renewal"] = (datetime.now() + timedelta(days=SUBSCRIPTIONS[sub_id]["frequency_days"])).isoformat()
        return True
    return False

def get_due_subscriptions():
    """Get all subscriptions due for renewal"""
    now = datetime.now()
    due = []
    for sub_id, sub in SUBSCRIPTIONS.items():
        if sub["status"] == SubscriptionStatus.ACTIVE:
            next_renewal = datetime.fromisoformat(sub["next_renewal"])
            if next_renewal <= now:
                due.append((sub_id, sub))
    return due

def update_subscription_charge(sub_id, amount):
    """Update subscription after successful charge"""
    if sub_id in SUBSCRIPTIONS:
        sub = SUBSCRIPTIONS[sub_id]
        sub["total_charged"] += amount
        sub["charge_count"] += 1
        sub["next_renewal"] = (datetime.now() + timedelta(days=sub["frequency_days"])).isoformat()
        return sub
    return None
