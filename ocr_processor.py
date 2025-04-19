# import pytesseract
# from PIL import Image, ImageEnhance, ImageFilter
# import io
# import re
# from pdf2image import convert_from_bytes
# import logging
# from datetime import datetime

# # Configure logging
# logging.basicConfig(level=logging.INFO)
# logger = logging.getLogger(__name__)

# # Configure Tesseract path (change if needed)
# pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

# def preprocess_image(image):
#     """Enhance image for better OCR results"""
#     try:
#         image = image.convert('L')  # Grayscale
#         image = image.filter(ImageFilter.SHARPEN)  # Sharpen
#         enhancer = ImageEnhance.Contrast(image)
#         return enhancer.enhance(2)  # Increase contrast
#     except Exception as e:
#         logger.error(f"Image preprocessing failed: {e}")
#         raise

# def process_image(image):
#     """Perform OCR on image"""
#     try:
#         processed_image = preprocess_image(image)
#         custom_config = r'--oem 3 --psm 6'
#         return pytesseract.image_to_string(processed_image, config=custom_config)
#     except Exception as e:
#         logger.error(f"Image processing failed: {e}")
#         raise

# def process_pdf(pdf_bytes):
#     """Convert PDF to images and process each page"""
#     try:
#         images = convert_from_bytes(pdf_bytes)
#         return " ".join(process_image(img) for img in images)
#     except Exception as e:
#         logger.error(f"PDF processing failed: {e}")
#         raise

# def extract_expense_data(text):
#     """Extract structured data from OCR text"""
#     try:
#         # Amount extraction
#         amount = None
#         amount_patterns = [
#             r'(?:Total|Amount|TOTAL)[:\s]*[\₹\$\£]?\s*(\d+[\.,]\d{2})',
#             r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2}))\b'
#         ]
        
#         for pattern in amount_patterns:
#             match = re.search(pattern, text, re.IGNORECASE)
#             if match:
#                 try:
#                     amount_str = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
#                     amount_str = amount_str.replace(',', '')
#                     amount = float(amount_str)
#                     break
#                 except (ValueError, AttributeError, IndexError) as e:
#                     logger.warning(f"Amount extraction issue: {e}")
#                     continue

#         # Date extraction (multiple formats)
#         date = None
#         date_patterns = [
#             r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
#             r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
#             r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
#             r'\d{1,2}-\w{3}-\d{4}'
#         ]
        
#         for pattern in date_patterns:
#             match = re.search(pattern, text)
#             if match:
#                 date = match.group(0)
#                 break

#         # Category detection
#         category = "Other"
#         category_keywords = {
#             "Food": ["restaurant", "cafe", "food", "dining", "meal"],
#             "Transport": ["fuel", "petrol", "diesel", "uber", "taxi"],
#             "Shopping": ["amazon", "flipkart", "store", "purchase"],
#             "Bills": ["electricity", "water", "internet", "bill"],
#             "Entertainment": ["movie", "netflix", "concert", "game"]
#         }
        
#         text_lower = text.lower()
#         for cat, keywords in category_keywords.items():
#             if any(keyword in text_lower for keyword in keywords):
#                 category = cat
#                 break

#         return {
#             "amount": amount,
#             "date": date,
#             "category": category,
#             "raw_text": text[:500]  # Trimmed text for debug
#         }

#     except Exception as e:
#         logger.error(f"Data extraction failed: {e}")
#         raise

# async def process_bill_file(content: bytes, content_type: str):
#     """Main processing function"""
#     try:
#         if content_type.startswith('image/'):
#             logger.info("Processing image file")
#             image = Image.open(io.BytesIO(content))
#             text = process_image(image)
#         elif content_type == 'application/pdf':
#             logger.info("Processing PDF file")
#             text = process_pdf(content)
#         else:
#             raise ValueError(f"Unsupported file type: {content_type}")

#         return extract_expense_data(text)
#     except Exception as e:
#         logger.error(f"Bill processing failed: {e}")
#         raise



from PIL import Image, ImageEnhance, ImageFilter
import pytesseract
import re
from datetime import datetime
from pathlib import Path

# Set the path to the Tesseract executable (update this path as needed)
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'  # Change this path if necessary

# --- Image Processing Functions ---
def preprocess_image(image_path):
    """Enhance image for better OCR results"""
    try:
        # Open the image from the path (works with both string paths and Path objects)
        if isinstance(image_path, (str, Path)):
            image = Image.open(str(image_path))
        else:
            # Handle case where image_path might be a file-like object
            image = Image.open(image_path)
            
        image = image.convert('L')  # Convert to grayscale
        image = image.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2)
        return image
    except Exception as e:
        raise ValueError(f"Failed to preprocess image: {str(e)}")

def process_image(img_path):
    """Extract text from image using OCR"""
    try:
        image = preprocess_image(img_path)
        custom_oem_psm_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
        return text
    except Exception as e:
        raise ValueError(f"OCR processing failed: {str(e)}")

