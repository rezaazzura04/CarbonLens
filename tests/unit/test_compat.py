"""
Regression test for a real reported bug: the app crashed on startup with
    TypeError: LayoutsMixin.container() got an unexpected keyword argument 'key'
because components/sidebar_nav.py called st.container(key=...) unconditionally,
and the key parameter for st.container() was not available in every build the
app can actually run under (it postdates the pinned 1.35.0 floor, and has been
reported as inconsistently packaged even in versions that document it).

components/compat.py fixes this the same way it already handles the
use_container_width/width split: detect what the running st.container()
actually supports, at runtime, rather than crashing when it doesn't.
"""
import pytest


def test_container_key_kwargs_never_raises_on_the_running_streamlit():
    """
    The actual bug, reproduced directly: calling st.container(**kwargs) with
    whatever container_key_kwargs() returns must never raise TypeError,
    regardless of which Streamlit build is actually running the test.
    """
    from components.compat import container_key_kwargs

    kwargs = container_key_kwargs("regression_test_wrap")
    assert kwargs in ({}, {"key": "regression_test_wrap"})

    import streamlit as st
    with st.container(**kwargs):
        pass  # if this raises TypeError, the bug has regressed


def test_container_key_kwargs_matches_actual_container_signature():
    """
    container_key_kwargs() must agree with what st.container() actually
    accepts on THIS build -- not with a hardcoded version number, since
    key-parameter availability has been reported to vary even across
    versions that document support for it.
    """
    import inspect
    import streamlit as st
    from components.compat import container_key_kwargs

    supports_key = "key" in inspect.signature(st.container).parameters
    kwargs = container_key_kwargs("x")

    if supports_key:
        assert kwargs == {"key": "x"}
    else:
        assert kwargs == {}


def test_container_key_kwargs_returns_plain_dict():
    from components.compat import container_key_kwargs

    result = container_key_kwargs("any_key")
    assert isinstance(result, dict)
    assert set(result.keys()) <= {"key"}
