# How many pieces of a product a kar is entitled to ("Op dit moment beschikbaar
# voor levering" on Kar laden, before the physical stock is taken into account).
# It follows the organisation's flow diagram, using the MasterData product's
# Blokkeer / Is logistiek product / Limiet (+ Limietwaarde) / Maximum initiële
# stock and the kar's KarTracker status:
#
#   Blokkeer                → 0
#   Is logistiek product    → Gevraagd door Vereniging (G)
#   Limiet Ongelimiteerd    → G (also without a Limiet or with an unknown one)
#   Limiet Automatisch      → total stock > season demand ? G : floor(G × stock ÷ demand)
#   Limiet Percentage       → floor(G × Limietwaarde %)
#   Limiet Toegewezen aantal→ G
#
# For Automatisch (when stock is short), Percentage and Toegewezen aantal the
# result is capped at Maximum initiële stock as long as the kar isn't
# "Geleverd". The cap counts per kar per product, so a Manueel row only gets
# what the kar's Altsien Select row left of it.
#
# Pure functions, no database: stock_queries.build_kar_detail gathers the
# inputs. Besides the number, the result carries a trace (values + the path of
# diagram nodes taken) so Kar laden can draw the diagram for each row.

from app.db.models.product import Product
from app.schemas.stockmaster import EntitlementTrace

# The kar status (KarTracker) after which Maximum initiële stock no longer applies.
DELIVERED_STATUS = "geleverd"

# The Limiet lookup is a free list of names (MasterData > Limiet); these names,
# compared ignoring case and spaces, pick a rule. Anything else counts as unlimited.
_LIMIT_ALIASES = {
    "ongelimiteerd": "unlimited",
    "onbeperkt": "unlimited",
    "unlimited": "unlimited",
    "automatisch": "automatic",
    "automatic": "automatic",
    "percentage": "percentage",
    "toegewezen aantal": "assigned",
    "toegewezen": "assigned",
    "assigned quantity": "assigned",
    "assigned": "assigned",
}


def limit_kind(name: str | None) -> str:
    """The rule behind a Limiet name: unlimited, automatic, percentage or assigned."""
    if not name:
        return "unlimited"
    return _LIMIT_ALIASES.get(" ".join(name.lower().split()), "unlimited")


def is_delivered_status(status_name: str | None) -> bool:
    """Whether a KarTracker status means the kar has been delivered."""
    return (status_name or "").strip().lower() == DELIVERED_STATUS


def delivery_entitlement(
    product: Product,
    limit_name: str | None,
    requested: int,
    total_stock: int,
    season_demand: int,
    kar_status: str | None,
    cap_used_by_other_row: int = 0,
) -> EntitlementTrace:
    """Walk the flow diagram for one row of Kar laden and return the result with its trace.

    `requested` is the row's Gevraagd door Vereniging, `total_stock` the product's
    free stock plus what's in kars, `season_demand` everything asked for the
    product this season over all kars, and `cap_used_by_other_row` the part of
    Maximum initiële stock already given to the kar's other row of this product.
    """
    kind = limit_kind(limit_name)
    delivered = is_delivered_status(kar_status)
    path: list[str] = []
    share_percent: float | None = None
    # Whether this branch of the diagram ends with the "not yet Geleverd" cap.
    cap_branch = False

    if product.is_blocked:
        path += ["blocked:yes", "result:zero"]
        before_cap = 0
    elif product.is_logistics_product:
        path += ["blocked:no", "logistics:yes", "result:logistics"]
        before_cap = requested
    else:
        path += ["blocked:no", "logistics:no", f"limit:{kind}"]
        if kind == "automatic":
            # Enough stock for everybody (or nothing asked at all): everyone gets what they asked.
            if season_demand <= 0 or total_stock > season_demand:
                path += ["shortage:no", "result:automatic_enough"]
                before_cap = requested
            else:
                # Short: every kar gets the same share of what it asked, rounded down.
                path += ["shortage:yes", "calc:share"]
                share_percent = round(total_stock * 100 / season_demand, 1)
                before_cap = requested * total_stock // season_demand
                cap_branch = True
        elif kind == "percentage":
            # Limietwaarde is the percentage; without one nothing is taken off.
            if product.limit_value is None:
                before_cap = requested
            else:
                share_percent = float(product.limit_value)
                before_cap = requested * product.limit_value // 100
            path.append("calc:percentage")
            cap_branch = True
        elif kind == "assigned":
            before_cap = requested
            cap_branch = True
        else:
            path.append("result:unlimited")
            before_cap = requested

    entitled = before_cap
    if cap_branch:
        if delivered:
            path += ["delivered:yes", f"result:{kind}"]
        else:
            path.append("delivered:no")
            # Not delivered yet: at most Maximum initiële stock over the kar's rows of this product.
            if product.max_initial_stock is not None:
                entitled = min(before_cap, max(product.max_initial_stock - cap_used_by_other_row, 0))
            path.append(f"result:{kind}_capped")

    return EntitlementTrace(
        requested=requested,
        is_blocked=product.is_blocked,
        is_logistics_product=product.is_logistics_product,
        limit_name=limit_name,
        limit_kind=kind,
        limit_value=product.limit_value,
        total_stock=total_stock,
        season_demand=season_demand,
        share_percent=share_percent,
        kar_status=kar_status,
        is_delivered=delivered,
        max_initial_stock=product.max_initial_stock,
        cap_used_by_other_row=cap_used_by_other_row,
        before_cap=max(before_cap, 0),
        entitled=max(entitled, 0),
        path=path,
    )
