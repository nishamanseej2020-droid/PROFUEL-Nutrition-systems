
from flask import Flask, render_template, jsonify, request
from datetime import datetime
from supabase_client import supabase

app = Flask(__name__)


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def get_products():
    """Retrieve products and calculate stock from inventory ledger."""

    products_response = (
        supabase.table("products")
        .select("*")
        .execute()
    )

    movements_response = (
        supabase.table("inventory_movements")
        .select("product_id, movement_type, quantity")
        .execute()
    )

    categories_response = (
        supabase.table("product_categories")
        .select("id, name")
        .execute()
    )

    products_data = products_response.data or []
    movements = movements_response.data or []
    categories = categories_response.data or []

    category_map = {
        str(c["id"]): c["name"]
        for c in categories
    }

    # Calculate stock using inventory movements
    inbound = {
        "opening",
        "purchase_receipt",
        "production_output",
        "sale_return"
    }

    outbound = {
        "production_use",
        "sale",
        "adjustment",
        "damage",
        "expiry"
    }

    stock_map = {}

    for movement in movements:
        product_id = str(movement["product_id"])
        quantity = float(movement["quantity"])
        movement_type = movement["movement_type"]

        if movement_type in inbound:
            stock_map[product_id] = (
                stock_map.get(product_id, 0) + quantity
            )

        elif movement_type in outbound:
            stock_map[product_id] = (
                stock_map.get(product_id, 0) - quantity
            )

    result = []

    for product in products_data:
        product_id = str(product["id"])
        stock = stock_map.get(product_id, 0)
        reorder_level = float(product.get("reorder_level") or 20)

        result.append({
            "id": product["id"],
            "name": product.get("name", ""),
            "sku": product.get("sku", ""),
            "category": category_map.get(
                str(product.get("category_id")), "Other"
            ),
            "stock": stock,
            "price": float(product.get("retail_price") or 0),
            "status": (
                "Low Stock"
                if stock <= reorder_level
                else "In Stock"
            )
        })

    return result


def get_orders():
    """Retrieve recent sales orders."""

    response = (
        supabase.table("sales_orders")
        .select("*")
        .order("created_at", desc=True)
        .limit(10)
        .execute()
    )

    result = []

    for order in response.data or []:
        result.append({
            "id": order.get("order_number") or str(order.get("id", "")),
            "customer": order.get("customer_name", "Customer"),
            "date": str(
                order.get("order_date")
                or order.get("created_at")
                or ""
            )[:10],
            "amount": float(
                order.get("total_amount") or 0
            ),
            "status": order.get("status", "Pending")
        })

    return result


def get_customers():
    """Retrieve customer records."""

    response = (
        supabase.table("customers")
        .select("*")
        .limit(100)
        .execute()
    )

    result = []

    for customer in response.data or []:
        result.append({
            "name": (
                customer.get("name")
                or customer.get("customer_name")
                or "Customer"
            ),
            "email": customer.get("email", ""),
            "orders": customer.get("total_orders", 0),
            "spent": float(customer.get("total_spent") or 0)
        })

    return result


# --------------------------------------------------
# ADMIN DASHBOARD
# --------------------------------------------------

@app.route("/")
def dashboard():

    try:
        products = get_products()
        orders = get_orders()
        customers = get_customers()

        return render_template(
            "dashboard.html",
            products=products,
            orders=orders,
            customers=customers
        )

    except Exception as error:
        app.logger.exception("Dashboard loading failed")
        return f"Dashboard loading failed: {str(error)}", 500


# --------------------------------------------------
# PRODUCT API
# --------------------------------------------------


from postgrest.exceptions import APIError

