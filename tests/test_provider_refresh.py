"""Provider authorization, secret redaction, bounded network and immutable source binding."""

import csv
import io
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx
import pytest

from packages.data import provider_refresh, providers
from packages.data.finviz import COLUMNS, read_snapshot
from packages.data.provider_config import provider_setting
from packages.data.provider_refresh import read_sec_bundle, refresh_finviz, sync_sec

TOKEN = "fictional-unit-test-token-not-a-credential"
CONTACT = "Fixture Lab fixture@baghunter.invalid"


@pytest.fixture
def transport(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for key in ("SEC_USER_AGENT", "BAGHUNTER_SEC_USER_AGENT", "FINVIZ_TOKEN"):
        monkeypatch.delenv(key, raising=False)
    original = httpx.Client
    monkeypatch.setattr(providers.time, "sleep", lambda _: None)

    def install(handler):
        monkeypatch.setattr(
            httpx, "Client", lambda **kw: original(transport=httpx.MockTransport(handler), **kw)
        )

    return install


def csv_body():
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(COLUMNS)
    writer.writerow(
        [1, "DEMO-X", "Fictional widgets", "Tech", "Widgets", "USA", "12", "0", "3", "1%", "100"]
    )
    return stream.getvalue().encode()


def sec_sources():
    return (
        {
            "cik": "1",
            "filings": {
                "recent": {
                    "accessionNumber": ["0000000001-20-000001"],
                    "acceptanceDateTime": ["2020-02-01T12:00:00Z"],
                    "form": ["10-K"],
                    "primaryDocument": ["annual.htm"],
                }
            },
        },
        {
            "cik": 1,
            "facts": {
                "us-gaap": {
                    "Revenues": {
                        "units": {
                            "USD": [
                                {
                                    "accn": "0000000001-20-000001",
                                    "form": "10-K",
                                    "start": "2019-01-01",
                                    "end": "2019-12-31",
                                    "filed": "2020-02-01",
                                    "val": 100,
                                }
                            ]
                        }
                    }
                }
            },
        },
    )


def test_dotenv_alias_quotes_precedence_and_no_environment_export(transport, monkeypatch):
    env = Path(".env")
    env.write_text(
        "UNRELATED_SETTING=never-export\n"
        f'BAGHUNTER_SEC_USER_AGENT="{CONTACT}" # comment\nFINVIZ_TOKEN={TOKEN}\n'
    )
    assert provider_setting("SEC_USER_AGENT") == CONTACT
    assert provider_setting("FINVIZ_TOKEN") == TOKEN
    import os

    assert "UNRELATED_SETTING" not in os.environ
    assert "BAGHUNTER_SEC_USER_AGENT" not in os.environ
    monkeypatch.setenv("SEC_USER_AGENT", "Environment fixture@baghunter.invalid")
    assert provider_setting("SEC_USER_AGENT").startswith("Environment")
    with pytest.raises(ValueError, match="Unsupported"):
        provider_setting("UNRELATED_SETTING")


@pytest.mark.parametrize(
    "content",
    [
        'SEC_USER_AGENT="unterminated',
        "SEC_USER_AGENT=a\nSEC_USER_AGENT=b",
        'SEC_USER_AGENT="a" trailing',
        "SEC_USER_AGENT=a\x00b",
        "x" * (64 * 1024 + 1),
    ],
    ids=["unterminated", "duplicate", "trailing", "control", "oversized"],
)
def test_invalid_dotenv_is_not_evaluated_or_echoed(transport, content):
    Path(".env").write_text(content)
    with pytest.raises(ValueError):
        provider_setting("SEC_USER_AGENT")


def test_finviz_manual_refresh_validates_and_archives_without_token(transport):
    requests = []

    def respond(request):
        requests.append(request)
        assert request.url.params["auth"] == TOKEN
        if len(requests) == 1:
            return httpx.Response(302, headers={"location": "/export"})
        return httpx.Response(200, content=csv_body(), headers={"content-type": "text/csv"})

    transport(respond)
    report = refresh_finviz(TOKEN, usage_authorized=True)
    assert len(requests) == 2 and report["rows"] == 1
    coverage, rows = read_snapshot(report["snapshot_id"], "EXTERNAL_UNVERIFIED")
    assert coverage["status"] == "QUARANTINED_CURRENT_SNAPSHOT"
    assert rows[0].security_id is None
    for path in Path("data").rglob("*"):
        if path.is_file():
            assert TOKEN.encode() not in path.read_bytes()
    assert not list(Path("data").rglob("CURRENT"))


@pytest.mark.parametrize(
    "location",
    [
        "https://attacker.invalid/export",
        "http://elite.finviz.com/export",
        "https://elite.finviz.com:8443/export",
        "/login",
        "https://user:pass@elite.finviz.com/export",
    ],
)
def test_finviz_never_forwards_auth_to_unapproved_redirect(transport, location):
    attempts = []
    transport(
        lambda request: (
            attempts.append(request),
            httpx.Response(302, headers={"location": location}),
        )[1]
    )
    with pytest.raises(ValueError, match="redirect"):
        refresh_finviz(TOKEN, usage_authorized=True)
    assert len(attempts) == 1 and not Path("data").exists()


@pytest.mark.parametrize("kind", ["html", "large", "credential", "429"])
def test_finviz_rejects_bad_responses_without_publication(transport, monkeypatch, kind):
    body = csv_body()
    headers = {"content-type": "text/csv"}
    status = 200
    if kind == "html":
        body, headers = b"<html>login</html>", {"content-type": "text/html"}
    elif kind == "large":
        monkeypatch.setattr(provider_refresh, "MAX_BYTES", 8)
    elif kind == "credential":
        body = body.replace(b"Fictional widgets", TOKEN.encode())
    else:
        status = 429
    transport(lambda _: httpx.Response(status, content=body, headers=headers))
    with pytest.raises((ValueError, httpx.HTTPError)):
        refresh_finviz(TOKEN, usage_authorized=True)
    assert not Path("data").exists()


def test_sec_pair_bundle_source_and_normalized_integrity(transport):
    submissions, facts = sec_sources()
    calls = []

    def respond(request):
        calls.append(request)
        assert request.headers["User-Agent"] == CONTACT
        return httpx.Response(
            200, json=facts if "/companyfacts/" in request.url.path else submissions
        )

    transport(respond)
    output = Path.cwd() / "data/real/sec"
    clock = datetime(2020, 4, 1, tzinfo=UTC)
    result = sync_sec("1", CONTACT, clock, output)
    assert result["facts"] == 1 and len(calls) == 2
    bundle = read_sec_bundle(result["bundle_id"])
    assert bundle["normalized"]["facts"][0]["value"] == 100
    assert "UNVERIFIED" in bundle["normalized"]["identity_assignment"]
    assert result == sync_sec("1", CONTACT, clock, output)
    for path in output.rglob("*.json"):
        assert CONTACT not in path.read_text()
    path = output / "bundles" / result["bundle_id"] / "normalized.json"
    path.write_text("{}")
    with pytest.raises(ValueError, match="integrity"):
        read_sec_bundle(result["bundle_id"])
    with pytest.raises(ValueError, match="integrity"):
        sync_sec("1", CONTACT, clock, output)


@pytest.mark.parametrize("kind", ["redirect", "wrong_cik", "non_json", "oversized", "403"])
def test_sec_rejects_untrusted_sources_without_cache(transport, kind):
    data = {"cik": 2 if kind == "wrong_cik" else 1, "facts": {}}
    status = 302 if kind == "redirect" else 403 if kind == "403" else 200
    content = b"x" * (20 * 1024 * 1024 + 1) if kind == "oversized" else json.dumps(data).encode()
    transport(
        lambda _: httpx.Response(
            status,
            content=content,
            headers={
                "content-type": "text/html" if kind == "non_json" else "application/json",
                "location": "https://attacker.invalid/",
            },
        )
    )
    with pytest.raises((ValueError, httpx.HTTPError)):
        providers.SecClient(CONTACT, Path("raw")).companyfacts("1")
    assert not list(Path("raw").glob("*.json"))


def test_cli_does_not_echo_failed_authenticated_url_or_contact(transport, monkeypatch, capsys):
    from packages import cli

    Path(".env").write_text(f"FINVIZ_TOKEN={TOKEN}\nBAGHUNTER_SEC_USER_AGENT={CONTACT}\n")
    monkeypatch.setattr("sys.argv", ["baghunter", "refresh-finviz", "--usage-authorized"])

    def reject(*args, **kwargs):
        raise httpx.ConnectError(f"https://elite.finviz.com/export?auth={TOKEN}; {CONTACT}")

    monkeypatch.setattr(cli, "refresh_finviz", reject)
    with pytest.raises(SystemExit) as error:
        cli.main()
    assert error.value.code == 2
    captured = capsys.readouterr()
    assert TOKEN not in captured.err and CONTACT not in captured.err
    assert "suppressed" in captured.err and not captured.out
    with pytest.raises(ValueError, match="clock"):
        sync_sec("1", CONTACT, datetime.now(UTC) + timedelta(days=1), Path("data/real/sec"))


def test_sec_api_requires_verified_bundle_and_preserves_empty_filters(transport):
    from fastapi.testclient import TestClient

    from apps.api.main import app

    submissions, facts = sec_sources()
    transport(
        lambda request: httpx.Response(
            200, json=facts if "/companyfacts/" in request.url.path else submissions
        )
    )
    result = sync_sec("1", CONTACT, datetime(2020, 4, 1, tzinfo=UTC), Path.cwd() / "data/real/sec")
    client = TestClient(app)
    index = client.get("/sec/bundles").json()
    assert index["bundles"][0]["bundle_id"] == result["bundle_id"]
    endpoint = f"/sec/bundles/{result['bundle_id']}"
    response = client.get(endpoint + "?limit=1").json()
    assert response["total"] == 1 and response["source_facts"] == 1
    assert response["normalized"]["facts"][0]["published_at"] == "2020-02-02T00:00:00Z"
    assert response["issuer"]["scope"] == "CURRENT_ISSUER_METADATA_NOT_SECURITY_MAPPING"
    assert response["issuer"]["name"] is None
    assert client.get(endpoint + "?metric=annual_net_income").json()["total"] == 0
    for query in ("limit=101", "offset=-1", "metric=share_price"):
        assert client.get(endpoint + "?" + query).status_code == 422
    assert client.post(endpoint).status_code == 405
    (Path("data/real/sec/bundles") / result["bundle_id"] / "companyfacts.json").write_text("{}")
    rejected = client.get(endpoint)
    assert rejected.status_code == 503 and "verification failed" in rejected.json()["detail"]


@pytest.mark.parametrize("kind", ["valid", "missing", "bad_name", "bad_lists"])
def test_issuer_display_metadata_is_bounded_current_and_never_a_security_assignment(
    transport, kind
):
    submissions, facts = sec_sources()
    if kind != "missing":
        submissions.update(
            name="Fictional issuer", tickers=["FICTION", "FICTION.A"], exchanges=["NYSE"]
        )
        submissions["phone"] = "Fictional detail not exported"
    if kind == "bad_name":
        submissions["name"] = "Unsafe\nname"
    if kind == "bad_lists":
        submissions["tickers"] = ["TOO_MANY"] * 101
        submissions["exchanges"] = ["bad\nexchange"]
    transport(
        lambda request: httpx.Response(
            200, json=facts if "/companyfacts/" in request.url.path else submissions
        )
    )
    result = sync_sec("1", CONTACT, datetime(2020, 4, 1, tzinfo=UTC), Path.cwd() / "data/real/sec")
    bundle = read_sec_bundle(result["bundle_id"])
    issuer = bundle["issuer"]
    assert set(issuer) == {"name", "tickers", "exchanges", "scope", "source_sha256", "retrieved_at"}
    assert issuer["source_sha256"] == bundle["manifest"]["submissions"]["sha256"]
    assert issuer["retrieved_at"] == bundle["manifest"]["submissions"]["retrieved_at"]
    assert issuer["scope"] == "CURRENT_ISSUER_METADATA_NOT_SECURITY_MAPPING"
    assert issuer["name"] == ("Fictional issuer" if kind in ("valid", "bad_lists") else None)
    assert issuer["tickers"] == (
        ["FICTION", "FICTION.A"] if kind in ("valid", "bad_name") else None
    )
    assert issuer["exchanges"] == (["NYSE"] if kind in ("valid", "bad_name") else None)
    assert len(bundle["normalized"]["facts"]) == 1
    assert bundle["normalized"]["identity_assignment"] == "OPERATOR_SUPPLIED_UNVERIFIED"


def test_sec_bundle_rejects_linked_archive(tmp_path, transport):
    import os

    root = Path("data/real/sec/bundles")
    root.mkdir(parents=True)
    target = tmp_path / "outside"
    target.mkdir()
    try:
        os.symlink(target, root / ("a" * 64), target_is_directory=True)
    except OSError:
        pytest.skip("Symlink capability unavailable; required in Linux CI")
    with pytest.raises(ValueError, match="symlinks"):
        read_sec_bundle("a" * 64)


def test_refresh_requires_authorization_before_any_network_or_files(transport):
    def unexpected(_):
        raise AssertionError("Unauthorized network request")

    transport(unexpected)
    with pytest.raises(ValueError, match="Authorized"):
        refresh_finviz(TOKEN, usage_authorized=False)
    assert not Path("data").exists()


def test_sec_cache_metadata_cannot_add_private_fields_or_repair_itself(transport):
    transport(lambda _: httpx.Response(200, json={"cik": 1, "facts": {}}))
    client = providers.SecClient(CONTACT, Path("raw"))
    manifest = client.companyfacts("1")
    path = Path("raw") / f"{manifest['sha256']}.manifest.json"
    path.write_text(json.dumps(manifest | {"private_field": "must-not-propagate"}))
    before = path.read_bytes()
    with pytest.raises(ValueError, match="manifest integrity"):
        client.companyfacts("1")
    assert path.read_bytes() == before


def test_sec_sync_does_not_publish_through_linked_bundle_root(transport, tmp_path):
    import os

    submissions, facts = sec_sources()
    transport(
        lambda request: httpx.Response(
            200, json=facts if "/companyfacts/" in request.url.path else submissions
        )
    )
    output = tmp_path / "data/real/sec"
    output.mkdir(parents=True)
    target = tmp_path / "outside"
    target.mkdir()
    try:
        os.symlink(target, output / "bundles", target_is_directory=True)
    except OSError:
        pytest.skip("Symlink capability unavailable; required in Linux CI")
    with pytest.raises(ValueError, match="symlinks"):
        sync_sec("1", CONTACT, datetime(2020, 4, 1, tzinfo=UTC), output)
    assert not list(target.iterdir())
