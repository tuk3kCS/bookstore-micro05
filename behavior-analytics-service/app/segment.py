from __future__ import annotations


def segment_from_counts(counts: dict) -> str:
    """
    Cold-start segmentation heuristic.
    Used as bootstrap labels for model_behavior training.
    """
    add_to_cart = counts.get("add_to_cart", 0)
    checkout_complete = counts.get("checkout_complete", 0)
    view_item = counts.get("view_item", 0) + counts.get("view_book", 0) + counts.get("view_clothes", 0)
    search = counts.get("search", 0)

    if checkout_complete >= 2:
        return "returning_buyer"
    if checkout_complete == 1:
        return "new_buyer"
    if add_to_cart >= 2:
        return "high_intent_browser"
    if view_item >= 5 and search >= 1:
        return "researcher"
    if view_item >= 3:
        return "browser"
    return "new_or_unknown"

