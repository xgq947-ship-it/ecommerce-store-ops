from typing import Any

import httpx


def build_client(**kwargs: Any) -> httpx.Client:
    return httpx.Client(timeout=kwargs.pop("timeout", 10.0), **kwargs)
