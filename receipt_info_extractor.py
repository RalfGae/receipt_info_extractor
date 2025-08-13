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

# Example: List 10 files in the specified (shared) Drive folder
def list_files_in_folder(folder_id):
    results = drive_service.files().list(
        q=f"'{folder_id}' in parents",
        pageSize=10,
        fields="nextPageToken, files(id, name)"
    ).execute()
    items = results.get('files', [])
    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(f"{item['name']} ({item['id']})")

# List only image files in a Google Drive folder and return as a list
def list_image_files_in_folder(folder_id, page_size=100):
    """
    Returns a list of image files (jpg, jpeg, png, gif, bmp, webp) in the specified Google Drive folder.
    Each item is a dict with 'id' and 'name'.
    """
    image_mime_types = [
        'image/jpeg', 'image/png', 'image/gif', 'image/bmp', 'image/webp'
    ]
    mime_query = ' or '.join([f"mimeType='{mime}'" for mime in image_mime_types])
    query = f"('{folder_id}' in parents) and ({mime_query}) and trashed = false"
    results = drive_service.files().list(
        q=query,
        pageSize=page_size,
        fields="nextPageToken, files(id, name, mimeType)"
    ).execute()
    items = results.get('files', [])
    return items

# Download a file from Google Drive given its metadata (expects dict with 'id' and 'name')
def download_drive_file(file_metadata, destination_folder="downloads"):
    """
    Downloads a file from Google Drive using its file metadata dict (with 'id' and 'name').
    Saves the file to the specified destination folder (default: 'downloads').
    Returns the local file path.
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

# Process folder IDs
def process_folder_ids(folder_id_input):
    if not folder_id_input:
        print("No GOOGLE_DRIVE_FOLDER_ID found in environment variables.")
        return
    
    print(f"Raw folder ID input: '{folder_id_input}'")
    
    # Check if it's a comma-separated list
    if ',' in folder_id_input:
        folder_ids = [fid.strip() for fid in folder_id_input.split(',')]
        print(f"Processing {len(folder_ids)} folder IDs: {folder_ids}")
        for folder_id in folder_ids:
            try:
                list_files_in_folder(folder_id)
            except Exception as e:
                print(f"Error processing folder ID '{folder_id}': {e}")
    else:
        # Single folder ID
        try:
            list_files_in_folder(folder_id_input.strip())
        except Exception as e:
            print(f"Error processing folder ID '{folder_id_input}': {e}")


def feed_image_to_llm_local(image_path, client):
    def encode_image(image_path):
        with open(image_path, 'rb') as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    base64_image = encode_image(image_path)

    input_messages=[
        {
            "role":"user",
            "content": [
                {
                    "type": "input_text",
                    "text": "Describe the image and extract the receipt information as JSON according to the provided schema."
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

    print(response.output_text)
    # Print token usage if available
    if hasattr(response, "usage"):
        print("Token usage:", response.usage)

def chat_loop():
    current_response_id = None

    while True:
        # Get user input
        user_input = input("You: ")

        if user_input.lower() in ["exit", "bye", "quit"]:
            print("Goodbye!")
            break

        response = client.responses.create(
            model="gpt-4o-mini",
            input=user_input,
            previous_response_id=current_response_id
        )

        current_response_id = response.id

        # Print the response
        print("Bot: ", response.output_text)

def process_images_from_folder(images, folder_id=None):
    """
    Helper to process the first image from a list of images, optionally with folder context.
    Always downloads the image and uses the local file for LLM processing.
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

# Run the function if folder_id is set
if __name__ == "__main__":
    # Test workflow: list images, download the first, and feed it to the LLM
    if not folder_id_input:
        print("No folder ID provided.")
    else:
        if ',' in folder_id_input:
            folder_ids = [fid.strip() for fid in folder_id_input.split(',')]
            for folder_id in folder_ids:
                images = list_image_files_in_folder(folder_id)
                process_images_from_folder(images, folder_id)
        else:
            images = list_image_files_in_folder(folder_id_input)
            process_images_from_folder(images, folder_id_input)