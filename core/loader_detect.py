def detect_loader(filename: str) -> str:
    name = filename.lower()

    if "quilt" in name:
        return "Quilt"
    if "fabric" in name:
        return "Fabric"
    if "forge" in name or "neoforge" in name:
        return "Forge"

    return "Unknown"
