"""Failures must not masquerade as uninteresting content."""
import pytest
import httpx

from webchanges.differs import AIOpenAIDiffer
from webchanges.filters._text import RejectTextFilter
from webchanges.jobs import JobBase


def test_block_page_is_rejected():
    job = JobBase.unserialize({'url': 'https://example.test'})
    from webchanges.handler import JobState
    f = RejectTextFilter(JobState(None, job))
    rule = {'pattern': 'Javascript is required.*enable javascript'}
    with pytest.raises(ValueError, match='access-block'):
        f.filter('Javascript is required. Please enable javascript', 'text/plain', rule)
    assert f.filter('New issue available', 'text/plain', rule)[0] == 'New issue available'


@pytest.mark.parametrize('body', ['', '   '])
def test_empty_model_output_is_error(monkeypatch, body):
    client = httpx.Client
    monkeypatch.setenv('OPENAI_API_KEY', 'test')
    monkeypatch.setattr(httpx, 'Client', lambda **kw: client(transport=httpx.MockTransport(
        lambda request: httpx.Response(200, json={'choices': [{'message': {'content': body}}]}, request=request)), **kw))
    job = JobBase.unserialize({'url': 'https://example.test'})
    summary, _ = AIOpenAIDiffer._send_to_model(job, '', 'Summarise changes')
    assert summary.startswith('## ERROR')
