import requests
import pandas as pd
from fuzzywuzzy import process
# --- IKEA Product Sheet Integration ---
def load_ikea_products(csv_path='products/ikea_products.csv'):
    """
    Loads IKEA product data from a CSV and returns a lookup dict and list of product names.
    Assumes columns: 'name', 'category'.
    """
    try:
        df = pd.read_csv(csv_path)
        product_dict = {str(row['name']).strip().lower(): str(row['category']).strip() for _, row in df.iterrows()}
        return product_dict, list(product_dict.keys())
    except Exception as e:
        print(f"[WARN] Could not load IKEA product sheet: {e}")
        return {{}}, []

def get_ikea_category(item_name, product_dict, product_names, threshold=95):
    """
    Fuzzy-matches item_name to IKEA product names and returns the category if found.
    """
    if not item_name:
        return None
    match = process.extractOne(item_name.lower(), product_names)
    if match and match[1] >= threshold:
        matched_name = match[0]
        matched_score = match[1]
        matched_category = product_dict[matched_name]
        print(f"[DEBUG] IKEA match: input='{item_name}' matched='{matched_name}' (score={matched_score}), category='{matched_category}'")
        return matched_category
    print(f"[DEBUG] IKEA match: input='{item_name}' no good match found (best score={match[1] if match else 'N/A'})")
    return None
import sys
from datetime import datetime
import argparse

# --- Debug Output Logging Setup ---
def setup_debug_logging():
    """
    [DEBUG] Redirects stdout and stderr to both terminal and a timestamped log file.
    Returns the log file object and the log file path.
    Only used if debug mode is enabled.
    """
    now = datetime.now()
    log_dir = os.path.join(os.path.dirname(__file__), 'output')
    os.makedirs(log_dir, exist_ok=True)
    log_filename = f"output_{now.strftime('%Y%m%d_%H_%M_%S')}.txt"
    log_path = os.path.join(log_dir, log_filename)
    class Tee:
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush()
        def flush(self):
            for f in self.files:
                f.flush()
    log_file = open(log_path, 'w', encoding='utf-8')
    sys.stdout = Tee(sys.__stdout__, log_file)
    sys.stderr = Tee(sys.__stderr__, log_file)
    return log_file, log_path
from PIL import Image, ImageEnhance
import pytesseract
import re
import os
from dotenv import load_dotenv
from google.oauth2 import service_account
from googleapiclient.discovery import build
from openai import OpenAI
import base64
from receipt_schema import receiptInfo_schema  # Assuming this is the correct import path

load_dotenv()

client = OpenAI()

# Path to your service account JSON file and required scopes
SERVICE_ACCOUNT_FILE = os.getenv("GOOGLE_DRIVE_APPLICATION_CREDENTIALS_PATH", 'service_account_dummy.json')
SCOPES = ['https://www.googleapis.com/auth/drive']

# Folder ID can be provided as an environment variable or directly in the code
folder_id_input = os.getenv("GOOGLE_DRIVE_FOLDER_ID")  # or: folder_id = 'your_folder_id'

# Load credentials from service account file
credentials = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES)

# Build the Google Drive API service object
drive_service = build('drive', 'v3', credentials=credentials)

