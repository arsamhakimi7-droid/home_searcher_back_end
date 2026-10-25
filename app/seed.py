"""Demo data. The first 8 listings, 4 agents and the Lake Forest guide mirror the original design;
the rest exist so every tab, filter and category tile returns results.
Run `python -m app.seed --reset` to wipe and reload."""
import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import select, func
from sqlalchemy.orm import Session

from .database import Base, SessionLocal, engine
from .models import Agent, Neighborhood, Property

PHOTOS = [f"/assets/{n}.png" for n in
          ("3f0ee", "88b39", "026d3", "6ded9", "ae194", "dc1ae", "3d347", "b72f5")]

AGENTS = [
    ("Sarah Jenkins", "Premier Heights Realty", 5.0, 48, "/assets/2405b.png", "sarah.jenkins@example.com", "(949) 555-0142"),
    ("David Vance", "HomeFind Partners", 5.0, 36, "/assets/034db.png", "david.vance@example.com", "(678) 555-0178"),
    ("Elena Rostova", "Elite Coastal Real Estate", 5.0, 52, "/assets/03594.png", "elena.rostova@example.com", "(941) 555-0119"),
    ("Marcus Sterling", "Apex Landmark Group", 5.0, 41, "/assets/31315.png", "marcus.sterling@example.com", "(973) 555-0163"),
]
# city key -> agent index
AGENT_BY_CITY = {"Lake Forest": 0, "Alpharetta": 1, "Sarasota": 2, "Maplewood": 3}

NEIGHBORHOODS = [
    # name, city, state, zip, description, median, school score, grade, walk, crime label, low?
    ("Lake Forest Heights", "Lake Forest", "CA", "92630",
     "An active, highly-rated community known for its premium school district, low crime index, and lakeside recreational amenities.",
     745_000, 9, "A+", 82, "Low (Top 10%)", True),
    ("Maplewood Village", "Maplewood", "NJ", "07040",
     "A walkable village with a commuter rail line to Manhattan, a lively downtown and tree-lined residential streets.",
     690_000, 8, "A", 88, "Low (Top 20%)", True),
    ("Alpharetta Downtown", "Alpharetta", "GA", "30009",
     "A fast-growing hub with top-ranked schools, greenway trails and a thriving restaurant district.",
     720_000, 9, "A", 64, "Low (Top 15%)", True),
    ("Siesta Bayfront", "Sarasota", "FL", "34236",
     "Coastal living near award-winning beaches, arts venues and the downtown waterfront.",
     830_000, 8, "A-", 76, "Moderate", False),
]

ZIP = {"Lake Forest": "92630", "Maplewood": "07040", "Alpharetta": "30009", "Sarasota": "34236"}
STATE = {"Lake Forest": "CA", "Maplewood": "NJ", "Alpharetta": "GA", "Sarasota": "FL"}

DESC = ("Bright, well-kept home with an open floor plan, updated kitchen and generous outdoor space. "
        "Close to schools, parks and shopping.")


def _prop(address, city, price, beds, baths, sqft, home_type="house", listing_type="buy",
          photo=0, **kw) -> dict:
    return dict(address=address, city=city, state=STATE[city], zip_code=ZIP[city], price=price,
                beds=beds, baths=baths, sqft=sqft, home_type=home_type, listing_type=listing_type,
                image=PHOTOS[photo % len(PHOTOS)], description=DESC, **kw)


