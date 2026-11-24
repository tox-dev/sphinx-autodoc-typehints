from __future__ import annotations

from http.client import HTTPMessage, RemoteDisconnected
from io import BytesIO
from typing import TYPE_CHECKING
from unittest.mock import create_autospec
from urllib.error import HTTPError

from conftest import download_inventory
from conftest import urlopen as open_inventory
from pytest import mark, param, raises

if TYPE_CHECKING:
    from pytest import MonkeyPatch


@mark.parametrize("status", [param(429, id="rate-limit"), param(503, id="unavailable")])
def test_download_inventory_retries_transient_failures(monkeypatch: MonkeyPatch, status: int) -> None:
    delays: list[int] = []
    monkeypatch.setattr("conftest.sleep", delays.append)
    url = "https://docs.python.org/3.14/objects.inv"
    monkeypatch.setattr(
        "conftest.urlopen",
        create_autospec(
            open_inventory,
            side_effect=[
                RemoteDisconnected("connection closed"),
                TimeoutError(),
                HTTPError(url, status, "retry", HTTPMessage(), None),
                BytesIO(b"inventory"),
            ],
        ),
    )

    assert (download_inventory(), delays) == (b"inventory", [1, 2, 4])


@mark.parametrize(
    ("status", "expected_delays"),
    [param(404, [], id="missing"), param(503, [1, 2, 4, 8], id="exhausted")],
)
def test_download_inventory_raises_after_retry_budget(
    monkeypatch: MonkeyPatch, status: int, expected_delays: list[int]
) -> None:
    delays: list[int] = []
    monkeypatch.setattr("conftest.sleep", delays.append)
    failure = HTTPError("https://docs.python.org/3.14/objects.inv", status, "failed", HTTPMessage(), None)
    monkeypatch.setattr("conftest.urlopen", create_autospec(open_inventory, side_effect=failure))

    with raises(HTTPError, match="failed") as error:
        download_inventory()

    assert (error.value.code, delays) == (status, expected_delays)
