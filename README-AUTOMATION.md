# Author report automation

A GitHub Actions workflow runs every six hours and can also be started manually from Actions > Update published reports > Run workflow.

It searches Google News RSS for the exact author name on AajTak and India Today NE, follows each result to the publisher site, and only includes a result when the publisher page exposes an explicit author/byline metadata field matching "Mansur Habibullah". It stores title, original URL, publication date, and a short metadata description in `reports.json`. The portfolio reads that JSON file at runtime.

This is best-effort discovery, not an official publisher API. Search indexing delays, publisher markup changes, robots restrictions, or missing byline metadata can delay or omit a story. It deliberately avoids adding stories where the byline cannot be verified.