def feed_image_to_llm_local(image_path, client):
    # Load IKEA product data once (could be moved to global scope for efficiency)
    ikea_product_dict, ikea_product_names = load_ikea_products()

    def mcp_lookup_ikea_category(item_name, threshold=95):
        """
        Try the full item name and all substrings (split by space and hyphen) for MCP lookup.
        Return the best category found (highest score above threshold).
        """
        url = "http://localhost:8000/lookup"
        candidates = set()
        if not item_name:
            return None
        # Add full name, then all space- and hyphen-separated substrings
        candidates.add(item_name.strip())
        for part in item_name.replace('-', ' ').split():
            if part.strip():
                candidates.add(part.strip())
        best = {"score": -1, "category": None, "matched_name": None, "input": None}
        for candidate in candidates:
            params = {"item_name": candidate, "threshold": threshold}
            try:
                resp = requests.get(url, params=params, timeout=2)
                if resp.status_code == 200:
                    data = resp.json()
                    if data.get("found") and data.get("score", 0) > best["score"]:
                        best = {"score": data["score"], "category": data["category"], "matched_name": data["matched_name"], "input": candidate}
            except Exception as e:
                print(f"[WARN] MCP lookup failed for '{candidate}': {e}")
        if best["category"]:
            print(f"[DEBUG] MCP best match: input='{item_name}' tried='{best['input']}' matched='{best['matched_name']}', category='{best['category']}', score={best['score']}")
            return best["category"]
        print(f"[DEBUG] MCP no good match for '{item_name}' (tried substrings: {candidates})")
        return None
    """
    Encodes a local image and sends it to the OpenAI LLM for receipt information extraction.
    Prints the extracted JSON and token usage if available.
    Args:
        image_path (str): Path to the image file.
        client (OpenAI): OpenAI client instance.
    """
    # Step 1: Enhance image contrast
    def enhance_contrast(image_path, factor=2.0):
        img = Image.open(image_path)
        enhancer = ImageEnhance.Contrast(img)
        enhanced_img = enhancer.enhance(factor)
        enhanced_path = image_path + ".enhanced.jpg"
        enhanced_img.save(enhanced_path)
        return enhanced_path

    # Step 2: OCR extraction
    def extract_text_with_ocr(image_path):
        return pytesseract.image_to_string(Image.open(image_path))

    # Step 3: Improved prompt for LLM
    improved_prompt = (
        "Extract the purchase date, store name, and all items from this receipt image. "
        "The date may appear in formats like DD.MM.YYYY, MM/DD/YYYY, or YYYY-MM-DD. "
        "If multiple dates are present, choose the one most likely to be the purchase date. "
        "Return the result as JSON according to the provided schema. "
        "If the date is missing or ambiguous, return null for the date field. "
        "Always use singular English nouns for categories (e.g., 'Fruit', 'Snack', 'Bag'). "
        "Normalize the store name to its most common, simple form (e.g., 'IKEA', 'REWE', 'ESSO'). "
        "Assign the most specific category possible; use 'General' only if no other category fits. "
        "If the store is known for a specific product type, prefer relevant categories (e.g., 'Furniture' for IKEA, 'Food' for REWE)."
    )

    # Step 4: Enhance image and extract OCR text
    enhanced_path = enhance_contrast(image_path)
    ocr_text = extract_text_with_ocr(enhanced_path)

    def encode_image(image_path):
        """Reads and base64-encodes the image file."""
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    base64_image = encode_image(enhanced_path)

    input_messages=[
        {
            "role":"user",
            "content": [
                {
                    "type": "input_text",
                    "text": improved_prompt + "\n\nHere is the OCR text for reference:\n" + ocr_text
                },
                {
                    "type": "input_image",
                    "image_url": f"data:image/jpeg;base64,{base64_image}"
                }
            ]
        }
    ]

    response = client.responses.create(
        model="gpt-4o-mini",
        input=input_messages,
        text={
        "format": {
            "type": "json_schema",
            "name": "ReceiptInfo",
            "schema": receiptInfo_schema, 
            "strict": True
            }
        }
    )

    # Step 5: Post-process the date field in the output
    import json
    try:
        result = json.loads(response.output_text)
        # --- Post-process date ---
        date_str = result.get("date")
        if not date_str or not is_valid_date(date_str):
            # Try to extract date from OCR text
            extracted_date = extract_date_from_text(ocr_text)
            if extracted_date:
                result["date"] = extracted_date
            else:
                result["date"] = None

        # --- Post-process store name normalization ---
        store_map = {
            "ikea": "IKEA",
            "ikea deutschland gmbh & co. kg": "IKEA",
            "ikea deutschland gmbh&co kg/nl furth": "IKEA",
            "rewe": "REWE",
            "esso tankstelle": "ESSO",
            # Add more mappings as needed
        }
        store = result.get("store", "")
        store_key = store.lower().replace(",", "").replace("  ", " ").strip()
        for k, v in store_map.items():
            if k in store_key:
                result["store"] = v
                break

        # --- Post-process categories: singularize and map known categories ---
        def singularize(word):
            if word.lower().endswith('ies'):
                return word[:-3] + 'y'
            elif word.lower().endswith('s') and not word.lower().endswith('ss'):
                return word[:-1]
            return word

        category_map = {
            "fruits": "Fruit",
            "fruit": "Fruit",
            "vegetables": "Vegetable",
            "snacks": "Snack",
            "food": "Food",
            "furniture": "Furniture",
            "plant": "Plant",
            "bag": "Bag",
            # Add more as needed
        }
        for item in result.get("items", []):
            cat = item.get("category", "")
            cat_key = cat.lower().strip()
            # If store is IKEA, try MCP tool first, then fallback to local product sheet
            if result.get("store", "").upper() == "IKEA":
                mcp_cat = mcp_lookup_ikea_category(item.get("name", ""))
                if mcp_cat:
                    item["category"] = mcp_cat
                    continue
                # fallback to local fuzzy match if MCP fails
                ikea_cat = get_ikea_category(item.get("name", ""), ikea_product_dict, ikea_product_names)
                if ikea_cat:
                    item["category"] = ikea_cat
                    continue
            if cat_key in category_map:
                item["category"] = category_map[cat_key]
            else:
                item["category"] = singularize(cat)
            # Optionally, assign 'General' if category is empty or unknown
            if not item["category"]:
                item["category"] = "General"

        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(response.output_text)
        print(f"[Warning] Could not post-process date/store/category: {e}")

    # Print token usage if available
    if hasattr(response, "usage"):
        print("Token usage:", response.usage)

