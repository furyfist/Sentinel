from agent.config import COST_SPIKE_MULTIPLIER, ERROR_CASCADE_THRESHOLD, AGENT_LOOP_GENERATION_THRESHOLD


def detect_cost_spike(current_hourly_cost: float, baseline_avg: float, threshold: float = COST_SPIKE_MULTIPLIER) -> bool:
    return current_hourly_cost > baseline_avg * threshold


def detect_error_cascade(error_count: int, retry_cost: float, threshold: float = ERROR_CASCADE_THRESHOLD) -> bool:
    return (error_count * retry_cost) > threshold


def detect_agent_loop(generation_count: int, threshold: int = AGENT_LOOP_GENERATION_THRESHOLD) -> bool:
    return generation_count > threshold
