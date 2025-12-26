def browser_name(agent: str) -> str:
    agent = agent.lower()

    if "edg" in agent:
        return "Edge"
    if "chrome" in agent and "safari" in agent:
        return "Chrome"
    if "safari" in agent and "chrome" not in agent:
        return "Safari"
    if "firefox" in agent:
        return "Firefox"

    return "Unknown"