def validate(product, budget):
    if product["price"] > budget:
        return False, "over_budget"

    if product.get("rating", 0) < 4:
        return False, "low_rating"

    return True, "approved"