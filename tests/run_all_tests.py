"""Run all source tests sequentially and print a summary."""

import asyncio
import sys
import os
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))


async def run_all():
    results = {}
    total_start = time.time()

    # Ensure tests/ dir is first on path so we import from here, not root
    tests_dir = os.path.dirname(os.path.abspath(__file__))

    # Import test functions explicitly from tests/ dir
    import importlib.util

    def load_test(name, filename):
        spec = importlib.util.spec_from_file_location(name, os.path.join(tests_dir, filename))
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod

    mod_rss = load_test("test_rss_feed", "test_rss_feed.py")
    mod_hn = load_test("test_hn", "test_hn.py")
    mod_arxiv = load_test("test_arxiv", "test_arxiv.py")
    mod_reddit = load_test("test_reddit", "test_reddit.py")
    mod_twitter = load_test("test_twitter", "test_twitter.py")
    mod_youtube = load_test("test_youtube_src", "test_youtube.py")

    tests = [
        ("RSS Feeds", mod_rss.test_rss),
        ("Hacker News", mod_hn.test_hn),
        ("arXiv", mod_arxiv.test_arxiv),
        ("Reddit", mod_reddit.test_reddit),
        ("Twitter/Nitter", mod_twitter.test_twitter),
        ("YouTube", mod_youtube.test_youtube),
    ]

    for name, func in tests:
        print(f"\n\n{'#' * 60}")
        print(f"# Running: {name}")
        print(f"{'#' * 60}\n")
        start = time.time()
        try:
            passed = await func()
            elapsed = time.time() - start
            results[name] = ("PASS" if passed else "FAIL", f"{elapsed:.1f}s")
        except Exception as e:
            elapsed = time.time() - start
            results[name] = ("ERROR", f"{elapsed:.1f}s — {str(e)[:60]}")
            print(f"\nERROR: {e}")

    # Summary
    total = time.time() - total_start
    print(f"\n\n{'=' * 60}")
    print(f"{'TEST SUMMARY':^60}")
    print(f"{'=' * 60}")
    print(f"{'Source':<20} {'Status':<10} {'Time'}")
    print(f"{'-' * 60}")
    for name, (status, detail) in results.items():
        icon = "+" if status == "PASS" else "X" if status == "FAIL" else "!"
        print(f"[{icon}] {name:<18} {status:<10} {detail}")
    print(f"{'-' * 60}")
    passed = sum(1 for s, _ in results.values() if s == "PASS")
    print(f"Total: {passed}/{len(results)} passed in {total:.1f}s")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(run_all())
