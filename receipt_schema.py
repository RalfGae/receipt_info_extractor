# ---
# SCHEMA EVALUATION ---
#
# This schema uses Pydantic and enforces:
#   - date: date (parsed by Pydantic, will error if not a valid date)
#   - store: str
#   - items: List[ReceiptItem] (with category, name, price)
#
# This is a robust approach. However, if the LLM or OCR extraction returns a date in an unexpected format,
# Pydantic will raise a validation error. The post-processing in receipt_info_extractor.py helps mitigate this by attempting to
# extract and validate a date from OCR text if the LLM output is missing or malformed.
#
# If you want to be even more robust, you could:
#   - Accept date as str in the schema, and post-validate/convert it in your code.
#   - Add custom Pydantic validators for more flexible date parsing.
#
# As it stands, this schema is strict and safe, but may reject some edge cases. The new post-processing
# should help fill in most gaps.
from pydantic import BaseModel, ConfigDict
from typing import List
from datetime import date

# Create the Pydantic class for the receipt item
class ReceiptItem(BaseModel):
    model_config = ConfigDict(extra='forbid')

    category: str
    name: str
    price: float

receiptItem_schema = ReceiptItem.model_json_schema()

# Create the Pydantic class for the receipt information
class ReceiptInfo(BaseModel):
    model_config = ConfigDict(extra='forbid')

    date: date
    store: str
    items: List[ReceiptItem]

receiptInfo_schema = ReceiptInfo.model_json_schema()