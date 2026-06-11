"""Safe Mode — يكمل بالمعرفة المحلية إذا تعطلت APIs"""
from systems.circuit_breaker import circuit_breaker

EXTERNAL_SERVICES = ["google_search","wikipedia","virustotal","github"]

def is_safe_mode() -> bool:
    return all(circuit_breaker.is_open(s) for s in EXTERNAL_SERVICES)

def available_services() -> list:
    return [s for s in EXTERNAL_SERVICES if not circuit_breaker.is_open(s)]

def get_mode() -> str:
    avail = available_services()
    if not avail:
        return "SAFE_MODE"
    if len(avail) < len(EXTERNAL_SERVICES) // 2:
        return "DEGRADED"
    return "NORMAL"
