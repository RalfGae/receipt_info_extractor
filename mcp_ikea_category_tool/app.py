from fastapi import FastAPI, Query
from pydantic import BaseModel
import pandas as pd
from fuzzywuzzy import process
from typing import Optional

app = FastAPI()

# Load IKEA product data at startup
df = pd.read_csv('../products/ikea_products.csv')
product_dict = {str(row['name']).strip().lower(): str(row['category']).strip() for _, row in df.iterrows()}
product_names = list(product_dict.keys())

class CategoryResponse(BaseModel):
    item_name: str
    matched_name: Optional[str]
    category: Optional[str]
    score: Optional[int]
    found: bool

@app.get("/lookup", response_model=CategoryResponse)
def lookup_category(item_name: str = Query(..., description="Item name to look up"), threshold: int = 85):
    if not item_name:
        return CategoryResponse(item_name=item_name, matched_name=None, category=None, score=None, found=False)
    match = process.extractOne(item_name.lower(), product_names)
    if match and match[1] >= threshold:
        matched_name = match[0]
        category = product_dict[matched_name]
        return CategoryResponse(item_name=item_name, matched_name=matched_name, category=category, score=match[1], found=True)
    return CategoryResponse(item_name=item_name, matched_name=match[0] if match else None, category=None, score=match[1] if match else None, found=False)

@app.get("/")
def root():
    return {"message": "IKEA Category MCP Tool. Use /lookup?item_name=..."}
