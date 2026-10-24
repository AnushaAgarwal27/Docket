from rules.apify_collector import collect, run_input
from rules.engine import load_rules
from seed.apify_sources import sync

RULES = load_rules()
FICA = next(r for r in RULES if r["id"] == "FICA_EXEMPT_F1")


class FakeApify:
    """Stands in for ApifyClient: one Actor run, one dataset of crawled pages."""

    def __init__(self, items, status="SUCCEEDED"):
        self.items, self.status, self.calls = items, status, []

    def actor(self, name):
        self.calls.append(name)
        return self

    def call(self, run_input):
        self.run_input = run_input
        return {"id": "run1", "status": self.status, "defaultDatasetId": "ds1"}

    def dataset(self, dataset_id):
        return self

    def iterate_items(self):
        return iter(self.items)


def page(url, sentence):
    return {"url": url, "crawl": {"loadedUrl": url}, "html": f"<html><script>x()</script><p>Intro.</p><p>{sentence}</p></html>"}


def test_one_run_fetches_every_page_at_depth_zero_with_html():
    urls = [r.get("fetch_url", r["source_url"]) for r in RULES]
    body = run_input(urls)
    assert body["maxCrawlDepth"] == 0 and body["saveHtml"] is True and len(body["startUrls"]) == len(urls)


def test_html_goes_through_our_text_extraction_so_quotes_match():
    fake = FakeApify([page(FICA["source_url"], FICA["quote"])])
    pages, missing = collect([FICA], client=fake)
    assert fake.calls == ["apify/website-content-crawler"]
    assert pages[0].text == f"Intro. {FICA['quote']}" and pages[0].run_id == "run1" and missing == []


def test_page_missing_from_results_is_reported():
    pages, missing = collect(RULES, client=FakeApify([page(FICA["source_url"], FICA["quote"])]))
    assert [p.rule_id for p in pages] == ["FICA_EXEMPT_F1"] and "FORM_8843_ANNUAL" in missing


def test_failed_run_raises():
    import pytest
    with pytest.raises(RuntimeError):
        collect([FICA], client=FakeApify([], status="FAILED"))


class FakeConvex:
    def __init__(self, stored=None):
        self.stored, self.mutations = stored, []

    def query(self, name, args):
        return self.stored

    def mutation(self, name, args):
        self.mutations.append((name, args))
        return "src1"


def test_changed_page_logs_source_changed_and_rechecks_quote():
    pages, _ = collect([FICA], client=FakeApify([page(FICA["source_url"], "The wording is different now.")]))
    convex = FakeConvex(stored={"hash": "0" * 64})
    lines = sync([FICA], pages, convex)
    actions = [a["action"] for n, a in convex.mutations if n == "activity:log"]
    assert actions == ["source_changed", "source_fetched"] and "QUOTE NOT FOUND" in lines[0]


def test_unchanged_page_is_same():
    pages, _ = collect([FICA], client=FakeApify([page(FICA["source_url"], FICA["quote"])]))
    lines = sync([FICA], pages, FakeConvex(stored={"hash": pages[0].hash}))
    assert lines[0].startswith("SAME") and "quote found" in lines[0]


def test_local_download_reports_new_same_changed(tmp_path, monkeypatch):
    import rules.download_sources as ds
    monkeypatch.setattr(ds, "SOURCES_DIR", tmp_path)
    assert [ds.save(FICA, t, "test") for t in ("a", "a", "b")] == ["NEW", "SAME", "CHANGED"]
    assert (tmp_path / "FICA_EXEMPT_F1.txt").read_text() == "b"
