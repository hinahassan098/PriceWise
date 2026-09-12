from app.database import Base, SessionLocal, engine
from app.services.live_search import live_search
from app.services.seed import seed

Base.metadata.create_all(bind=engine)
db = SessionLocal()
seed(db)
for q in ["brite 1kg", "lays"]:
    d = live_search(db, q, persist=True)
    print("Q", q, "stores", d["stores_queried"], "products", len(d["results"]), "flat", len(d["all_store_prices"]))
    for r in d["results"][:4]:
        offers = ", ".join(
            f"{o['retailer_name']}={o['price']}({o['availability']})" for o in r["offers"]
        )
        print(" ", r["name"], r["size_label"], "::", offers)
db.close()
