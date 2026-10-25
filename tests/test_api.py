import math

from app import mortgage


# ---------- health / auth ----------

def test_health(client):
    assert client.get("/api/health").json() == {"detail": "ok"}


def test_register_login_me(client):
    payload = {"full_name": "Ada Lovelace", "email": "Ada@Example.com", "password": "correct-horse"}
    r = client.post("/api/auth/register", json=payload)
    assert r.status_code == 201
    assert r.json()["user"]["email"] == "ada@example.com"          # normalised

    assert client.post("/api/auth/register", json=payload).status_code == 409   # duplicate (case-insensitive)

    ok = client.post("/api/auth/login", json={"email": "ada@example.com", "password": "correct-horse"})
    assert ok.status_code == 200
    token = ok.json()["access_token"]
    me = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me.json()["full_name"] == "Ada Lovelace"


def test_login_failures_are_generic(client):
    assert client.post("/api/auth/login", json={"email": "nobody@example.com", "password": "x"}).status_code == 401
    assert client.post("/api/auth/login", json={"email": "ada@example.com", "password": "wrong"}).status_code == 401


def test_register_validation(client):
    assert client.post("/api/auth/register", json={"full_name": "A", "email": "bad", "password": "longenough"}).status_code == 422
    assert client.post("/api/auth/register", json={"full_name": "A", "email": "a@b.co", "password": "short"}).status_code == 422


def test_me_requires_valid_token(client):
    assert client.get("/api/auth/me").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer garbage"}).status_code == 401


# ---------- properties ----------

def test_trending_matches_design(client):
    items = client.get("/api/properties/trending").json()
    assert [p["address"] for p in items] == ["102 Oakwood Dr", "408 Cherry Lane", "29 Royal Crest Lane", "802 Ocean Blvd"]
    assert [p["badge"] and p["badge"]["label"] for p in items] == ["Price Reduced", "New Listing", "Open House", None]
    assert items[0]["full_address"] == "102 Oakwood Dr, Lake Forest, CA"
    assert items[0]["est_monthly"] > 0


def test_recommended_default(client):
    items = client.get("/api/properties/recommended").json()
    assert len(items) == 4
    assert all(p["listing_type"] == "buy" for p in items)


def test_search_by_text_and_zip(client):
    r = client.get("/api/properties", params={"q": "lake forest"}).json()
    assert r["total"] > 0 and all(p["city"] == "Lake Forest" for p in r["items"])
    r = client.get("/api/properties", params={"q": "07040"}).json()
    assert r["total"] > 0 and all(p["zip_code"] == "07040" for p in r["items"])
    assert client.get("/api/properties", params={"q": "zzzzzz"}).json()["total"] == 0


def test_search_escapes_like_wildcards(client):
    assert client.get("/api/properties", params={"q": "%"}).json()["total"] == 0
    assert client.get("/api/properties", params={"q": "_"}).json()["total"] == 0


def test_filters_and_sort(client):
    r = client.get("/api/properties", params={
        "listing_type": "buy", "min_price": 500_000, "max_price": 900_000, "beds": 3, "home_type": "house", "sort": "price_asc",
    }).json()
    assert r["total"] > 0
    prices = [p["price"] for p in r["items"]]
    assert prices == sorted(prices)
    assert all(500_000 <= p["price"] <= 900_000 and p["beds"] >= 3 and p["home_type"] == "house" for p in r["items"])


def test_rent_and_sold_tabs(client):
    rent = client.get("/api/properties", params={"listing_type": "rent"}).json()
    assert rent["total"] >= 4 and all(p["est_monthly"] is None for p in rent["items"])
    sold = client.get("/api/properties", params={"listing_type": "sold"}).json()
    assert sold["total"] >= 4 and all(p["badge"]["key"] == "sold" for p in sold["items"])


