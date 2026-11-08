"""Validate source identity, evidence retention and Daily boundary preparation."""
from contextlib import nullcontext
from datetime import date
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlencode, urlsplit

import pytest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "bethlehem_observations", ROOT / "examples/fe_walter_bethlehem/prepare_observations.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def request():
    return {"request_id": "boundary_q", "station_id": "01449800", "parameter_code": "00060",
            "statistic_id": "00003", "quantity": "discharge", "source_unit": "ft^3/s", "role": "common_external_boundary"}


def feature(day="2024-02-29", value="1", **extra):
    p = {"monitoring_location_id": "USGS-01449800", "parameter_code": "00060", "statistic_id": "00003",
         "time": day, "value": value, "unit_of_measure": "ft^3/s", "approval_status": "Approved",
         "qualifier": "e", "time_series_id": "source-series", "last_modified": "2024-04-01T00:00:00Z"}
    p.update(extra)
    return {"type": "Feature", "properties": p}


def response(url, features, links=()):
    class Response:
        status = 200

        def read(self):
            return json.dumps({"features": features, "numberReturned": len(features), "links": links}).encode()

        def geturl(self):
            return url

    return nullcontext(Response())


def test_calendar_labels_leap_day_missingness_and_quality_are_preserved(tmp_path):
    profile = {"case_id": "test", "api_key": "do-not-copy", "observation_requests": [request()],
               "coverage_periods": [{"id": "custom", "start": "2024-02-29", "end_inclusive": "2024-02-29"}]}
    output = tmp_path / "input"
    result = MODULE.collect_daily(profile, date(2024, 2, 28), date(2024, 3, 1), output,
                                 opener=lambda url, **kw: response(url, [feature()]))
    assert result['status'] == 'RETRIEVED_AND_AUDITED_NOT_SCIENTIFIC_ACCEPTANCE'
    assert 'do-not-copy' not in (output / 'manifest.json').read_text()
    import csv
    rows = list(csv.DictReader((output / 'observations_daily.csv').open()))
    assert [r['date'] for r in rows] == ['2024-02-28', '2024-02-29', '2024-03-01']
    assert [r['record_status'] for r in rows] == ['no_source_record', 'numeric', 'no_source_record']
    assert Decimal(rows[1]['value']) == Decimal('0.028316846592')
    assert rows[1]['qualifier'] == 'e' and rows[0]['value'] == ''
    coverage = list(csv.DictReader((output / 'coverage_daily.csv').open()))
    assert [(r['period'], r['expected_days'], r['numeric_days']) for r in coverage] == [
        ('requested_interval', '3', '1'), ('custom', '1', '1')]


@pytest.mark.parametrize('changes', [
    {'monitoring_location_id': 'USGS-01453000'}, {'parameter_code': '00065'},
    {'statistic_id': '00001'}, {'unit_of_measure': 'm3/s'}, {'approval_status': 'unknown'},
    {'time': '2024-02-29T00:00:00Z'}, {'value': 'NaN'}, {'value': 'Infinity'}, {'value': '-1'},
])
def test_mismatched_or_invalid_source_content_is_rejected(changes):
    with pytest.raises(ValueError):
        MODULE.normalise_feature(feature(**changes), request(), date(2024, 2, 28), date(2024, 3, 1))


def test_null_source_value_remains_missing_not_zero():
    row = MODULE.normalise_feature(feature(value=None), request(), date(2024, 2, 29), date(2024, 2, 29))
    assert row['value'] == '' and row['record_status'] == 'source_value_missing'


def test_pool_elevation_remains_in_reported_feet():
    r = {**request(), 'quantity': 'pool_elevation', 'parameter_code': '00062', 'source_unit': 'ft'}
    row = MODULE.normalise_feature(feature(value='628.1', parameter_code='00062', unit_of_measure='ft'),
                                   r, date(2024, 2, 29), date(2024, 2, 29))
    assert row['value'] == '628.1' and row['unit'] == 'ft'


def test_duplicate_records_fail_after_raw_page_is_saved(tmp_path):
    output = tmp_path / 'input'
    with pytest.raises(ValueError, match='Duplicate Daily'):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29), date(2024, 2, 29), output,
                             opener=lambda url, **kw: response(url, [feature(), feature()]))
    result = json.loads((output / 'manifest.json').read_text())
    assert result['status'] == 'FAILED_EVIDENCE_RETAINED'
    assert (output / result['pages'][0]['path']).is_file()
    assert not (output / 'observations_daily.csv').exists()


