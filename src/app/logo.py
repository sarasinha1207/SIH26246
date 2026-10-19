"""
The logo mark, defined once.  build_pages.py puts it in the public header and writes assets/favicon.svg and assets/logo.svg; build_dashboard.py puts it in the dashboard top bar.

The mark: one line that splits in two, blue for demand and employment and marigold for supply (the same colours as the charts), drifting apart on a navy tile.
The dashed segment between the two end points is the gap the product measures and warns about.  Flat colours only, so it reads at 16 px and the same markup can appear
twice on a page.
"""
NAVY, BLUE, MARIGOLD = "#0F2B63", "#8FB0FF", "#F2A93B"

SHAPES = (
    f'<rect width="34" height="34" rx="9" fill="{NAVY}"/>'
    '<rect x=".5" y=".5" width="33" height="33" rx="8.5" fill="none" stroke="#fff" stroke-opacity=".16"/>'
    f'<path d="M8 25.5C13 25 15 21 18 18S23 11.5 27 9.5" fill="none" stroke="{BLUE}" stroke-width="3.2" stroke-linecap="round"/>'
    f'<path d="M8 25.5C13 25.2 17 24 20.5 22.3S25.5 20.5 27 20.5" fill="none" stroke="{MARIGOLD}" stroke-width="3.2" stroke-linecap="round"/>'
    f'<circle cx="27" cy="9.5" r="2.9" fill="{BLUE}"/>'
    f'<circle cx="27" cy="20.5" r="2.9" fill="{MARIGOLD}"/>'
    '<path d="M27 13.5V17" stroke="#fff" stroke-opacity=".55" stroke-width="1.6" stroke-linecap="round" stroke-dasharray="1.2 2.2"/>'
)


def inline():
    """The mark as inline markup for a page (decorative: the brand link carries the label)."""
    return f'<svg viewBox="0 0 34 34" aria-hidden="true">{SHAPES}</svg>'


def standalone():
    """The mark as a file (favicon and logo)."""
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 34 34" role="img" aria-label="KaushalSetu logo">{SHAPES}</svg>' + "\n"
