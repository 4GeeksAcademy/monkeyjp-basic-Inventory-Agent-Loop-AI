import csv
from pathlib import Path

from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field

app = FastAPI(
    title="Inventory API",
    description="API for managing inventory products",
    version="1.0.0",
)

CSV_FILE = Path("products.csv")


class ProductCreate(BaseModel):
    name: str
    quantity: float = Field(ge=0)
    unit: str
    low_stock_threshold: float = Field(ge=0)

class InventoryUpdate(BaseModel):
    quantity_change: float


def read_inventory():
    products = []

    if not CSV_FILE.exists():
        return products

    with CSV_FILE.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            products.append(
                {
                    "id": int(row["id"]),
                    "name": row["name"],
                    "quantity": float(row["quantity"]),
                    "unit": row["unit"],
                    "low_stock_threshold": float(row["low_stock_threshold"]),
                }
            )

    return products


def write_inventory(products):
    with CSV_FILE.open("w", encoding="utf-8", newline="") as file:
        fieldnames = [
            "id",
            "name",
            "quantity",
            "unit",
            "low_stock_threshold",
        ]

        writer = csv.DictWriter(file, fieldnames=fieldnames)

        writer.writeheader()
        writer.writerows(products)


@app.get("/")
def root():
    return {"message": "Inventory API is running"}


@app.get("/inventory")
def get_inventory():
    return read_inventory()


@app.post("/inventory", status_code=201)
def create_product(product: ProductCreate):
    products = read_inventory()

    existing_product = next(
        (
            item
            for item in products
            if item["name"].lower() == product.name.lower()
        ),
        None,
    )

    if existing_product:
        raise HTTPException(
            status_code=400,
            detail="A product with this name already exists",
        )

    new_id = max(
        (item["id"] for item in products),
        default=0,
    ) + 1

    new_product = {
        "id": new_id,
        "name": product.name,
        "quantity": product.quantity,
        "unit": product.unit,
        "low_stock_threshold": product.low_stock_threshold,
    }

    products.append(new_product)
    write_inventory(products)

    return new_product

@app.patch("/inventory/{product_id}")
def update_inventory(product_id: int, update: InventoryUpdate):
    products = read_inventory()

    product = next(
        (
            item
            for item in products
            if item["id"] == product_id
        ),
        None,
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found",
        )

    new_quantity = product["quantity"] + update.quantity_change

    if new_quantity < 0:
        raise HTTPException(
            status_code=400,
            detail="Stock cannot be negative",
        )

    product["quantity"] = new_quantity

    write_inventory(products)

    return product

@app.get("/inventory/alerts")
def get_low_stock_alerts():
    products = read_inventory()

    low_stock_products = [
        product
        for product in products
        if product["quantity"] <= product["low_stock_threshold"]
    ]

    return low_stock_products