# ---
# Helper: Extract date from text using regex
def extract_date_from_text(text):
    """
    Extracts a date string from text using regex for common date formats.
    Returns the first valid date found, or None.
    """
    date_patterns = [
        r"\b\d{2}[./-]\d{2}[./-]\d{4}\b",   # DD.MM.YYYY or DD-MM-YYYY or DD/MM/YYYY
        r"\b\d{4}[./-]\d{2}[./-]\d{2}\b",   # YYYY-MM-DD or YYYY/MM/DD
        r"\b\d{2}[./-]\d{2}[./-]\d{2}\b",   # DD.MM.YY
    ]
    for pattern in date_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(0)
    return None

# ---
# Helper: Validate date string
def is_valid_date(date_str):
    """
    Checks if a date string is in a valid format and not in the future.
    """
    from datetime import datetime, date
    try:
        # Try parsing with common formats
        for fmt in ("%d.%m.%Y", "%d-%m-%Y", "%d/%m/%Y", "%Y-%m-%d", "%Y/%m/%d", "%d.%m.%y", "%d-%m-%y", "%d/%m/%y"):
            try:
                dt = datetime.strptime(date_str, fmt)
                if dt.date() <= date.today():
                    return True
            except Exception:
                continue
        return False
    except Exception:
        return False