def test_pagination(client):
    p1 = client.get("/api/properties", params={"page_size": 5, "page": 1}).json()
    p2 = client.get("/api/properties", params={"page_size": 5, "page": 2}).json()
    assert len(p1["items"]) == 5 and p1["pages"] == math.ceil(p1["total"] / 5)
    assert {p["id"] for p in p1["items"]}.isdisjoint({p["id"] for p in p2["items"]})


def test_filter_validation(client):
    assert client.get("/api/properties", params={"min_price": 10, "max_price": 5}).status_code == 422
    assert client.get("/api/properties", params={"home_type": "castle"}).status_code == 422
    assert client.get("/api/properties", params={"category": "nope"}).status_code == 422
    assert client.get("/api/properties", params={"page_size": 500}).status_code == 422


def test_categories_all_populated(client):
    cats = client.get("/api/properties/categories").json()
    assert [c["key"] for c in cats] == ["new-listings", "open-houses", "price-reduced", "recently-sold", "new-construction", "foreclosures"]
    assert all(c["count"] > 0 for c in cats), cats
    for c in cats:
        r = client.get("/api/properties", params={"category": c["key"], "page_size": 50}).json()
        assert r["total"] == c["count"]


def test_property_detail_and_404(client):
    pid = client.get("/api/properties/trending").json()[0]["id"]
    d = client.get(f"/api/properties/{pid}").json()
    assert d["agent"]["name"] == "Sarah Jenkins"
    assert client.get("/api/properties/999999").status_code == 404


def test_suggestions(client):
    s = client.get("/api/properties/suggestions", params={"q": "sara"}).json()
    assert {"label": "Sarasota, FL", "kind": "city", "value": "Sarasota, FL"} in s


# ---------- favorites ----------

def test_favorites_flow(client, auth):
    headers, _ = auth
    assert client.get("/api/favorites").status_code == 401
    pid = client.get("/api/properties/trending").json()[1]["id"]

    assert client.put(f"/api/favorites/{pid}", headers=headers).status_code == 204
    assert client.put(f"/api/favorites/{pid}", headers=headers).status_code == 204     # idempotent
    assert client.get("/api/favorites/ids", headers=headers).json() == [pid]
    assert [p["id"] for p in client.get("/api/favorites", headers=headers).json()] == [pid]

    flagged = client.get("/api/properties/trending", headers=headers).json()
    assert [p["is_favorite"] for p in flagged] == [False, True, False, False]
    # an anonymous user never sees someone else's flags
    assert not any(p["is_favorite"] for p in client.get("/api/properties/trending").json())

    assert client.delete(f"/api/favorites/{pid}", headers=headers).status_code == 204
    assert client.get("/api/favorites/ids", headers=headers).json() == []
    assert client.put("/api/favorites/999999", headers=headers).status_code == 404


def test_recommendations_personalise_from_favorites(client, auth):
    headers, _ = auth
    luxury = client.get("/api/properties", params={"listing_type": "buy", "sort": "price_desc", "page_size": 1}).json()["items"][0]
    client.put(f"/api/favorites/{luxury['id']}", headers=headers)
    recs = client.get("/api/properties/recommended", headers=headers).json()
    assert luxury["id"] not in [p["id"] for p in recs]
    assert recs[0]["price"] >= 1_000_000


# ---------- agents ----------

def test_agents_list_and_contact(client, auth):
    agents = client.get("/api/agents").json()
    assert len(agents) == 4
    assert {a["name"] for a in agents} == {"Sarah Jenkins", "David Vance", "Elena Rostova", "Marcus Sterling"}

    aid = agents[0]["id"]
    body = {"name": "Buyer", "email": "buyer@example.com", "message": "I'd love to see this home."}
    r = client.post(f"/api/agents/{aid}/contact", json=body)
    assert r.status_code == 201 and "sent to" in r.json()["detail"]

    pid = client.get("/api/properties/trending").json()[0]["id"]
    assert client.post(f"/api/agents/{aid}/contact", json={**body, "property_id": pid}, headers=auth[0]).status_code == 201
    assert client.post(f"/api/agents/{aid}/contact", json={**body, "property_id": 99999}).status_code == 404
    assert client.post("/api/agents/99999/contact", json=body).status_code == 404
    assert client.post(f"/api/agents/{aid}/contact", json={**body, "message": "x"}).status_code == 422
    assert client.post(f"/api/agents/{aid}/contact", json={**body, "email": "nope"}).status_code == 422


