from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MonetizationState:
    show_ads: bool
    paid_features_enabled: bool
    trial_days_remaining: int


def derive_monetization_state(*, is_paid_user: bool, ads_enabled: bool, trial_days: int) -> MonetizationState:
    if is_paid_user:
        return MonetizationState(show_ads=False, paid_features_enabled=True, trial_days_remaining=0)

    return MonetizationState(
        show_ads=bool(ads_enabled),
        paid_features_enabled=False,
        trial_days_remaining=max(0, int(trial_days)),
    )