"""Read only allowlisted provider settings; never evaluate or export dotenv contents."""

import os
from pathlib import Path

SETTINGS = {
    "SEC_USER_AGENT": ("SEC_USER_AGENT", "BAGHUNTER_SEC_USER_AGENT"),
    "FINVIZ_TOKEN": ("FINVIZ_TOKEN",),
}


def provider_setting(name: str, env_file: Path = Path(".env")) -> str:
    if name not in SETTINGS:
        raise ValueError("Unsupported provider setting")
    keys = SETTINGS[name]
    for key in keys:
        if os.environ.get(key, "").strip():
            return os.environ[key].strip()
    if not env_file.exists():
        return ""
    with env_file.open("rb") as stream:
        body = stream.read(64 * 1024 + 1)
    if len(body) > 64 * 1024:
        raise ValueError("Provider configuration exceeds size limit")
    values = {}
    for line in body.decode("utf-8-sig").splitlines():
        line = line.strip()
        if line.startswith("export "):
            line = line[7:].lstrip()
        key, separator, value = line.partition("=")
        if not separator or key.strip() not in keys:
            continue
        key, value = key.strip(), value.strip()
        if key in values:
            raise ValueError("Duplicate provider configuration key")
        if value.startswith(('"', "'")):
            quote = value[0]
            end = value.find(quote, 1)
            if end < 0 or (
                value[end + 1 :].strip() and not value[end + 1 :].lstrip().startswith("#")
            ):
                raise ValueError("Invalid quoted provider configuration")
            value = value[1:end]
        else:
            value = value.split(" #", 1)[0].rstrip()
        if any(ord(c) < 32 for c in value):
            raise ValueError("Invalid provider configuration characters")
        values[key] = value
    return next((values[k] for k in keys if values.get(k)), "")
