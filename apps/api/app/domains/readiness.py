def calculate_readiness(payload: dict) -> tuple[int, list[str]]:
    score = 70
    reasons: list[str] = []
    sleep = payload.get("sleep_hours")
    if sleep is not None:
        if sleep >= 7.5:
            score += 10
            reasons.append("Sleep duration supports normal training readiness.")
        elif sleep < 6:
            score -= 18
            reasons.append("Short sleep is the largest readiness constraint today.")
    energy = payload.get("energy")
    if energy is not None:
        score += (energy - 3) * 5
        if energy <= 2:
            reasons.append("Low self-reported energy reduces the score.")
    soreness = payload.get("soreness")
    if soreness is not None:
        score -= max(0, soreness - 2) * 6
        if soreness >= 4:
            reasons.append("High soreness suggests holding volume or effort.")
    stress = payload.get("stress")
    if stress is not None:
        score -= max(0, stress - 3) * 4
    score = max(20, min(100, score))
    if not reasons:
        reasons.append("Available recovery inputs are close to your normal range.")
    return score, reasons[:2]