@app.route("/api/products", methods=["GET", "POST"])
def product_api():
    try:
        if request.method == "GET":
            return jsonify(get_products())

        data = request.get_json(silent=True) or {}

        name = str(data.get("name") or "").strip()
        sku = str(data.get("sku") or "").strip()

        if not name or not sku:
            return jsonify({
                "error": "Product name and SKU are required."
            }), 400

        try:
            price = float(data.get("price") or 0)
            cost_price = float(data.get("cost_price") or 0)
            reorder_level = int(data.get("reorder_level") or 20)
        except (ValueError, TypeError):
            return jsonify({
                "error": "Price, cost price and reorder level must be valid numbers."
            }), 400

        if price < 0 or cost_price < 0 or reorder_level < 0:
            return jsonify({
                "error": "Values cannot be negative."
            }), 400

        product_data = {
            "name": name,
            "sku": sku,
            "description": data.get("description") or "",
            "product_type": "finished_good",
            "retail_price": price,
            "cost_price": cost_price,
            "reorder_level": reorder_level,
            "status": "active"
        }

        # Only send category_id when supplied.
        category_id = data.get("category_id")

        if category_id not in (None, ""):
            product_data["category_id"] = category_id

        response = (
            supabase.table("products")
            .insert(product_data)
            .execute()
        )

        if not response.data:
            return jsonify({
                "error": "Product insertion returned no data."
            }), 400

        return jsonify({
            "message": "Product added successfully.",
            "product": response.data[0]
        }), 201

    except APIError as error:
        app.logger.exception("Supabase product insertion failed")

        return jsonify({
            "error": "Supabase database error.",
            "details": str(error)
        }), 400

    except Exception as error:
        app.logger.exception("Product API failed")

        return jsonify({
            "error": "Product creation failed.",
            "details": str(error)
        }), 500


# --------------------------------------------------
# INVENTORY API
# --------------------------------------------------

@app.route("/api/inventory", methods=["GET"])
def inventory_api():

    try:
        products = get_products()

        low_stock = [
            product for product in products
            if product["status"] == "Low Stock"
        ]

        return jsonify({
            "total_products": len(products),
            "low_stock_count": len(low_stock),
            "products": products,
            "low_stock_products": low_stock
        })

    except Exception as error:
        app.logger.exception("Inventory API failed")
        return jsonify({"error": str(error)}), 500


# --------------------------------------------------
# ORDERS API
# --------------------------------------------------

@app.route("/api/orders", methods=["GET"])
def orders_api():

    try:
        return jsonify(get_orders())

    except Exception as error:
        app.logger.exception("Orders API failed")
        return jsonify({"error": str(error)}), 500


# --------------------------------------------------
# CUSTOMERS API
# --------------------------------------------------

@app.route("/api/customers", methods=["GET"])
def customers_api():

    try:
        return jsonify(get_customers())

    except Exception as error:
        app.logger.exception("Customers API failed")
        return jsonify({"error": str(error)}), 500


# --------------------------------------------------
# CHATBOT
# --------------------------------------------------

@app.route("/api/chat", methods=["POST"])
def chat():

    try:
        message = (
            request.get_json(silent=True) or {}
        ).get("message", "").lower()

        products = get_products()

        if any(word in message for word in [
            "stock", "inventory", "low"
        ]):

            low = [
                p for p in products
                if p["status"] == "Low Stock"
            ]

            answer = (
                "Low-stock products: " +
                (
                    ", ".join(
                        f'{p["name"]} ({p["stock"]} units)'
                        for p in low
                    )
                    if low
                    else "No products are currently below their reorder level."
                )
            )

        elif "order" in message or "sales" in message:

            orders = get_orders()

            total = sum(
                order["amount"] for order in orders
            )

            answer = (
                f"There are {len(orders)} recent orders. "
                f"Total value: ₹{total:,.2f}."
            )

        elif "customer" in message:

            customers = get_customers()

            answer = (
                f"Your customer database contains "
                f"{len(customers)} retrieved customer records."
            )

        elif "product" in message:

            answer = (
                f"Your ProFuel database contains "
                f"{len(products)} products."
            )

        else:

            answer = (
                "Welcome to ProFuel Assistant! "
                "I can help you with inventory, low-stock products, "
                "orders, sales, customers and products."
            )

        return jsonify({"reply": answer})

    except Exception as error:
        app.logger.exception("Chatbot failed")
        return jsonify({
            "reply": "Sorry, I could not retrieve the latest information."
        }), 500


# --------------------------------------------------
# APPLICATION START
# --------------------------------------------------

if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000,
        debug=True
    )
