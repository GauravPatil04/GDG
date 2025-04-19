# from PIL import Image, ImageEnhance, ImageFilter
# import pytesseract
# import re
# from datetime import datetime

# # Set the path to the Tesseract executable (update this path as needed)
# pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files (x86)\Tesseract-OCR\tesseract.exe'  # Change this path if necessary

# # --- Image Processing Functions ---
# def preprocess_image(image):
#     """Enhance image for better OCR results"""
#     image = image.convert('L')  # Convert to grayscale
#     image = image.filter(ImageFilter.SHARPEN)
#     enhancer = ImageEnhance.Contrast(image)
#     image = enhancer.enhance(2)
#     return image

# def process_image(img_path):
#     """Extract text from image using OCR"""
#     image = preprocess_image(img_path)
#     custom_oem_psm_config = r'--oem 3 --psm 6'
#     text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
#     return text

# # --- Information Extraction ---
# def extract_information(text):
#     """Extract key information from bill text with comprehensive regex patterns"""
#     # --- Amount Extraction (Multiple Patterns) ---
#     amount_patterns = [
#         # Standard patterns with currency symbols
#         r'(?:Total|Subtotal|Grand\s*Total|Amount|Bill\s*Amount|TOTAL\s*\(?[A-Z]{3}\)?|TOTAL\s*DUE|Total\s*Invoice\s*Amount)\s*[:=-]?\s*[₹$£€]?\s*([\d,]+(?:\.\d{2})?)',
#         r'[₹$£€]\s*([\d,]+(?:\.\d{2})?)',
#         r'\b(?:RS?|INR)\s*\.?\s*([\d,]+(?:\.\d{2})?)',
        
#         # Patterns with currency symbols at end
#         r'([\d,]+(?:\.\d{2})?)\s*(?:RS?|INR|USD|EUR|GBP)',
        
#         # Patterns with decimal places
#         r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
        
#         # Patterns for amounts in brackets/parentheses (often indicates totals)
#         r'\(([\d,]+(?:\.\d{2})?)\)',
        
#         # Patterns for amounts after "Total" without explicit label
#         r'(?:Total|TOTAL)\b\D*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        
#         # Patterns for amounts with thousands separators
#         r'\b(\d{1,3}(?:,\d{3})+)',
        
#         # Patterns for amounts with words like "only" at end
#         r'([\d,]+(?:\.\d{2})?)\s*(?:only|/-)',
        
#         # Patterns for amounts in different formats
#         r'\b(\d+\.\d{2})\b',
#         r'\b(\d+)\b(?!\s*%)'  # Basic number but not followed by %
#     ]
    
#     amount = None
#     for pattern in amount_patterns:
#         amount_match = re.search(pattern, text, re.IGNORECASE | re.VERBOSE)
#         if amount_match:
#             try:
#                 amount_str = amount_match.group(1).replace(",", "")
#                 if float(amount_str) > 0:  # Basic validation
#                     amount = float(amount_str)
#                     break
#             except (ValueError, AttributeError):
#                 continue

#     # --- Enhanced Date Extraction (with Walmart-specific patterns) ---
#     date_patterns = [
#         # Walmart-specific patterns (mm/dd/yy with optional time)
#         r'\b(\d{1,2}/\d{1,2}/\d{2})(?:\s+\d{1,2}:\d{2}:\d{2})?\b',
        
#         # Other common receipt date patterns
#         r'(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},?\s+\d{4}',
#         r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
#         r'\d{4}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2}',
#         r'\d{4}[-/]\d{2}[-/]\d{2}',
#         r'\d{2}[-/]\d{2}[-/]\d{4}',
#         r'\d{1,2}[./]\d{1,2}[./]\d{4}',
#         r'\d{1,2}-(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*-\d{4}',
#         r'\d{2}-\w{3}-\d{4}',
#         r'\d{1,2}-(?:JAN|FEB|MAR|APR|MAY|JUN|JUL|AUG|SEP|OCT|NOV|DEC)-\d{2,4}',
#         r'\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}',
#         r'\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}',
#         r'\d{1,2}(?:st|nd|rd|th)\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
#         r'(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)[a-z]*,\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+\d{4}'
#     ]
    