# Download a file from Google Drive given its metadata (expects dict with 'id' and 'name')
def download_drive_file(file_metadata, destination_folder="downloads"):
    """
    Downloads a file from Google Drive using its file metadata dict (with 'id' and 'name').
    Saves the file to the specified destination folder (default: 'downloads').
    Returns the local file path.
    Args:
        file_metadata (dict): Metadata dict with 'id' and 'name'.
        destination_folder (str): Local folder to save the file.
    Returns:
        str: Local file path of the downloaded file.
    """
    if not os.path.exists(destination_folder):
        os.makedirs(destination_folder)
    file_id = file_metadata['id']
    file_name = file_metadata['name']
    request = drive_service.files().get_media(fileId=file_id)
    local_path = os.path.join(destination_folder, file_name)
    from googleapiclient.http import MediaIoBaseDownload
    import io
    fh = io.FileIO(local_path, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    fh.close()
    return local_path

def process_images_from_folder(images, folder_id=None):
    """
    Processes the first image from a list of images, optionally with folder context.
    Downloads the image and sends it to the LLM for extraction.
    Args:
        images (list): List of image metadata dicts.
        folder_id (str, optional): Folder context for logging.
    """
    if not images:
        if folder_id:
            print(f"No images found in folder {folder_id}.")
        else:
            print("No images found in the folder.")
        return
    first_image = images[0]
    print(f"Downloading: {first_image['name']}")
    local_path = download_drive_file(first_image)
    print(f"Saved to: {local_path}")
    print("Sending image to LLM...")
    feed_image_to_llm_local(local_path, client)

# Breadth-first search: collect all image files in all folders and subfolders.
# Returns a list of image file dicts and a list of all visited folder IDs.
from collections import deque
def bfs_collect_images_and_folders(root_folder_ids):
    """
    Performs a breadth-first search to collect all image files in all folders and subfolders.
    Returns a list of image file dicts and a set of all visited folder IDs.
    Args:
        root_folder_ids (list): List of root folder IDs to start traversal from.
    Returns:
        tuple: (all_images, visited_folders)
            all_images (list): List of image file metadata dicts.
            visited_folders (set): Set of all visited folder IDs.
    """
    queue = deque(root_folder_ids)
    all_images = []
    visited_folders = set()
    while queue:
        folder_id = queue.popleft()
        if folder_id in visited_folders:
            continue
        visited_folders.add(folder_id)
        print(f"Processing folder: {folder_id}")
        # Query for both files and subfolders in one call
        query = f"'{folder_id}' in parents and trashed = false"
        try:
            results = drive_service.files().list(
                q=query,
                fields="nextPageToken, files(id, name, mimeType)",
                pageSize=1000
            ).execute()
            files = results.get('files', [])
            for f in files:
                if f.get('mimeType') == 'application/vnd.google-apps.folder':
                    queue.append(f['id'])
                    print(f"  Found subfolder: {f['name']} ({f['id']})")
                elif f.get('mimeType') in [
                    'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp']:
                    all_images.append(f)
                    print(f"  Found image: {f['name']} ({f['id']})")
        except Exception as e:
            print(f"  Error listing items in folder '{folder_id}': {e}")
    return all_images, visited_folders

# Process folder IDs
def process_folder_ids(folder_id_input):
    """
    Entry point for processing all images in the specified Google Drive folder(s).
    Traverses all folders and subfolders, collects images, and processes them.
    Args:
        folder_id_input (str): Comma-separated string of root folder IDs or a single folder ID.
    """
    if not folder_id_input:
        print("No GOOGLE_DRIVE_FOLDER_ID found in environment variables.")
        return

    print(f"Raw folder ID input: '{folder_id_input}'")

    # Prepare root folder IDs
    if ',' in folder_id_input:
        root_folder_ids = [fid.strip() for fid in folder_id_input.split(',')]
        print(f"Processing {len(root_folder_ids)} folder IDs: {root_folder_ids}")
    else:
        root_folder_ids = [folder_id_input.strip()]

    all_images, all_folders = bfs_collect_images_and_folders(root_folder_ids)
    print(f"\nTotal images found: {len(all_images)}")
    for img in all_images:
        process_images_from_folder([img], img.get('parents', [None])[0])

# Run the function if folder_id is set
if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Receipt Info Extractor")
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug logging to file')
    args = parser.parse_args()

    log_file = None
    if args.debug:
        # [DEBUG] Enable debug logging to file
        log_file, log_path = setup_debug_logging()
        print(f"[DEBUG] Output will be logged to: {log_path}")

    start_time = datetime.now()
    try:
        if not folder_id_input:
            print("No folder ID provided.")
        else:
            process_folder_ids(folder_id_input)
    finally:
        end_time = datetime.now()
        elapsed = end_time - start_time
        print(f"[INFO] Execution finished at {end_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"[INFO] Total execution time: {elapsed}")
        if log_file:
            log_file.close()