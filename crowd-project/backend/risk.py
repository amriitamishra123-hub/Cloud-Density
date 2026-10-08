"""
Risk Assessment Module for Crowd Density & Stampede Risk Prediction.
Implements rule-based heuristics to determine risk severity levels.
"""

from typing import List

# Risk level classification labels
LABELS: List[str] = ["Low", "Medium", "High"]

# Configurable threshold constants
LOW_T: int = 50       # Density count threshold for Low risk
HIGH_T: int = 150     # Density count threshold for High risk (Stampede danger)
TURB_T: float = 2.0   # Motion turbulence threshold to elevate risk severity

def rule_risk(count: float, turb: float) -> int:
    """
    Evaluates rule-based crowd stampede risk level (0, 1, 2).

    Args:
        count: Estimated crowd headcount.
        turb: Motion turbulence (std of optical flow velocity magnitude).

    Returns:
        int: 0 for "Low", 1 for "Medium", 2 for "High".

    Logic:
      - 0 if count < LOW_T (Low density)
      - 1 if count < HIGH_T (Medium density)
      - 2 otherwise (High density)
      - If turbulence > TURB_T and level > 0, raise level by one (max 2).
    """
    if count < LOW_T:
        level = 0
    elif count < HIGH_T:
        level = 1
    else:
        level = 2

    # High turbulence elevates elevated/medium risk to high risk
    if turb > TURB_T and level > 0:
        level = min(2, level + 1)

    return level
