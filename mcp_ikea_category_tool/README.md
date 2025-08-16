# MCP IKEA Category Tool

A minimal FastAPI service that exposes an endpoint to look up IKEA product categories by item name using fuzzy matching against the IKEA product CSV.

## Usage

1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Start the server:
   ```bash
   uvicorn app:app --reload
   ```
3. Query the API:
   - Example: `http://localhost:8000/lookup?item_name=JUSTINA`

## Endpoints
- `/lookup?item_name=...` : Returns the best-matched IKEA product and its category.
- `/` : Welcome message.

## Notes
- The tool loads the product sheet from `../products/ikea_products.csv`.
- Adjust the fuzzy match threshold with the `threshold` query parameter if needed.