def build_properties(now: datetime) -> list[dict]:
    h, d = timedelta(hours=1), timedelta(days=1)
    return [
        # --- Trending (design cards 1-4) ---
        _prop("102 Oakwood Dr", "Lake Forest", 849_000, 4, 3, 3200, photo=0, original_price=899_000, listed_at=now - 9 * d, is_trending=True),
        _prop("408 Cherry Lane", "Maplewood", 625_000, 3, 2, 2150, photo=1, listed_at=now - 3 * h, is_trending=True),
        _prop("29 Royal Crest Lane", "Alpharetta", 1_120_000, 5, 4, 4800, photo=2, listed_at=now - 6 * d, open_house_at=now + 2 * d, is_trending=True),
        _prop("802 Ocean Blvd", "Sarasota", 1_450_000, 4, 3, 3500, photo=3, listed_at=now - 21 * d, is_trending=True),
        # --- Recommended (design cards 5-8) ---
        _prop("125 Valley View Road", "Maplewood", 589_000, 3, 2, 1980, photo=4, listed_at=now - 12 * d, is_recommended=True),
        _prop("45 Meadowlane Dr", "Alpharetta", 950_000, 4, 3, 3100, photo=5, listed_at=now - 15 * d, is_recommended=True),
        _prop("89 Pinecrest Way", "Lake Forest", 710_000, 3, 2, 2400, photo=6, listed_at=now - 8 * d, is_recommended=True),
        _prop("91 Beach Walk Lane", "Sarasota", 1_300_000, 4, 4, 3350, photo=7, listed_at=now - 18 * d, is_recommended=True),
        # --- More for sale (feeds category tiles) ---
        _prop("17 Harbor View Ct", "Sarasota", 480_000, 2, 2, 1400, "condo", photo=2, listed_at=now - 4 * d, is_new_construction=True),
        _prop("310 Ridgeline Ave", "Lake Forest", 695_000, 3, 2.5, 1750, "townhouse", photo=5, original_price=725_000, listed_at=now - 14 * d),
        _prop("56 Elm Street", "Maplewood", 735_000, 4, 2.5, 2600, photo=1, listed_at=now - 5 * d, open_house_at=now + 3 * d),
        _prop("7 Bankers Row", "Alpharetta", 399_000, 3, 2, 1900, photo=6, listed_at=now - 30 * d, is_foreclosure=True),
        _prop("220 Crescent Dr", "Lake Forest", 1_380_000, 5, 4, 4100, photo=3, listed_at=now - 5 * h),
        _prop("1 Gulfstream Pl", "Sarasota", 565_000, 2, 2, 1250, "condo", photo=4, listed_at=now - 8 * h, is_new_construction=True),
        # --- Rentals (price = monthly rent) ---
        _prop("14 Maple Court", "Maplewood", 2_800, 2, 1.5, 1200, "townhouse", "rent", photo=0, listed_at=now - 2 * d),
        _prop("903 Lakeshore Blvd", "Lake Forest", 3_400, 2, 2, 1100, "condo", "rent", photo=5, listed_at=now - 6 * h),
        _prop("61 Peachtree Row", "Alpharetta", 2_950, 3, 2, 1800, "house", "rent", photo=7, listed_at=now - 10 * d),
        _prop("480 Bayfront Dr", "Sarasota", 2_300, 1, 1, 800, "condo", "rent", photo=2, listed_at=now - 3 * d),
        # --- Recently sold ---
        _prop("33 Oak Hollow Rd", "Lake Forest", 810_000, 4, 3, 2900, listing_type="sold", photo=6, listed_at=now - 50 * d, sold_at=now - 12 * d),
        _prop("78 Birchwood Ln", "Maplewood", 560_000, 3, 2, 1850, listing_type="sold", photo=1, listed_at=now - 45 * d, sold_at=now - 20 * d),
        _prop("5 Windsor Chase", "Alpharetta", 1_050_000, 5, 4, 4200, listing_type="sold", photo=2, listed_at=now - 60 * d, sold_at=now - 9 * d),
        _prop("640 Siesta Dr", "Sarasota", 720_000, 3, 2.5, 1950, "townhouse", "sold", photo=7, listed_at=now - 40 * d, sold_at=now - 15 * d),
    ]


def seed(db: Session, reset: bool = False) -> bool:
    """Returns True if data was inserted."""
    if reset:
        Base.metadata.drop_all(db.get_bind())
        Base.metadata.create_all(db.get_bind())
    elif db.scalar(select(func.count()).select_from(Property)):
        return False

    agents = [Agent(name=n, brokerage=b, rating=r, recent_sales=s, avatar=a, email=e, phone=p)
              for n, b, r, s, a, e, p in AGENTS]
    db.add_all(agents)
    hoods = {}
    for n, city, st, z, desc, med, ss, sg, ws, cl, low in NEIGHBORHOODS:
        hoods[z] = Neighborhood(name=n, city=city, state=st, zip_code=z, description=desc, median_price=med,
                                school_score=ss, school_grade=sg, walk_score=ws, crime_label=cl, crime_is_low=low)
    db.add_all(hoods.values())
    db.flush()

    for row in build_properties(datetime.now(timezone.utc)):
        row["agent_id"] = agents[AGENT_BY_CITY[row["city"]]].id
        row["neighborhood_id"] = hoods[row["zip_code"]].id
        db.add(Property(**row))
    db.commit()
    return True


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="drop all tables and reseed")
    args = ap.parse_args()
    Base.metadata.create_all(engine)
    with SessionLocal() as s:
        print("Seeded." if seed(s, reset=args.reset) else "Database already has data (use --reset to reload).")