# --- Information Extraction ---
def extract_information(text):
    """Extract key information from bill text with comprehensive regex patterns"""
    try:
        # --- Amount Extraction (Multiple Patterns) ---
        amount_patterns = [
            r'(?:Total|Subtotal|Grand\s*Total|Amount|Bill\s*Amount|TOTAL\s*\(?[A-Z]{3}\)?|TOTAL\s*DUE|Total\s*Invoice\s*Amount)\s*[:=-]?\s*[₹$£€]?\s*([\d,]+(?:\.\d{2})?)',
            r'[₹$£€]\s*([\d,]+(?:\.\d{2})?)',
            r'\b(?:RS?|INR)\s*\.?\s*([\d,]+(?:\.\d{2})?)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:RS?|INR|USD|EUR|GBP)',
            r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
            r'\(([\d,]+(?:\.\d{2})?)\)',
            r'(?:Total|TOTAL)\b\D*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
            r'\b(\d{1,3}(?:,\d{3})+)',
            r'([\d,]+(?:\.\d{2})?)\s*(?:only|/-)',
            r'\b(\d+\.\d{2})\b',
            r'\b(\d+)\b(?!\s*%)'
        ]
        
        amount = None
        for pattern in amount_patterns:
            amount_match = re.search(pattern, text, re.IGNORECASE | re.VERBOSE)
            if amount_match:
                try:
                    amount_str = amount_match.group(1).replace(",", "")
                    if float(amount_str) > 0:  # Basic validation
                        amount = float(amount_str)
                        break
                except (ValueError, AttributeError):
                    continue

        # --- Enhanced Date Extraction ---
        date_patterns = [
            r'\b(\d{1,2}/\d{1,2}/\d{2})(?:\s+\d{1,2}:\d{2}:\d{2})?\b',
            r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}',
            r'\d{4}[-/]\d{2}[-/]\d{2}',
            r'\d{2}[-/]\d{2}[-/]\d{4}',
            r'\d{1,2}[./]\d{1,2}[./]\d{4}',
            r'\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{4}',
            r'\d{2}-\w{3}-\d{4}',
            r'\d{1,2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2,4}',
            r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
            r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
            r'\d{1,2}(?:st|nd|rd|th)\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}'
        ]
        
        date = None
        for pattern in date_patterns:
            date_match = re.search(pattern, text, re.IGNORECASE)
            if date_match:
                try:
                    date_str = date_match.group(1) if date_match.groups() else date_match.group()
                    for fmt in (
                        "%m/%d/%y", "%m/%d/%Y", "%B %d, %Y", "%b %d, %Y", 
                        "%d %B %Y", "%d %b %Y", "%Y-%m-%d", "%d-%m-%Y", 
                        "%d/%m/%Y", "%m/%d/%Y", "%d-%b-%Y", "%d-%B-%Y", 
                        "%d-%m-%y", "%d.%m.%Y", "%Y %b %d", "%dth %b %Y", 
                        "%a, %b %d, %Y"
                    ):
                        try:
                            date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
                            break
                        except ValueError:
                            continue
                    if date:
                        break
                except Exception:
                    continue

        # --- Category Extraction ---
        category_keywords = {
            "Shopping": [r'\bwalmart\b', r'\bmall\b', r'\bamazon\b'],
            "Medical": [r'\bhospital\b', r'\bclinic\b', r'\bpharmacy\b'],
            "Entertainment": [r'\bmovie\b', r'\bcinema\b', r'\bnetflix\b'],
            "Fuel": [r'\bpetrol\b', r'\bdiesel\b', r'\bfuel\b'],
            "Food": [r'\brestaurant\b', r'\bfood\b', r'\bbill\b'],
            "Travel": [r'\bhotel\b', r'\bflight\b', r'\bairlines\b'],
            "Utilities": [r'\belectricity\b', r'\bwater\b', r'\bbilldesk\b'],
            "Education": [r'\bschool\b', r'\bcollege\b', r'\buniversity\b']
        }
        
        category = "Uncategorized"
        for cat, patterns in category_keywords.items():
            for pattern in patterns:
                if re.search(pattern, text, re.IGNORECASE):
                    category = cat
                    break
            if category != "Uncategorized":
                break

        return {
            "amount": amount,
            "date": date,
            "category": category,
            "raw_text": text
        }
    except Exception as e:
        return {
            "error": f"Information extraction failed: {str(e)}",
            "raw_text": text
        }

# --- Extract Information from Image ---
def extract_info_from_image(img_path):
    """Main function to process image and extract information"""
    try:
        text = process_image(img_path)
        if not text.strip():
            return {"error": "No text could be extracted from the image", "raw_text": ""}
        return extract_information(text)
    except Exception as e:
        return {"error": f"Failed to process image: {str(e)}", "raw_text": ""}
