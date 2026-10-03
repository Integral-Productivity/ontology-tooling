"""Snapshots of released versions (metawork-ontology ADR-0004 decision 3).

Ported with the behavior of vertical-development-ontology#6 (its PR #12):
every release tag vX.Y.Z keeps its snapshot, and a released file is frozen.
"""
import subprocess

import pytest

import ontology_tooling as ot

TTL = """@prefix owl: <http://www.w3.org/2002/07/owl#> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
<https://example.org/tiny> a owl:Ontology ; owl:versionInfo "{version}" .
<https://example.org/tiny/vocab/a> a skos:Concept ; skos:prefLabel "{label}" .
"""


def tiny(version, label="A"):
    return TTL.format(version=version, label=label).encode()


def write(path, version, label="A"):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(tiny(version, label))
    return path


def git(repo, *args):
    subprocess.run(["git", "-C", str(repo), *args], check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    r = tmp_path / "repo"
    r.mkdir()
    git(r, "init", "-q", "-b", "main")
    git(r, "config", "user.email", "t@example.org")
    git(r, "config", "user.name", "t")
    git(r, "config", "commit.gpgsign", "false")
    git(r, "config", "tag.gpgsign", "false")
    return r


def commit_and_tag(repo, ttl, tag=None):
    git(repo, "add", "-A")
    git(repo, "commit", "-q", "-m", "x")
    if tag:
        git(repo, "tag", tag)


def test_older_released_version_is_kept(tmp_path):
    ttl = write(tmp_path / "ontology" / "tiny.ttl", "0.2.0")
    out = tmp_path / "site"
    ot.build(out, ttl, releases={"0.1.0": tiny("0.1.0")})
    assert (out / "tiny/v/0.1.0/tiny.ttl").read_bytes() == tiny("0.1.0")
    assert (out / "tiny/v/0.2.0/tiny.ttl").read_bytes() == ttl.read_bytes()
    assert "snapshot of version 0.1.0" in (out / "tiny/v/0.1.0/index.html").read_text()


def test_unbumped_edit_of_a_released_version_fails_before_writing(tmp_path):
    ttl = write(tmp_path / "ontology" / "tiny.ttl", "0.1.0", label="Edited")
    out = tmp_path / "site"
    with pytest.raises(ot.ReleaseError, match="bump owl:versionInfo"):
        ot.build(out, ttl, releases={"0.1.0": tiny("0.1.0")})
    assert not out.exists()


def test_released_version_equal_to_the_file_builds(tmp_path):
    ttl = write(tmp_path / "ontology" / "tiny.ttl", "0.1.0")
    out = tmp_path / "site"
    ot.build(out, ttl, releases={"0.1.0": tiny("0.1.0")})
    assert sorted(p.name for p in (out / "tiny/v").iterdir()) == ["0.1.0"]


def test_released_reads_semver_tags_from_git(repo):
    ttl = write(repo / "ontology" / "tiny.ttl", "0.1.0")
    commit_and_tag(repo, ttl, "v0.1.0")
    write(ttl, "0.2.0")
    commit_and_tag(repo, ttl, "release-0.2")  # not vX.Y.Z: ignored
    assert ot.released(ttl) == {"0.1.0": tiny("0.1.0")}


def test_released_outside_a_git_work_tree_is_empty(tmp_path):
    ttl = write(tmp_path / "ontology" / "tiny.ttl", "0.1.0")
    assert ot.released(ttl) == {}


def test_tag_whose_file_says_another_version_fails(repo):
    ttl = write(repo / "ontology" / "tiny.ttl", "0.1.0")
    commit_and_tag(repo, ttl, "v0.3.0")
    with pytest.raises(ot.ReleaseError, match="has owl:versionInfo 0.1.0, not 0.3.0"):
        ot.released(ttl)


def test_tag_without_the_file_fails(repo):
    (repo / "README").write_text("x")
    commit_and_tag(repo, None, "v0.1.0")
    ttl = write(repo / "ontology" / "tiny.ttl", "0.2.0")
    with pytest.raises(ot.ReleaseError, match="does not exist at that tag"):
        ot.released(ttl)


def test_build_reads_releases_from_git_end_to_end(repo, tmp_path):
    ttl = write(repo / "ontology" / "tiny.ttl", "0.1.0")
    commit_and_tag(repo, ttl, "v0.1.0")
    write(ttl, "0.2.0", label="B")
    out = tmp_path / "site"
    ot.build(out, ttl)
    assert (out / "tiny/v/0.1.0/tiny.ttl").read_bytes() == tiny("0.1.0")
    assert (out / "tiny/v/0.2.0/tiny.ttl").read_bytes() == tiny("0.2.0", "B")

    write(ttl, "0.1.0", label="Unbumped")
    with pytest.raises(ot.ReleaseError):
        ot.build(out, ttl)
