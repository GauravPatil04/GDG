import streamlit as st
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import io
import re
import pandas as pd
import google.generativeai as genai
from datetime import datetime
import tempfile
import os
import matplotlib.pyplot as plt
import hashlib
import sqlite3

# Configure Gemini
GOOGLE_API_KEY = st.secrets.get("GOOGLE_API_KEY", os.getenv("GOOGLE_API_KEY"))

if not GOOGLE_API_KEY:
    st.error("Please set GOOGLE_API_KEY in secrets or environment variables")
    st.stop()

try:
    genai.configure(api_key=GOOGLE_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
except Exception as e:
    st.error(f"Failed to initialize Gemini: {str(e)}")
    st.stop()

# --- Database Functions ---
def initialize_database():
    """Initialize the SQLite database for user authentication"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            username TEXT PRIMARY KEY,
            name TEXT,
            password TEXT,
            email TEXT
        )
    ''')
    conn.commit()
    conn.close()

def create_user(username, name, password, email):
    """Create a new user in the database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    try:
        c.execute('INSERT INTO users VALUES (?, ?, ?, ?)', 
                 (username, name, hashed_password, email))
        conn.commit()
        return True
    except sqlite3.IntegrityError:
        return False
    finally:
        conn.close()

def verify_user(username, password):
    """Verify user credentials against the database"""
    conn = sqlite3.connect('users.db')
    c = conn.cursor()
    hashed_password = hashlib.sha256(password.encode()).hexdigest()
    c.execute('SELECT * FROM users WHERE username = ? AND password = ?', 
             (username, hashed_password))
    result = c.fetchone()
    conn.close()
    return result is not None

# --- Authentication Pages ---
def login_page():
    """Display login and registration forms"""
    st.title("💰 Bite Bill - Expense Tracker")
    
    login_tab, register_tab = st.tabs(["Login", "Register"])
    
    with login_tab:
        with st.form("login_form"):
            st.subheader("Login to Your Account")
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit_button = st.form_submit_button("Login")
            
            if submit_button:
                if verify_user(username, password):
                    st.session_state['authenticated'] = True
                    st.session_state['username'] = username
                    st.rerun()
                else:
                    st.error("Invalid username or password")
    
    with register_tab:
        with st.form("register_form"):
            st.subheader("Create New Account")
            new_username = st.text_input("Choose a username")
            new_name = st.text_input("Full name")
            new_email = st.text_input("Email")
            new_password = st.text_input("Choose a password", type="password")
            confirm_password = st.text_input("Confirm password", type="password")
            register_button = st.form_submit_button("Register")
            
            if register_button:
                if new_password != confirm_password:
                    st.error("Passwords don't match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters")
                else:
                    if create_user(new_username, new_name, new_password, new_email):
                        st.success("Registration successful! Please login.")
                    else:
                        st.error("Username already exists")

# --- Image Processing Functions ---
def preprocess_image(image):
    """Enhance image for better OCR results"""
    image = image.convert('L')  # Convert to grayscale
    image = image.filter(ImageFilter.SHARPEN)
    enhancer = ImageEnhance.Contrast(image)
    image = enhancer.enhance(2)
    return image

def process_image(image):
    """Extract text from image using OCR"""
    image = preprocess_image(image)
    custom_oem_psm_config = r'--oem 3 --psm 6'
    text = pytesseract.image_to_string(image, config=custom_oem_psm_config)
    return text

# --- Information Extraction ---
def extract_information(text):
    """Extract key information from bill text with comprehensive regex patterns"""
    # --- Amount Extraction (Multiple Patterns) ---
    amount_patterns = [
        # Standard patterns with currency symbols
        r'(?:Total|Subtotal|Grand\s*Total|Amount|Bill\s*Amount|TOTAL\s*\(?[A-Z]{3}\)?|TOTAL\s*DUE|Total\s*Invoice\s*Amount)\s*[:=-]?\s*[₹$£€]?\s*([\d,]+(?:\.\d{2})?)',
        r'[₹$£€]\s*([\d,]+(?:\.\d{2})?)',
        r'\b(?:RS?|INR)\s*\.?\s*([\d,]+(?:\.\d{2})?)',
        
        # Patterns with currency symbols at end
        r'([\d,]+(?:\.\d{2})?)\s*(?:RS?|INR|USD|EUR|GBP)',
        
        # Patterns with decimal places
        r'\b(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)\b',
        
        # Patterns for amounts in brackets/parentheses (often indicates totals)
        r'\(([\d,]+(?:\.\d{2})?)\)',
        
        # Patterns for amounts after "Total" without explicit label
        r'(?:Total|TOTAL)\b\D*?(\d{1,3}(?:,\d{3})*(?:\.\d{2})?)',
        
        # Patterns for amounts with thousands separators
        r'\b(\d{1,3}(?:,\d{3})+)',
        
        # Patterns for amounts with words like "only" at end
        r'([\d,]+(?:\.\d{2})?)\s*(?:only|/-)',
        
        # Patterns for amounts in different formats
        r'\b(\d+\.\d{2})\b',
        r'\b(\d+)\b(?!\s*%)'  # Basic number but not followed by %
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

    # --- Enhanced Date Extraction (with Walmart-specific patterns) ---
    date_patterns = [
        # Walmart-specific patterns (mm/dd/yy with optional time)
        r'\b(\d{1,2}/\d{1,2}/\d{2})(?:\s+\d{1,2}:\d{2}:\d{2})?\b',
        
        # Other common receipt date patterns
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
                # Try multiple date formats for parsing, with Walmart format first
                for fmt in (
                    "%m/%d/%y",  # Walmart format (10/18/20)
                    "%m/%d/%Y",  # Alternative format
                    "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y", 
                    "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%Y", "%m/%d/%Y",
                    "%d-%b-%Y", "%d-%B-%Y", "%d-%m-%y", "%d.%m.%Y",
                    "%Y %b %d", "%dth %b %Y", "%a, %b %d, %Y"
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

    # --- Category Extraction (Enhanced Patterns) ---
    category_keywords = {
        "Shopping": [
            r'\bwalmart\b', r'\bmall\b', r'\bamazon\b', r'\bflipkart\b', 
            r'\bpurchase\b', r'\bitem\b', r'\binvoice\b', r'\bstore\b',
            r'\bshopping\b', r'\bretail\b', r'\boutlet\b', r'\bmarket\b',
            r'\bpos\b', r'\becommerce\b', r'\bmerchant\b'
        ],
        "Medical": [
            r'\bhospital\b', r'\bclinic\b', r'\bpharmacy\b', 
            r'\bmedicine\b', r'\bdoctor\b', r'\bhealthcare\b',
            r'\bmedical\b', r'\bprescription\b', r'\bdiagnostic\b',
            r'\blab\b', r'\bhealth\s*care\b', r'\bhospitality\b'
        ],
        "Entertainment": [
            r'\bmovie\b', r'\bcinema\b', r'\bnetflix\b', 
            r'\bconcert\b', r'\btheatre\b', r'\bticket\b',
            r'\bentertainment\b', r'\bstreaming\b', r'\bgame\b',
            r'\bgaming\b', r'\bamusement\b', r'\bpark\b'
        ],
        "Fuel": [
            r'\bpetrol\b', r'\bdiesel\b', r'\bfuel\b', 
            r'\bgas\s*station\b', r'\bhp\b', r'\bindian\s*oil\b',
            r'\bpetroleum\b', r'\bfilling\s*station\b', r'\bgasoline\b',
            r'\bcng\b', r'\blpg\b', r'\bfuel\s*price\b'
        ],
        "Food": [
            r'\brestaurant\b', r'\bfood\b', r'\bbill\b', 
            r'\bdine\b', r'\bmeal\b', r'\bdominos\b', 
            r'\bzomato\b', r'\bswiggy\b', r'\bcafe\b',
            r'\bbakery\b', r'\bbistro\b', r'\bfast\s*food\b',
            r'\bgrocery\b', r'\bsupermarket\b', r'\bkitchen\b'
        ],
        "Travel": [
            r'\bhotel\b', r'\bflight\b', r'\bairlines\b', 
            r'\btrain\b', r'\birctc\b', r'\bubers?\b', 
            r'\bola\b', r'\btravel\b', r'\btourism\b',
            r'\baccomodation\b', r'\bairport\b', r'\btaxi\b',
            r'\bcab\b', r'\btransport\b', r'\bbus\b'
        ],
        "Utilities": [
            r'\belectricity\b', r'\bwater\b', r'\bbilldesk\b', 
            r'\bbroadband\b', r'\bwifi\b', r'\binternet\b',
            r'\butility\b', r'\bphone\b', r'\bmobile\b',
            r'\bbill\b', r'\bpayment\b', r'\bpostpaid\b',
            r'\bcable\b', r'\btv\b', r'\btelecom\b'
        ],
        "Education": [
            r'\bschool\b', r'\bcollege\b', r'\buniversity\b',
            r'\beducation\b', r'\btuition\b', r'\bcourse\b',
            r'\bexam\b', r'\btextbook\b', r'\blibrary\b',
            r'\bstudent\b', r'\blearning\b', r'\btraining\b'
        ]
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

# --- Gemini Analysis Functions ---
def analyze_with_gemini(expense_data, financial_context=None):
    """Get spending insights from Gemini for individual bills"""
    if not expense_data.get('amount') or not expense_data.get('category'):
        return "Cannot analyze - missing amount or category"
    
    prompt = f"""
    Analyze this expense record and provide personalized financial advice:
    
    Expense Details:
    - Amount: {expense_data.get('amount', 'N/A')}
    - Date: {expense_data.get('date', 'N/A')}
    - Category: {expense_data.get('category', 'N/A')}
    - Context from bill: {expense_data.get('raw_text', '')[:500]}... [truncated]
    
    Financial Context:
    {financial_context if financial_context else "No additional financial context provided"}
    
    Please provide:
    1. A brief analysis of this expense (1-2 sentences)
    2. Suggestions for better spending in this category (2-3 bullet points)
    3. Any potential savings opportunities (1-2 suggestions)
    4. General financial advice related to this expense (1-2 sentences)
    
    Keep the response under 200 words total.
    """
    
    try:
        response = model.generate_content(prompt)
        if not response.text:
            return "Received empty response from Gemini"
        return response.text
    except Exception as e:
        error_msg = f"Gemini analysis failed: {str(e)}"
        if "404" in str(e):
            error_msg += "\n\nNote: Please check the latest Gemini documentation for available models."
        return error_msg

def get_comprehensive_analysis(expenses_df, financial_context):
    """Get overall spending analysis based on all bills"""
    if expenses_df.empty:
        return "No expenses to analyze"
    
    # Prepare summary data
    total_spent = expenses_df['Amount'].sum()
    avg_monthly = expenses_df.groupby(expenses_df['Date'].str[:7])['Amount'].sum().mean()
    category_spending = expenses_df.groupby('Category')['Amount'].sum().sort_values(ascending=False)
    top_category = category_spending.index[0] if not category_spending.empty else "N/A"
    top_amount = category_spending.iloc[0] if not category_spending.empty else 0
    
    prompt = f"""
    Analyze this comprehensive spending data and provide personalized financial advice:
    
    Spending Overview:
    - Total tracked expenses: ${total_spent:,.2f}
    - Average monthly spending: ${avg_monthly:,.2f}
    - Number of transactions: {len(expenses_df)}
    - Top spending category: {top_category} (${top_amount:,.2f})
    
    Spending by Category:
    {category_spending.to_string()}
    
    Financial Context:
    {financial_context}
    
    Please provide:
    1. Overall spending health assessment (1 paragraph)
    2. Top 3 spending categories needing attention
    3. Specific recommendations for each problematic category
    4. General money-saving strategies
    5. Suggested budget adjustments
    
    Format the response with clear headings and bullet points.
    Keep the response under 400 words.
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Could not generate comprehensive analysis: {str(e)}"

# --- Visualization Functions ---
def create_category_visualizations(categories, amounts):
    """Create bar, pie, and donut charts for category spending"""
    colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4', '#FFD166', '#06D6A0', '#118AB2', '#EF476F']
    
    # Create figure with 3 subplots
    fig, (ax1, ax2, ax3) = plt.subplots(1, 3, figsize=(18, 6))
    
    # Bar Chart
    bars = ax1.bar(categories, amounts, color=colors[:len(categories)])
    ax1.set_title('Spending by Category', fontweight='bold')
    ax1.set_xlabel('Categories', fontweight='bold')
    ax1.set_ylabel('Amount ($)', fontweight='bold')
    
    # Rotate x-labels if needed
    if len(max(categories, key=len)) > 8:
        plt.setp(ax1.get_xticklabels(), rotation=45, ha='right')
    
    # Add values on top of bars
    for bar in bars:
        height = bar.get_height()
        ax1.text(bar.get_x() + bar.get_width()/2., height,
                f'${height:,.2f}',
                ha='center', va='bottom')

    # Pie Chart
    pie_wedges, pie_texts, pie_autotexts = ax2.pie(
        amounts, 
        labels=categories, 
        colors=colors[:len(categories)],
        autopct='%1.1f%%',
        startangle=90,
        textprops={'fontweight': 'bold'}
    )
    ax2.set_title('Spending Breakdown', fontweight='bold')
    plt.setp(pie_autotexts, size=10, weight='bold')  # Format percentage texts

    # Donut Chart
    donut_wedges, donut_texts, donut_autotexts = ax3.pie(
        amounts,
        colors=colors[:len(categories)],
        startangle=90,
        pctdistance=0.85,
        autopct='%1.1f%%',
        textprops={'fontweight': 'bold'}
    )

    # Draw white circle in the center
    centre_circle = plt.Circle((0,0), 0.70, fc='white')
    fig.gca().add_artist(centre_circle)

    # Equal aspect ratio ensures the donut chart is circular
    ax3.axis('equal')
    ax3.set_title('Spending Distribution', fontweight='bold')
    
    # Add legend
    ax3.legend(
        donut_wedges,
        categories,
        title='Categories',
        loc='center left',
        bbox_to_anchor=(1, 0, 0.5, 1)
    )

    plt.tight_layout(pad=3.0)
    return fig

def create_monthly_trend_chart(expenses_df):
    """Create visualization of monthly spending trend"""
    if expenses_df.empty:
        return None
    
    monthly_spending = expenses_df.groupby(expenses_df['Date'].str[:7])['Amount'].sum()
    
    fig, ax = plt.subplots(figsize=(10, 4))
    monthly_spending.plot(kind='bar', ax=ax, color='#4ECDC4')
    ax.set_xlabel('Month')
    ax.set_ylabel('Amount ($)')
    ax.set_title('Monthly Spending Trend')
    plt.xticks(rotation=45)
    plt.tight_layout()
    return fig

# --- Gemini Chart Bot Functions ---
def gemini_chat_bot():
    """Create a Gemini-powered chat interface for financial questions"""
    st.subheader("💬 Gemini Financial Assistant")
    st.write("Ask any financial questions or get advice about your expenses")
    
    # Initialize chat history
    if "gemini_messages" not in st.session_state:
        st.session_state.gemini_messages = []
    
    # Display chat messages from history on app rerun
    for message in st.session_state.gemini_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
    
    # Accept user input
    if prompt := st.chat_input("Ask about your finances..."):
        # Add user message to chat history
        st.session_state.gemini_messages.append({"role": "user", "content": prompt})
        # Display user message in chat message container
        with st.chat_message("user"):
            st.markdown(prompt)
        
        # Display assistant response in chat message container
        with st.chat_message("assistant"):
            with st.spinner("Thinking..."):
                try:
                    # Include financial context in the prompt
                    full_prompt = f"""
                    Financial Context:
                    {st.session_state.financial_context}
                    
                    Expense History:
                    {st.session_state.expenses.to_string() if not st.session_state.expenses.empty else "No expense history"}
                    
                    User Question: {prompt}
                    
                    Please provide a detailed, helpful response with specific advice based on the financial context and expense history.
                    """
                    
                    response = model.generate_content(full_prompt)
                    if response.text:
                        st.markdown(response.text)
                        st.session_state.gemini_messages.append({"role": "assistant", "content": response.text})
                    else:
                        st.error("Sorry, I couldn't generate a response. Please try again.")
                except Exception as e:
                    st.error(f"An error occurred: {str(e)}")

# --- Main Application ---
def dashboard():
    """Main dashboard that shows after successful login"""
    # Custom CSS
    st.markdown("""
    <style>
        .header {
            font-size: 36px !important;
            font-weight: bold;
            color: #4a4a4a;
            margin-bottom: 20px;
        }
        .subheader {
            font-size: 20px !important;
            color: #6c6c6c;
            margin-bottom: 10px;
        }
        .analysis-box {
            background-color: #f9f9f9;
            border-radius: 10px;
            padding: 20px;
            margin-top: 20px;
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
        }
        .extracted-data {
            background-color: #e8f4fc;
            border-radius: 10px;
            padding: 15px;
            margin-bottom: 20px;
        }
        .stButton>button {
            background-color: #4CAF50;
            color: white;
            border-radius: 5px;
            padding: 10px 24px;
            font-weight: bold;
        }
        .stButton>button:hover {
            background-color: #45a049;
        }
        .file-name {
            font-size: 14px;
            color: #666;
            margin-top: 5px;
        }
        .tab-content {
            padding: 15px 0;
        }
        .chart-container {
            margin-bottom: 30px;
        }
        .chat-container {
            border: 1px solid #e0e0e0;
            border-radius: 10px;
            padding: 15px;
            margin-top: 20px;
            height: 500px;
            overflow-y: auto;
        }
    </style>
    """, unsafe_allow_html=True)
    
    st.markdown('<div class="header">💰 Bite Bill</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="subheader">Welcome back, {st.session_state["username"]}!</div>', unsafe_allow_html=True)
    
    # Initialize session state
    if 'expenses' not in st.session_state:
        st.session_state.expenses = pd.DataFrame(columns=["Date", "Amount", "Category", "Filename"])
    if 'processing_results' not in st.session_state:
        st.session_state.processing_results = []
    if 'financial_context' not in st.session_state:
        st.session_state.financial_context = ""
    if 'comprehensive_analysis' not in st.session_state:
        st.session_state.comprehensive_analysis = ""
    
    # Sidebar for financial context
    with st.sidebar:
        if st.button("Logout"):
            st.session_state['authenticated'] = False
            st.rerun()
            
        st.header("Your Financial Profile")
        monthly_income = st.number_input("Monthly Income ($)", min_value=0, value=5000, key='monthly_income')
        savings = st.number_input("Current Savings ($)", min_value=0, value=15000, key='savings')
        financial_goals = st.text_area("Financial Goals", "Save for vacation ($3,000)\nEmergency fund ($10,000)", key='financial_goals')
        
        # Store financial context
        st.session_state.financial_context = f"""
        Monthly income: ${monthly_income:,}
        Current savings: ${savings:,}
        Financial goals: {financial_goals}
        """
        
        st.markdown("---")
        st.markdown("### Expense History")
        if not st.session_state.expenses.empty:
            st.dataframe(st.session_state.expenses, hide_index=True)
            total_spent = st.session_state.expenses["Amount"].sum()
            st.metric("Total Tracked Expenses", f"${total_spent:,.2f}")
            
            # Show spending by category
            st.markdown("#### Spending by Category")
            category_spending = st.session_state.expenses.groupby('Category')['Amount'].sum()
            st.dataframe(category_spending, column_config={
                "Amount": st.column_config.ProgressColumn(
                    "Amount",
                    format="$%.2f",
                    min_value=0,
                    max_value=float(category_spending.max()) if not category_spending.empty else 0
                )
            })
        else:
            st.info("No expenses tracked yet")
    
    # Main content area
    tab1, tab2, tab3 = st.tabs(["Upload & Process Bills", "Comprehensive Analysis", "Financial Assistant"])
    
    with tab1:
        st.subheader("Upload Your Bills")
        uploaded_files = st.file_uploader("Choose image or PDF files", 
                                        type=["jpg", "jpeg", "png", "pdf"],
                                        accept_multiple_files=True,
                                        key="file_uploader")
        
        if uploaded_files and len(uploaded_files) > 0:
            # Display file selection
            st.write(f"Selected {len(uploaded_files)} file(s):")
            for file in uploaded_files:
                st.markdown(f'<div class="file-name">{file.name}</div>', unsafe_allow_html=True)
            
            # Process the files when button is clicked
            if st.button("Analyze All Bills", key="analyze_button"):
                with st.spinner(f"Processing {len(uploaded_files)} bills..."):
                    results = []
                    for file in uploaded_files:
                        try:
                            # Process each file
                            if file.type.startswith('image/'):
                                image = Image.open(io.BytesIO(file.read()))
                                text = process_image(image)
                            else:
                                # For PDFs, save temporarily
                                with tempfile.NamedTemporaryFile(delete=False) as tmp:
                                    tmp.write(file.read())
                                    try:
                                        from pdf2image import convert_from_path
                                        images = convert_from_path(tmp.name)
                                        text = ""
                                        for img in images:
                                            text += process_image(img)
                                    finally:
                                        os.unlink(tmp.name)
                            
                            # Extract information
                            expense_data = extract_information(text)
                            expense_data['filename'] = file.name
                            
                            # Get Gemini analysis
                            analysis = analyze_with_gemini(expense_data, st.session_state.financial_context)
                            
                            # Store results
                            results.append({
                                "filename": file.name,
                                "extracted_data": expense_data,
                                "analysis": analysis
                            })
                            
                            # Add to expense history if valid
                            if expense_data['amount'] and expense_data['date']:
                                new_expense = pd.DataFrame({
                                    "Date": [expense_data['date']],
                                    "Amount": [expense_data['amount']],
                                    "Category": [expense_data['category']],
                                    "Filename": [file.name]
                                })
                                st.session_state.expenses = pd.concat([st.session_state.expenses, new_expense], ignore_index=True)
                                
                        except Exception as e:
                            results.append({
                                "filename": file.name,
                                "error": f"Error processing file: {str(e)}"
                            })
                    
                    st.session_state.processing_results = results
                    st.success(f"Processed {len([r for r in results if 'error' not in r])} bills successfully!")
                    st.rerun()
        
        if 'processing_results' in st.session_state and st.session_state.processing_results:
            st.subheader("Individual Bill Results")
            
            for result in st.session_state.processing_results:
                with st.expander(f"Results for {result['filename']}", expanded=False):
                    if 'error' in result:
                        st.error(result['error'])
                    else:
                        expense_data = result['extracted_data']
                        
                        st.markdown("**Extracted Data**")
                        with st.container():
                            st.markdown('<div class="extracted-data">', unsafe_allow_html=True)
                            
                            cols = st.columns(3)
                            with cols[0]:
                                st.metric("Amount", f"${expense_data['amount']:,.2f}" if expense_data['amount'] else "Not detected")
                            with cols[1]:
                                st.metric("Date", expense_data['date'] if expense_data['date'] else "Not detected")
                            with cols[2]:
                                st.metric("Category", expense_data['category'])
                            
                            st.markdown('</div>', unsafe_allow_html=True)
                        
                        st.markdown("**AI Analysis**")
                        with st.container():
                            st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
                            st.markdown(result['analysis'])
                            st.markdown('</div>', unsafe_allow_html=True)
    
    with tab2:
        if 'expenses' in st.session_state and not st.session_state.expenses.empty:
            st.subheader("Comprehensive Spending Analysis")
            
            # Initialize analysis trigger if not exists
            if 'generate_analysis' not in st.session_state:
                st.session_state.generate_analysis = False
            
            # Button to trigger analysis generation
            if st.button("Generate Overall Recommendations"):
                st.session_state.generate_analysis = True
            
            # Generate and display analysis when triggered
            if st.session_state.get('generate_analysis', False):
                with st.spinner("Analyzing your complete spending patterns..."):
                    analysis = get_comprehensive_analysis(
                        st.session_state.expenses,
                        st.session_state.financial_context
                    )
                    st.session_state.comprehensive_analysis = analysis
                    st.session_state.generate_analysis = False  # Reset trigger
            
            # Display analysis if available
            if 'comprehensive_analysis' in st.session_state:
                with st.container():
                    st.markdown('<div class="analysis-box">', unsafe_allow_html=True)
                    st.markdown(st.session_state.comprehensive_analysis)
                    st.markdown('</div>', unsafe_allow_html=True)
            
            # Visualizations
            st.subheader("Spending Visualizations")
            
            # Get category data from expenses
            category_spending = st.session_state.expenses.groupby('Category')['Amount'].sum()
            categories = category_spending.index.tolist()
            amounts = category_spending.values.tolist()
            
            # Create and display the visualizations
            if categories and amounts:
                try:
                    st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                    fig = create_category_visualizations(categories, amounts)
                    st.pyplot(fig)
                    st.markdown('</div>', unsafe_allow_html=True)
                except Exception as e:
                    st.error(f"Could not generate visualizations: {str(e)}")
                
                st.markdown('<div class="chart-container">', unsafe_allow_html=True)
                monthly_trend = create_monthly_trend_chart(st.session_state.expenses)
                if monthly_trend:
                    st.pyplot(monthly_trend)
                else:
                    st.warning("Not enough data for monthly trend")
                st.markdown('</div>', unsafe_allow_html=True)
            else:
                st.warning("Not enough data for visualizations")
            
            # Raw data
            st.subheader("All Processed Expenses")
            st.dataframe(st.session_state.expenses, hide_index=True)
            
        else:
            st.info("Process some bills first to see comprehensive analysis")
    
    with tab3:
        gemini_chat_bot()

def main():
    st.set_page_config(page_title="Smart Expense Tracker", page_icon="💰", layout="wide")
    
    # Initialize database
    initialize_database()
    
    # Check authentication
    if 'authenticated' not in st.session_state:
        st.session_state['authenticated'] = False
    
    if not st.session_state['authenticated']:
        login_page()
    else:
        dashboard()

if __name__ == "__main__":
    main()