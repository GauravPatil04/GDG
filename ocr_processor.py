import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
from pdf2image import convert_from_bytes
import logging
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Tesseract path (change if needed)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe"

def preprocess_image(image):
    """Enhance image for better OCR results"""
    try:
        image = image.convert('L')  # Grayscale
        image = image.filter(ImageFilter.SHARPEN)  # Sharpen
        enhancer = ImageEnhance.Contrast(image)
        return enhancer.enhance(2)  # Increase contrast
    except Exception as e:
        logger.error(f"Image preprocessing failed: {e}")
        raise

def process_image(image):
    """Perform OCR on image"""
    try:
        processed_image = preprocess_image(image)
        custom_config = r'--oem 3 --psm 6'
        return pytesseract.image_to_string(processed_image, config=custom_config)
    except Exception as e:
        logger.error(f"Image processing failed: {e}")
        raise

def process_pdf(pdf_bytes):
    """Convert PDF to images and process each page"""
    try:
        images = convert_from_bytes(pdf_bytes)
        return " ".join(process_image(img) for img in images)
    except Exception as e:
        logger.error(f"PDF processing failed: {e}")
        raise

def extract_expense_data(text):
    """Extract structured data from OCR text"""
    try:
        # Amount extraction
        amount = None
        amount_patterns = [
            r'(?:Total|Amount|TOTAL)[:\s]*[\₹\$\£]?\s*(\d+[\.,]\d{2})',
            r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2}))\b'
        ]
        
        for pattern in amount_patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                try:
                    amount_str = match.group(1) if match.lastindex and match.lastindex >= 1 else match.group(0)
                    amount_str = amount_str.replace(',', '')
                    amount = float(amount_str)
                    break
                except (ValueError, AttributeError, IndexError) as e:
                    logger.warning(f"Amount extraction issue: {e}")
                    continue

        # Date extraction (multiple formats)
        date = None
        date_patterns = [
            r'\d{2}/\d{2}/\d{4}',  # DD/MM/YYYY
            r'\d{4}-\d{2}-\d{2}',  # YYYY-MM-DD
            r'\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}',
            r'\d{1,2}-\w{3}-\d{4}'
        ]
        
        for pattern in date_patterns:
            match = re.search(pattern, text)
            if match:
                date = match.group(0)
                break

        # Category detection
        category = "Other"
        category_keywords = {
            "Food": ["restaurant", "cafe", "food", "dining", "meal"],
            "Transport": ["fuel", "petrol", "diesel", "uber", "taxi"],
            "Shopping": ["amazon", "flipkart", "store", "purchase"],
            "Bills": ["electricity", "water", "internet", "bill"],
            "Entertainment": ["movie", "netflix", "concert", "game"]
        }
        
        text_lower = text.lower()
        for cat, keywords in category_keywords.items():
            if any(keyword in text_lower for keyword in keywords):
                category = cat
                break

        return {
            "amount": amount,
            "date": date,
            "category": category,
            "raw_text": text[:500]  # Trimmed text for debug
        }

    except Exception as e:
        logger.error(f"Data extraction failed: {e}")
        raise

async def process_bill_file(content: bytes, content_type: str):
    """Main processing function"""
    try:
        if content_type.startswith('image/'):
            logger.info("Processing image file")
            image = Image.open(io.BytesIO(content))
            text = process_image(image)
        elif content_type == 'application/pdf':
            logger.info("Processing PDF file")
            text = process_pdf(content)
        else:
            raise ValueError(f"Unsupported file type: {content_type}")

        return extract_expense_data(text)
    except Exception as e:
        logger.error(f"Bill processing failed: {e}")
        raise
