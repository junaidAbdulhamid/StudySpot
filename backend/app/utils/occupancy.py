def classify_occupancy(percent: int) -> str:
    if not 0 <= percent <= 100:
        raise ValueError("Occupancy must be between 0 and 100")
    return (
        "available"
        if percent < 40
        else "moderate"
        if percent < 65
        else "busy"
        if percent < 85
        else "full"
    )