# ---------- neighborhoods ----------

def test_neighborhoods(client):
    first = client.get("/api/neighborhoods").json()[0]
    assert first["label"] == "Lake Forest (92630)"
    assert first["schools_display"] == "9/10 (A+)" and first["walk_display"] == "82 / 100"
    assert client.get("/api/neighborhoods/92630").json()["median_price"] == 745_000
    assert client.get("/api/neighborhoods", params={"q": "sarasota"}).json()[0]["zip_code"] == "34236"
    assert client.get("/api/neighborhoods", params={"q": "nowhere"}).json() == []
    assert client.get("/api/neighborhoods/00000").status_code == 404


# ---------- mortgage ----------

def test_mortgage_math_known_value():
    # $200k, 6% 30y => $1,199.10/mo (standard amortisation table value)
    assert round(mortgage.monthly_payment(200_000, 6.0, 30), 2) == 1199.10
    assert round(mortgage.monthly_payment(120_000, 0, 10), 2) == 1000.00


def test_calculate_endpoint(client):
    r = client.post("/api/mortgage/calculate", json={
        "home_price": 500_000, "down_payment_pct": 20, "annual_rate": 6.0, "years": 30, "include_schedule": True,
    }).json()
    assert r["loan_amount"] == 400_000 and r["down_payment"] == 100_000
    assert r["principal_and_interest"] == 2398.20
    assert round(r["total_paid"], 0) == round(400_000 + r["total_interest"], 0)
    assert len(r["schedule"]) == 30 and r["schedule"][-1]["remaining_balance"] < 1


def test_calculate_defaults_and_validation(client):
    r = client.post("/api/mortgage/calculate", json={"home_price": 400_000}).json()
    assert r["down_payment"] == 80_000 and r["annual_rate"] == client.get("/api/mortgage/rates").json()["rates"][0]["rate"]
    assert client.post("/api/mortgage/calculate", json={"home_price": 100, "down_payment": 500}).status_code == 422
    assert client.post("/api/mortgage/calculate", json={"home_price": -5}).status_code == 422
    assert client.post("/api/mortgage/calculate", json={"home_price": 5, "years": 0}).status_code == 422


def test_affordability_respects_dti(client):
    body = {"annual_income": 120_000, "monthly_debts": 500, "down_payment": 60_000, "credit_band": "excellent"}
    r = client.post("/api/mortgage/affordability", json=body).json()
    assert r["max_price"] > 60_000
    assert r["debt_to_income"] <= 0.36 + 1e-6
    # heavier debts or worse credit can only lower what you can afford
    worse = client.post("/api/mortgage/affordability", json={**body, "monthly_debts": 2000, "credit_band": "poor"}).json()
    assert worse["max_price"] < r["max_price"]
    broke = client.post("/api/mortgage/affordability", json={"annual_income": 30_000, "monthly_debts": 2_000}).json()
    assert broke["max_price"] >= 0 and broke["monthly_housing_budget"] == 0


def test_pre_approval(client):
    body = {"full_name": "Pat Buyer", "email": "pat@example.com", "annual_income": 150_000, "monthly_debts": 300,
            "down_payment": 80_000, "credit_band": "good"}
    r = client.post("/api/mortgage/pre-approval", json=body)
    assert r.status_code == 201 and r.json()["estimate"]["max_price"] > 0
    assert client.post("/api/mortgage/pre-approval", json={**body, "email": "bad"}).status_code == 422


# ---------- misc ----------

def test_subscribe_idempotent(client):
    for _ in range(2):
        assert client.post("/api/subscribe", json={"email": "Fan@Example.com"}).status_code == 201
    assert client.post("/api/subscribe", json={"email": "nope"}).status_code == 422
