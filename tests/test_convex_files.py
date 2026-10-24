from pathlib import Path

import agents.convex_files as cf


class FakeConvex:
    def __init__(self, fail_post=False):
        self.calls, self.logs, self.fail_post = [], [], fail_post

    def mutation(self, name, args=None):
        self.calls.append((name, args))
        return "https://upload.example/abc" if name == "files:generateUploadUrl" else "file_1"

    def log(self, agent, action, detail, **extra):
        self.logs.append((agent, action, detail, extra))


class FakeResponse:
    def raise_for_status(self):
        pass

    def json(self):
        return {"storageId": "kg_storage_1"}


def install(monkeypatch, fake, posted):
    monkeypatch.setattr(cf, "mutation", fake.mutation)
    monkeypatch.setattr(cf, "log", fake.log)

    def post(url, data, headers, timeout):
        if fake.fail_post:
            raise ConnectionError("upload refused")
        posted.append((url, data, headers))
        return FakeResponse()
    monkeypatch.setattr(cf.requests, "post", post)


def test_upload_posts_bytes_then_attaches_and_logs(tmp_path: Path, monkeypatch):
    fake, posted = FakeConvex(), []
    install(monkeypatch, fake, posted)
    pdf = tmp_path / "paystub_01.pdf"
    pdf.write_bytes(b"%PDF-1.4 synthetic")
    assert cf.upload_and_attach(pdf, "paystub", agent="ledger", paystubId="ps_1") == "file_1"
    assert posted == [("https://upload.example/abc", b"%PDF-1.4 synthetic", {"Content-Type": "application/pdf"})]
    assert fake.calls[-1] == ("files:attach", {"storageId": "kg_storage_1", "kind": "paystub",
                                               "filename": "paystub_01.pdf", "paystubId": "ps_1"})
    assert fake.logs == [("ledger", "file_uploaded", "paystub paystub_01.pdf",
                          {"inputIds": ["ps_1"], "outputIds": ["file_1"]})]


def test_in_memory_bytes_use_the_given_name(monkeypatch):
    fake, posted = FakeConvex(), []
    install(monkeypatch, fake, posted)
    cf.upload_and_attach(Path("refund_request.pdf"), "letter", agent="caseworker", data=b"%PDF", flagId="fl_1")
    assert posted[0][1] == b"%PDF" and fake.calls[-1][1]["filename"] == "refund_request.pdf"


def test_failure_is_logged_not_raised(tmp_path: Path, monkeypatch):
    fake, posted = FakeConvex(fail_post=True), []
    install(monkeypatch, fake, posted)
    pdf = tmp_path / "x.pdf"
    pdf.write_bytes(b"%PDF")
    assert cf.upload_and_attach(pdf, "paystub", agent="ledger", paystubId="ps_1") is None
    assert fake.logs[0][1] == "file_upload_failed" and "upload refused" in fake.logs[0][2]
    assert not any(name == "files:attach" for name, _ in fake.calls)
