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