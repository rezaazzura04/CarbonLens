"""
CarbonLens - Streamlit version compatibility helpers.

Section 29 guard: Streamlit APIs differ across versions. The pinned runtime
is 1.35.0, but newer releases deprecate `use_container_width` (announced
removal after 2025-12-31) in favour of `width="stretch" | "content"`.
Passing `width=` to 1.35 raises TypeError; keeping the old kwarg breaks on
newer releases. This module resolves the call shape once at import time so
the rest of the codebase is version-agnostic.
"""
from __future__ import annotations

import inspect
import streamlit as st

_STREAMLIT_VERSION = tuple(int(p) for p in st.__version__.split(".")[:2])

# `st.container(key=...)` was introduced after the pinned 1.35.0 floor (it
# ships with the `st-key-<key>` CSS-class convention documented from 1.39.0
# onward) — confirmed as the root cause of a real startup crash
# (`LayoutsMixin.container() got an unexpected keyword argument 'key'`) on
# an environment actually running an older/incompatible build. Detected by
# introspecting the live signature rather than gating on a version number:
# `key` support has been reported inconsistent across platforms/wheels even
# within versions that are documented to include it, so checking what the
# installed build can actually do is more reliable than trusting its
# version string alone.
_CONTAINER_SUPPORTS_KEY = "key" in inspect.signature(st.container).parameters


def container_key_kwargs(key: str) -> dict:
    """
    Return {"key": key} if the running st.container() accepts a key
    parameter, else {} — degrades to an unstyled but fully functional
    container instead of crashing the app.

    Usage:
        with st.container(**container_key_kwargs(f"{key}_wrap")):
            ...
    """
    if _CONTAINER_SUPPORTS_KEY:
        return {"key": key}
    return {}


def width_stretch_kwargs() -> dict:
    """
    Return full-width kwargs valid for the RUNNING Streamlit version.

    st.button / st.download_button / st.plotly_chart (and peers):
      - Streamlit >= 1.43 : {"width": "stretch"}
      - Streamlit <  1.43 : {"use_container_width": True}

    Usage:
        st.plotly_chart(fig, **width_stretch_kwargs(), config={...})
        if st.button("Go", key="k", **width_stretch_kwargs()):
    """
    if _STREAMLIT_VERSION >= (1, 43):
        return {"width": "stretch"}
    return {"use_container_width": True}
