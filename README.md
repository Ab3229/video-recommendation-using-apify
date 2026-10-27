# Adult Video Recommendation Actor

This Apify Actor crawls public listing pages supplied by the user, extracts public video metadata, filters titles and URLs containing common minor/age-ambiguous terms, and returns a ranked dataset of adult-only recommendations.

Use this Actor only with websites you are legally allowed to access. It does not download, host, or return video files. It stores only public metadata and does not attempt to identify people.

## Input

```json
{
  "start_urls": [{"url": "https://example.com/adult/videos"}],
  "top_n": 10,
  "max_pages": 5
}
```

- `start_urls`: public listing pages containing cards with a title and link.
- `top_n`: maximum number of recommendations.
- `max_pages`: maximum number of listing pages to crawl.

The extractor recognizes common selectors such as `.video-card`, `.title`, `.views`, `.rating`, `h2`, and `h3`. Site-specific HTML may require adjusting the selectors in `my_actor/main.py`.

## Output

Each dataset item contains:

- `rank`: recommendation rank
- `title`: public title
- `url`: public video URL
- `views`: parsed public view count
- `rating`: normalized rating from `0` to `1`
- `score`: ranking score from `0` to `1`

The score combines the public rating (75%) with logarithmic view engagement (25%), so popular videos do not automatically overwhelm quality signals.

## Local run

Install the Apify CLI, place input in `storage/key_value_stores/default/INPUT.json`, then run:

```bash
apify validate-schema
apify run
```

Results are written to `storage/datasets/default/`.

## Important limitations

- The Actor does not prove age or consent; it only applies conservative text filtering. Review results before use.
- Respect robots.txt, terms of service, licensing, privacy law, and local age-verification requirements.
- Do not use it to discover, store, or distribute illegal, non-consensual, or minor-related content.