#     date = None
#     for pattern in date_patterns:
#         date_match = re.search(pattern, text, re.IGNORECASE)
#         if date_match:
#             try:
#                 date_str = date_match.group(1) if date_match.groups() else date_match.group()
#                 # Try multiple date formats for parsing, with Walmart format first
#                 for fmt in (
#                     "%m/%d/%y",  # Walmart format (10/18/20)
#                     "%m/%d/%Y",  # Alternative format
#                     "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", 
#                     "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
#                     "%d-%b-%Y", "%d-%B-%Y", "%d-%m-%y", "%d.%m.%Y",
#                     "%Y %b %d", "%dth %b %Y", "%a, %b %d, %Y"
#                 ):
#                     try:
#                         date = datetime.strptime(date_str, fmt).strftime("%Y-%m-%d")
#                         break
#                     except ValueError:
#                         continue
#                 if date:
#                     break
#             except Exception:
#                 continue

#     # --- Category Extraction (Enhanced Patterns) ---
#     category_keywords = {
#         "Shopping": [
#             r'\bwalmart\b', r'\bmall\b', r'\bamazon\b', r'\bflipkart\b', 
#             r'\bpurchase\b', r'\bitem\b', r'\binvoice\b', r'\bstore\b',
#             r'\bshopping\b', r'\bretail\b', r'\boutlet\b', r'\bmarket\b',
#             r'\bpos\b', r'\becommerce\b', r'\bmerchant\b'
#         ],
#         "Medical": [
#             r'\bhospital\b', r'\bclinic\b', r'\bpharmacy\b', 
#             r'\bmedicine\b', r'\bdoctor\b', r'\bhealthcare\b',
#             r'\bmedical\b', r'\bprescription\b', r'\bdiagnostic\b',
#             r'\blab\b', r'\bhealth\s*care\b', r'\bhospitality\b'
#         ],
#         "Entertainment": [
#             r'\bmovie\b', r'\bcinema\b', r'\bnetflix\b', 
#             r'\bconcert\b', r'\btheatre\b', r'\bticket\b',
#             r'\bentertainment\b', r'\bstreaming\b', r'\bgame\b',
#             r'\bgaming\b', r'\bamusement\b', r'\bpark\b'
#         ],
#         "Fuel": [
#             r'\bpetrol\b', r'\bdiesel\b', r'\bfuel\b', 
#             r'\bgas\s*station\b', r'\bhp\b', r'\bindian\s*oil\b',
#             r'\bpetroleum\b', r'\bfilling\s*station\b', r'\bgasoline\b',
#             r'\bcng\b', r'\blpg\b', r'\bfuel\s*price\b'
#         ],
#         "Food": [
#             r'\brestaurant\b', r'\bfood\b', r'\bbill\b', 
#             r'\bdine\b', r'\bmeal\b', r'\bdominos\b', 
#             r'\bzomato\b', r'\bswiggy\b', r'\bcafe\b',
#             r'\bbakery\b', r'\bbistro\b', r'\bfast\s*food\b',
#             r'\bgrocery\b', r'\bsupermarket\b', r'\bkitchen\b'
#         ],
#         "Travel": [
#             r'\bhotel\b', r'\bflight\b', r'\bairlines\b', 
#             r'\btrain\b', r'\birctc\b', r'\bubers?\b', 
#             r'\bola\b', r'\btravel\b', r'\btourism\b',
#             r'\baccomodation\b', r'\bairport\b', r'\btaxi\b',
#             r'\bcab\b', r'\btransport\b', r'\bbus\b'
#         ],
#         "Utilities": [
#             r'\belectricity\b', r'\bwater\b', r'\bbilldesk\b', 
#             r'\bbroadband\b', r'\bwifi\b', r'\binternet\b',
#             r'\butility\b', r'\bphone\b', r'\bmobile\b',
#             r'\bbill\b', r'\bpayment\b', r'\bpostpaid\b',
#             r'\bcable\b', r'\btv\b', r'\btelecom\b'
#         ],
#         "Education": [
#             r'\bschool\b', r'\bcollege\b', r'\buniversity\b',
#             r'\beducation\b', r'\btuition\b', r'\bcourse\b',
#             r'\bexam\b', r'\btextbook\b', r'\blibrary\b',
#             r'\bstudent\b', r'\blearning\b', r'\btraining\b'
#         ]
#     }
    
#     category = "Uncategorized"
#     for cat, patterns in category_keywords.items():
#         for pattern in patterns:
#             if re.search(pattern, text, re.IGNORECASE):
#                 category = cat
#                 break
#         if category != "Uncategorized":
#             break

#     return {
#         "amount": amount,
#         "date": date,
#         "category": category,
#         "raw_text": text
#     }

# # --- Extract Information from Image ---
# def extract_info_from_image(img_path):
#     text = process_image(img_path)
#     return extract_information(text)



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