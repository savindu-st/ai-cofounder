# Deterministic Financial Calculation Engine
def calculate_projections(starting_customers: int, monthly_price: float, growth_rate: float, churn_rate: float, months: int = 12):
    projections = []
    customers = starting_customers
    for m in range(1, months + 1):
        revenue = customers * monthly_price
        projections.append({
            "month": m,
            "customers": int(customers),
            "revenue": round(revenue, 2)
        })
        customers = customers * (1 + growth_rate - churn_rate)
    return projections
