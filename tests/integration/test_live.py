import io
import os

import pytest

from igt.cli import main

pytestmark = pytest.mark.integration


@pytest.mark.skipif(
    not os.environ.get("IGT_TEST_URL"), reason="set IGT_TEST_URL to a reel with speech"
)
def test_real_reel_produces_text():
    out, err = io.StringIO(), io.StringIO()
    code = main(
        [os.environ["IGT_TEST_URL"], "--model", os.environ.get("IGT_MODEL", "tiny")],
        stdout=out,
        stderr=err,
    )
    assert code == 0, err.getvalue()
    assert out.getvalue().strip()
