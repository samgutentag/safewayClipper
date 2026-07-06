import responses
from clipper.notify import Notifier

URL = "https://api.pushover.net/1/messages.json"


@responses.activate
def test_send_posts_payload():
    responses.add(responses.POST, URL, json={"status": 1}, status=200)
    Notifier("tok", "usr").send("Title", "Body", priority=1)
    body = responses.calls[0].request.body
    assert "token=tok" in body and "user=usr" in body and "priority=1" in body


@responses.activate
def test_missing_credentials_is_noop():
    Notifier(None, None).send("Title", "Body")
    assert len(responses.calls) == 0


@responses.activate
def test_http_error_does_not_raise():
    responses.add(responses.POST, URL, status=500)
    Notifier("tok", "usr").send("Title", "Body")  # must not raise
