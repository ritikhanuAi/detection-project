import os
import platform


def get_cpu_brand() -> str:
    """Detects CPU brand name dynamically from host or env override."""
    env_cpu = os.getenv("HARDWARE_CPU_NAME")
    if env_cpu:
        return env_cpu

    try:
        with open("/proc/cpuinfo", "r") as f:
            for line in f:
                if "model name" in line:
                    brand = line.split(":", 1)[1].strip()
                    if "i5" in brand:
                        return "Intel Core i5"
                    if "i7" in brand:
                        return "Intel Core i7"
                    if "i9" in brand:
                        return "Intel Core i9"
                    if "Ryzen" in brand:
                        return "AMD Ryzen"
                    return brand.split("@")[0].strip().replace("(R)", "").replace("(TM)", "")
    except Exception:
        pass

    proc = platform.processor()
    return proc if proc and proc != "x86_64" else "Intel Core i5"


def format_model_name(raw_model: str) -> str:
    """Formats raw VLM model string into a clean UI label."""
    m = raw_model.lower()
    if "qwen2.5vl" in m or "qwen2.5-vl" in m:
        return "Qwen2.5-VL"
    if "moondream" in m:
        return "Moondream"
    if "llama" in m:
        return "Llama"
    return raw_model.split(":")[0].capitalize()


def system_hardware_context(request):
    """Context processor providing dynamic system hardware and model info to templates."""
    raw_model = os.getenv("VLM_MODEL", "qwen2.5vl:3b")
    model_name = format_model_name(raw_model)
    cpu_name = get_cpu_brand()

    return {
        "SYSTEM_CPU_NAME": cpu_name,
        "SYSTEM_VLM_MODEL": model_name,
        "SYSTEM_RAW_MODEL": raw_model,
        "SYSTEM_FOOTER_INFO": f"Local Offline CPU Inference • {cpu_name} • Quantized {model_name}",
    }
