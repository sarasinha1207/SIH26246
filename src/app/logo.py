"""
The logo mark, defined once.  build_pages.py puts it in the public header and writes assets/favicon.svg and assets/logo.svg; build_dashboard.py puts it in the dashboard top bar.

The mark: three rising bars on a navy tile (history, then the forecast bar drawn lighter) crossed by a marigold trend line that ends in a dot (the forecast point).
Blue is demand and employment, marigold is supply, as on the charts.  Flat colours only, so it reads at 16 px and the same markup can appear twice on a page.
"""
NAVY, BLUE, MARIGOLD = "#0F2B63", "#8FB0FF", "#F2A93B"

SHAPES = (
    f'<rect width="34" height="34" rx="9" fill="{NAVY}"/>'
    '<rect x=".5" y=".5" width="33" height="33" rx="8.5" fill="none" stroke="#fff" stroke-opacity=".16"/>'
    f'<rect x="6.5" y="19" width="5.4" height="8.5" rx="1.6" fill="{BLUE}"/>'
    f'<rect x="14.3" y="14" width="5.4" height="13.5" rx="1.6" fill="{BLUE}"/>'
    f'<rect x="22.1" y="8.5" width="5.4" height="19" rx="1.6" fill="{BLUE}" fill-opacity=".42"/>'
    f'<path d="M5.5 22.5C10 22 13 17.5 17 15S23.5 9.5 27.5 7" fill="none" stroke="{MARIGOLD}" stroke-width="2.6" stroke-linecap="round" stroke-linejoin="round"/>'
    f'<circle cx="27.5" cy="7" r="2.7" fill="{MARIGOLD}"/>'
)


def inline():
    """The mark as inline markup for a page (decorative: the brand link carries the label)."""
    return f'<svg viewBox="0 0 34 34" aria-hidden="true">{SHAPES}</svg>'


def standalone():
    """The mark as a file (favicon and logo)."""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 34" role="img" aria-label="KaushalSetu logo">{SHAPES}</svg>' + "\n"