def test_transport_failure_is_recorded_without_retry(tmp_path):
    calls = []

    def fail(url, **kwargs):
        calls.append(url)
        raise URLError('fixture timeout')

    output = tmp_path / 'input'
    with pytest.raises(URLError):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29), date(2024, 2, 29), output, opener=fail)
    manifest = json.loads((output / 'manifest.json').read_text())
    assert len(calls) == 1 and manifest['pages'][0]['url'] == calls[0]
    assert manifest['pages'][0]['status'] == 'FAILED_RESPONSE_NOT_SAVED'


def test_http_failure_keeps_body_and_does_not_retry(tmp_path):
    calls = []

    def fail(url, **kwargs):
        calls.append(url)
        raise HTTPError(url, 503, 'fixture', {}, io.BytesIO(b'upstream unavailable'))

    output = tmp_path / 'input'
    with pytest.raises(HTTPError):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29), date(2024, 2, 29), output, opener=fail)
    manifest = json.loads((output / 'manifest.json').read_text())
    assert len(calls) == 1 and manifest['pages'][0]['http_status'] == 503
    assert (output / manifest['pages'][0]['path']).read_bytes() == b'upstream unavailable'


@pytest.mark.parametrize('mutate', ['host', 'selection'])
def test_pagination_cannot_change_host_or_series_selection(mutate, tmp_path):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        query = {k: v[0] for k, v in parse_qs(urlsplit(url).query).items()}
        target = MODULE.API
        if mutate == 'host':
            target = 'https://untrusted.invalid/next'
        else:
            query['monitoring_location_id'] = 'USGS-01453000'
        return response(url, [feature()], [{'rel': 'next', 'href': target + '?' + urlencode(query)}])

    with pytest.raises(ValueError, match='pagination|Pagination'):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29), date(2024, 2, 29),
                             tmp_path / 'input', opener=fetch)
    assert len(calls) == 1


def test_existing_output_and_unsafe_request_id_are_rejected_before_network(tmp_path):
    sentinel = tmp_path / 'untouched.txt'
    sentinel.write_text('preserve')
    with pytest.raises(FileExistsError):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29), date(2024, 2, 29), tmp_path)
    assert sentinel.read_text() == 'preserve'
    with pytest.raises(ValueError, match='unsafe request_id'):
        MODULE.collect_daily({'observation_requests': [{**request(), 'request_id': '../escape'}]},
                             date(2024, 2, 29), date(2024, 2, 29), tmp_path / 'input')
    assert not (tmp_path / 'input').exists()


def test_empty_page_with_next_link_fails_closed_and_retains_evidence(tmp_path):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        return response(url, [], [{'rel': 'next', 'href': url + '&cursor=second'}])

    output = tmp_path / 'input'
    with pytest.raises(ValueError, match='completeness is unknown'):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29),
                             date(2024, 2, 29), output, opener=fetch)
    assert len(calls) == 1
    manifest = json.loads((output / 'manifest.json').read_text())
    assert manifest['status'] == 'FAILED_EVIDENCE_RETAINED'
    assert json.loads((output / manifest['pages'][0]['path']).read_bytes())['features'] == []
    assert not (output / 'coverage_daily.csv').exists()


def test_rejected_redirect_retains_received_body_and_hash(tmp_path):
    raw = b'{"original": "unexpected redirect source"}'

    class RedirectResponse:
        status = 200

        def read(self):
            return raw

        def geturl(self):
            return 'https://unexpected.invalid/body'

    output = tmp_path / 'input'
    with pytest.raises(ValueError, match='redirect host'):
        MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 29),
                             date(2024, 2, 29), output,
                             opener=lambda url, **kw: nullcontext(RedirectResponse()))
    manifest = json.loads((output / 'manifest.json').read_text())
    saved = manifest['pages'][0]
    import hashlib
    assert manifest['status'] == 'FAILED_EVIDENCE_RETAINED'
    assert (output / saved['path']).read_bytes() == raw
    assert saved['sha256'] == hashlib.sha256(raw).hexdigest()
    assert saved['bytes'] == len(raw) and saved['http_status'] == 200
    assert not (output / 'observations_daily.csv').exists()


def test_two_pages_form_one_continuous_observation_series(tmp_path):
    calls = []

    def fetch(url, **kwargs):
        calls.append(url)
        if len(calls) == 1:
            return response(url, [feature(day='2024-02-28')],
                            [{'rel': 'next', 'href': url + '&cursor=second'}])
        return response(url, [feature(day='2024-02-29')])

    output = tmp_path / 'input'
    manifest = MODULE.collect_daily({'observation_requests': [request()]}, date(2024, 2, 28),
                                    date(2024, 2, 29), output, opener=fetch)
    import csv
    rows = list(csv.DictReader((output / 'observations_daily.csv').open()))
    assert len(calls) == 2 and len(manifest['pages']) == 2
    assert [row['date'] for row in rows] == ['2024-02-28', '2024-02-29']
    assert [row['record_status'] for row in rows] == ['numeric', 'numeric']
