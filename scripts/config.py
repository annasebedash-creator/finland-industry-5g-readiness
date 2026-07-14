"""Shared configuration: sector definitions, metrics, and scoring weights.

The analysis maps every Finnish enterprise sector to the industry grouping that
Statistics Finland uses in its "Use of information technology in enterprises"
survey (table 14yc), because that is the finest level at which real AI / robotics
/ IoT adoption is published per industry. Economic size (table 13vy) is summed
from the constituent TOL 2008 letter/2-digit classes to match those groups.

Weights below are an explicit *analyst framework* — a documented judgement call,
not an official Statistics Finland or DNA figure. They are here to be argued with.
"""

# StatFin PxWeb tables
READINESS_TABLE = ("icte", "14yc")   # Use of IT in enterprises, by industry
ECONOMY_TABLE = ("yrti", "13vy")     # Enterprises by industry (turnover, personnel, count)

READINESS_YEARS = ["2025", "2024", "2023"]  # take latest non-null per metric
ECONOMY_YEAR = "2024"                         # latest available in 13vy

# --- Sectors -------------------------------------------------------------
# code       -> the 14yc industry-group code (readiness data key)
# econ_codes -> TOL 2008 classes in 13vy that sum to the same group (size data)
# industrial -> physical/asset-heavy sectors most addressable by private 5G
SECTORS = [
    {"id": 1, "code": "CTE",      "short": "Manufacturing & Energy",
     "name": "Manufacturing; energy & utilities (C–E)",
     "econ_codes": ["C", "D", "E"], "industrial": True},
    {"id": 2, "code": "H",        "short": "Transport & Storage",
     "name": "Transportation and storage (H)",
     "econ_codes": ["H"], "industrial": True},
    {"id": 3, "code": "F41TF43",  "short": "Construction",
     "name": "Construction (F)",
     "econ_codes": ["F"], "industrial": True},
    {"id": 4, "code": "G45_G46",  "short": "Wholesale & Vehicle Trade",
     "name": "Wholesale & motor-vehicle trade (45–46)",
     "econ_codes": ["G45", "G46"], "industrial": False},
    {"id": 5, "code": "G47",      "short": "Retail",
     "name": "Retail trade (47)",
     "econ_codes": ["G47"], "industrial": False},
    {"id": 6, "code": "I55_I56",  "short": "Accommodation & Food",
     "name": "Accommodation and food service (I)",
     "econ_codes": ["I"], "industrial": False},
    {"id": 7, "code": "J",        "short": "Information & Communication",
     "name": "Information and communication (J)",
     "econ_codes": ["J"], "industrial": False},
    {"id": 8, "code": "M",        "short": "Professional & Technical",
     "name": "Professional, scientific & technical (M)",
     "econ_codes": ["M"], "industrial": False},
    {"id": 9, "code": "L_N_S951", "short": "Real Estate & Admin",
     "name": "Real estate, admin & support services (L, N, S951)",
     "econ_codes": ["L", "N"], "industrial": False},
]

# --- Readiness metrics (from 14yc, % of enterprises) ---------------------
# metric_code, label, weight. Weights sum to 1.0. Higher = more ready.
READINESS_METRICS = [
    ("icte22", "Uses AI technologies",                     0.20),
    ("icte29", "Autonomous robots / vehicles / drones",    0.20),
    ("icte38", "Uses IoT smart-device / sensor data",      0.18),
    ("icte28", "AI-based process automation (RPA)",        0.14),
    ("icte27", "Machine learning for data analysis",       0.10),
    ("icte11", "Uses cloud services",                      0.10),
    ("icte02", "≥100 Mbps broadband connection",      0.08),
]

# --- Attractiveness metrics (from 13vy) ----------------------------------
# contentscode, label, weight. Higher = more attractive (bigger prize).
ECONOMY_METRICS = [
    ("yri_Liikevaihto",       "Turnover (€1,000)",        0.50),
    ("yri_Henkmaara",         "Personnel (staff-years)",       0.30),
    ("yri_Yritysten_Lukumaara", "Number of enterprises",       0.20),
]

# Names used on the two composite axes
AXIS_ATTRACTIVENESS = "Market attractiveness"
AXIS_READINESS = "AI & 5G readiness"
