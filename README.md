# 💸 Bite Bill - Smart Expense Tracking Automation

![Bite Bill Logo](https://via.placeholder.com/150x150.png?text=💰)

An intelligent expense management system that automates bill processing from emails and documents using AI-powered insights.

## 🌟 Key Features

- 📧 **Gmail Integration** - Automatic detection of bills/invoices in your email
- 🧾 **Multi-Format Support** - Process PDF, JPEG, PNG, and email attachments
- 🔍 **OCR Extraction** - Tesseract-powered text recognition from images/PDFs
- 🤖 **AI Analysis** - Gemini-generated spending insights and recommendations
- 📈 **Interactive Dashboard** - Visualize spending with Plotly charts
- 🔐 **Secure Auth** - SQLite database with SHA-256 password hashing
- 📆 **Date Filtering** - Smart detection of transaction dates
- 💬 **Financial Assistant** - ChatGPT-like interface for expense queries

## 🛠️ Installation

### Prerequisites
- Python 3.9+
- Tesseract OCR ([Install Guide](https://tesseract-ocr.github.io/tessdoc/Installation.html))
- Google API Key ([Get from AI Studio](https://aistudio.google.com/))

```bash
# Clone repository
git clone https://github.com/yourusername/bitebill.git
cd bitebill

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
.\venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
echo "GOOGLE_API_KEY=your_actual_key_here" > .env
