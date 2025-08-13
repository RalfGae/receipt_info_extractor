
# Receipt Info Extractor

This project provides a tool to extract structured information from images of receipts using Google Drive and OpenAI's LLMs. It automates the process of fetching receipt images from Google Drive, processing them with an LLM, and outputting the extracted data in a structured JSON format.

## Features
- Fetches receipt images from specified Google Drive folders
- Downloads and processes images locally
- Uses OpenAI's API to extract receipt information as JSON (using a Pydantic schema)
- Supports multiple Google Drive folders
- Easy configuration via `.env` file

## Project Structure

```
Google.py                  # Google Drive helper functions
receipt_info_extractor.py  # Main script for extraction workflow
receipt_schema.py          # Pydantic schemas for receipt data
requirements.txt           # Python dependencies
setup.sh                   # Project setup script (virtualenv, dependencies)
service_account_dummy.json # Example Google service account file
creds/                     # Place your real Google service account key here
downloads/                 # Downloaded receipt images
```

## Setup

1. **Clone the repository**
2. **Run the setup script:**
	 ```bash
	 bash setup.sh
	 ```
	 This creates a virtual environment, installs dependencies, and generates a `.env` template if needed.

3. **Configure environment variables:**
	 - Edit the `.env` file with your OpenAI API key and Google Drive settings.
	 - Example:
		 ```ini
		 OPENAI_API_KEY=your-openai-key
		 GOOGLE_DRIVE_APPLICATION_CREDENTIALS_PATH=creds/ServiceKey_GoogleDrive.json
		 GOOGLE_DRIVE_FOLDER_ID=your-folder-id-1,your-folder-id-2
		 ```

4. **Add your Google service account key:**
	 - Place your Google Drive service account JSON in the `creds/` directory.

## Usage

Activate the virtual environment and run the main script:

```bash
source venv/bin/activate
python3 receipt_info_extractor.py
```

The script will:
- List images in the specified Google Drive folders
- Download the first image from each folder
- Send the image to OpenAI's LLM for extraction
- Print the extracted receipt information as JSON

## Configuration

- **Google Drive:**
	- Requires a service account with access to the target folders
	- Folder IDs can be comma-separated for batch processing
- **OpenAI:**
	- Requires an API key with access to the `gpt-4o-mini` model

## Schema

Receipt information is extracted according to the following schema (see `receipt_schema.py`):

```python
class ReceiptItem(BaseModel):
		category: str
		name: str
		price: float

class ReceiptInfo(BaseModel):
		date: date
		store: str
		items: List[ReceiptItem]
```

## Example .env

```ini
OPENAI_API_KEY=your-api-key-here
GOOGLE_DRIVE_APPLICATION_CREDENTIALS_PATH=creds/ServiceKey_GoogleDrive.json
GOOGLE_DRIVE_FOLDER_ID=your-folder-id-1,your-folder-id-2
```

## License

This project is for educational and research purposes. See LICENSE for details.
