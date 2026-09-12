from __future__ import annotations

from app.collectors.metro_next import MetroNextCollector
from app.collectors.naheed_html import NaheedHtmlCollector
from app.collectors.shopify import DEFAULT_QUERIES, ShopifyCollector
from app.collectors.spar_html import NiceMartCollector, SparHtmlCollector

SPRINGS_COLLECTIONS = [
    "laundry",
    "household",
    "beverages",
    "drinks",
    "dairy",
    "baby",
    "baby-care",
    "snacks",
    "food-cupboard",
    "tea-coffee",
    "cooking-oil",
]


class SpringsCollector(ShopifyCollector):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            retailer_id="springs",
            base_url="https://springs.com.pk",
            search_queries=DEFAULT_QUERIES,
            collection_handles=SPRINGS_COLLECTIONS,
            **kwargs,
        )


class AlfatahCollector(ShopifyCollector):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            retailer_id="alfatah",
            base_url="https://alfatah.pk",
            search_queries=DEFAULT_QUERIES,
            collection_handles=["snacks", "laundry", "beverages", "household", "dairy"],
            **kwargs,
        )


class GreenValleyCollector(ShopifyCollector):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            retailer_id="green-valley",
            base_url="https://greenvalley.pk",
            search_queries=DEFAULT_QUERIES,
            collection_handles=["grocery-food", "laundry", "beverages", "snacks", "household"],
            **kwargs,
        )


class AlMadinaCollector(ShopifyCollector):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            retailer_id="al-madina",
            base_url="https://www.almadinastore.pk",
            search_queries=DEFAULT_QUERIES,
            collection_handles=["all"],
            **kwargs,
        )


class SnapcartCollector(ShopifyCollector):
    def __init__(self, **kwargs) -> None:
        super().__init__(
            retailer_id="snapcart",
            base_url="https://snapcart.pk",
            search_queries=DEFAULT_QUERIES,
            collection_handles=["snacks", "grocery", "beverages", "household", "laundry"],
            **kwargs,
        )


# Registry of live-capable collectors (public JSON / allowed storefronts).
LIVE_COLLECTORS = {
    "springs": SpringsCollector,
    "alfatah": AlfatahCollector,
    "green-valley": GreenValleyCollector,
    "al-madina": AlMadinaCollector,
    "snapcart": SnapcartCollector,
    "spar": SparHtmlCollector,
    "nice-mart": NiceMartCollector,
    "naheed": NaheedHtmlCollector,
    "metro": MetroNextCollector,
}

# Fast JSON-only storefronts for interactive search (HTML scrapers are too slow on Render).
FAST_LIVE_COLLECTORS = {
    "springs": SpringsCollector,
    "alfatah": AlfatahCollector,
    "green-valley": GreenValleyCollector,
    "al-madina": AlMadinaCollector,
    "snapcart": SnapcartCollector,
}


def get_live_collectors() -> dict:
    return {key: cls() for key, cls in LIVE_COLLECTORS.items()}


def get_fast_live_collectors() -> dict:
    return {key: cls() for key, cls in FAST_LIVE_COLLECTORS.items()}