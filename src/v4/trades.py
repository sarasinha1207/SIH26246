"""
v4 - the 25 trades (NCO-2015 occupation families, five per sector) and the assumptions that give each its own behaviour.

Every number here is a MODELLING ASSUMPTION for the simulator, not a statistic.  The trade list itself is the NCO-2015 crosswalk
(data/raw/sector_nco_crosswalk.csv); the order of the five trades in each sector must match it.

  e          share of the sector's employed workers (the five add up to 1)
  v          vacancy intensity: openings per worker relative to the sector average
  wage       average monthly wage relative to the sector average
  g          annual drift of the trade's share against its sector (log points per year)
  cm         sensitivity to the COVID-19 shock relative to the sector (1.0 = same)
  sm         sensitivity to the seasonal pattern of the sector (1.0 = same)
  seat       weight in the sector's training seats (relative to its employment share)
  fa, ga, ya female share, graduate share and share aged 15-24, as differences from the sector average
"""
import numpy as np

K = ("code", "e", "v", "wage", "g", "cm", "sm", "seat", "fa", "ga", "ya")
_ROWS = {
    "Manufacturing": [
        (7223, .22, 1.00, 1.05, .000, 1.00, 1.0, 1.2, -.02, .00, .00),
        (8212, .20, 1.25, 1.00, .012, .90, 1.0, 1.0, .20, .02, .04),
        (8131, .15, .85, 1.10, .000, .80, 1.0, .7, -.03, .04, -.02),
        (7233, .18, 1.00, 1.08, .004, .95, 1.0, 1.3, -.05, .00, .00),
        (7212, .25, 1.10, .95, .000, 1.10, 1.0, 1.6, -.05, -.03, .02),
    ],
    "Construction": [
        (7111, .22, 1.00, 1.05, .006, 1.00, 1.0, 1.2, .00, .01, .00),
        (7112, .20, .95, .95, .000, 1.05, 1.2, 1.1, .00, -.02, .00),
        (7115, .14, 1.00, 1.00, -.004, 1.00, 1.0, 1.4, -.02, .00, .00),
        (7126, .10, 1.15, 1.08, .010, .90, .9, 1.5, -.03, .01, .01),
        (9313, .34, .90, .80, -.002, 1.20, 1.5, .4, .06, -.03, .00),
    ],
    "IT-ITeS": [
        (2511, .15, 1.10, 1.20, .010, 1.00, 1.0, .8, -.02, .04, -.03),
        (2512, .36, 1.30, 1.10, .015, 1.00, 1.0, 1.2, -.04, .02, .02),
        (2513, .12, 1.10, .85, .008, 1.00, 1.0, 1.0, .08, .00, .03),
        (2514, .22, 1.00, 1.00, -.005, 1.00, 1.0, 1.0, .00, .02, .00),
        (3512, .15, .85, .65, -.010, 1.00, 1.0, 1.8, .05, -.10, .05),
    ],
    "Healthcare": [
        (2211, .10, 1.00, 1.80, .000, .90, 1.0, .3, -.02, .30, -.15),
        (2212, .06, 1.10, 2.60, .004, .90, 1.0, .15, -.06, .35, -.20),
        (2221, .34, 1.25, .95, .010, .90, 1.0, 1.8, .30, .05, .02),
        (3221, .30, 1.00, .70, .004, 1.00, 1.0, 2.0, .25, -.15, .04),
        (3212, .20, .90, .75, .012, 1.00, 1.0, 1.3, .05, .05, .04),
    ],
    "Textiles and Apparel": [
        (8153, .38, 1.05, .95, .004, 1.00, 1.1, 1.5, .15, -.03, .02),
        (8152, .22, .90, 1.00, -.004, 1.00, 1.0, 1.0, .00, .00, .00),
        (8151, .15, .80, .90, -.012, 1.05, 1.0, .8, .05, -.02, .00),
        (7531, .15, 1.05, 1.00, .000, 1.00, 1.0, 1.6, .10, .00, .00),
        (7533, .10, .95, .85, -.002, 1.00, 1.0, 1.2, .20, -.02, .00),
    ],
}


def params(sector):
    """List of five dicts for the sector, in crosswalk order."""
    rows = [dict(zip(K, r)) for r in _ROWS[sector]]
    assert abs(sum(r["e"] for r in rows) - 1.0) < 1e-9, sector
    return rows


def arrays(sector):
    """Parameter name -> numpy array of length 5."""
    rows = params(sector)
    return {k: np.array([r[k] for r in rows], float) for k in K if k != "code"} | {"code": [r["code"] for r in rows]}
