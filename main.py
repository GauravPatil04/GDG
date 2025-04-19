from fastapi import FastAPI, Request, Form, UploadFile, File
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from starlette.middleware.sessions import SessionMiddleware
from supabase import create_client, Client
from ocr_utils import extract_info_from_image
from gemini_utils import analyze_with_gemini
from pathlib import Path
import shutil
import os
from datetime import datetime
from dotenv import load_dotenv
from typing import List

# Load environment variables
load_dotenv()

# Initialize FastAPI
app = FastAPI()
app.add_middleware(SessionMiddleware, secret_key="your-secret-key")

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Configure templates and static files
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")

# Ensure uploads directory exists
uploads_dir = BASE_DIR / "uploads"
uploads_dir.mkdir(exist_ok=True)

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    """Landing page before authentication"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, username: str = Form(...), password: str = Form(...)):
    try:
        # Check user in Supabase users1 table
        response = supabase.table("users1").select("*").eq("username", username).execute()
        if response.data and response.data[0]["password"] == password:
            request.session["user"] = username
            return RedirectResponse("/dashboard", status_code=302)
    except Exception as e:
        print(f"Login error: {e}")
    
    return templates.TemplateResponse("login.html", {
        "request": request, 
        "error": "Invalid credentials"
    })

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(request: Request, 
                username: str = Form(...),
                name: str = Form(...),
                password: str = Form(...),
                email: str = Form(...)):
    try:
        # Check if username exists
        response = supabase.table("users1").select("*").eq("username", username).execute()
        if response.data:
            return templates.TemplateResponse("signup.html", {
                "request": request, 
                "error": "Username already exists"
            })
        
        # Create new user in Supabase
        supabase.table("users1").insert({
            "username": username,
            "name": name,
            "password": password,
            "email": email
        }).execute()
        
        # Set session and redirect to dashboard
        request.session["user"] = username
        return RedirectResponse("/dashboard", status_code=302)
        
    except Exception as e:
        print(f"Signup error: {e}")
        return templates.TemplateResponse("signup.html", {
            "request": request, 
            "error": "Registration failed. Please try again."
        })

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/", status_code=302)
    
    # Fetch expenses and income from Supabase
    expenses = []
    income = []
    try:
        expenses = supabase.table("expenses3").select("*").eq("user_id", user).execute().data
        income = supabase.table("income").select("*").eq("user_id", user).execute().data
    except Exception as e:
        print(f"Dashboard data error: {e}")
    
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "expenses": expenses,
        "income": income
    })

@app.post("/upload")
async def upload_bills(request: Request, files: List[UploadFile] = File(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/", status_code=302)
    
    all_results = []
    
    for file in files:
        file_path = uploads_dir / file.filename
        try:
            # Save file
            with open(file_path, "wb") as f:
                shutil.copyfileobj(file.file, f)

            # Process file
            data = extract_info_from_image(file_path)
            analysis = analyze_with_gemini(data)
            
            # Save to expenses3 table
            expense_data = {
                "user_id": user,
                "amount": float(data.get("amount", 0)),
                "date": data.get("date", datetime.now().date().isoformat()),
                "category": data.get("category", "Uncategorized")
            }
            
            # Add description if analysis exists
            if analysis:
                expense_data["description"] = analysis[:500]  # Truncate if too long
            
            supabase.table("expenses3").insert(expense_data).execute()
            
            all_results.append({
                "filename": file.filename,
                "data": data,
                "analysis": analysis,
                "success": True
            })
            
        except Exception as e:
            all_results.append({
                "filename": file.filename,
                "error": f"Failed to process file: {str(e)}",
                "success": False
            })
        finally:
            # Clean up file
            try:
                os.unlink(file_path)
            except:
                pass
    
    # Refresh data after upload
    expenses = supabase.table("expenses3").select("*").eq("user_id", user).execute().data
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "results": all_results,
        "expenses": expenses
    })

@app.post("/add-income")
async def add_income(request: Request, 
                    amount: float = Form(...),
                    date: str = Form(...),
                    source: str = Form(...)):
    user = request.session.get("user")
    if not user:
        return RedirectResponse("/", status_code=302)
    
    try:
        supabase.table("income").insert({
            "user_id": user,
            "amount": amount,
            "date": date,
            "source": source
        }).execute()
    except Exception as e:
        print(f"Income save error: {e}")
    
    return RedirectResponse("/dashboard", status_code=302)

@app.get("/logout")
async def logout(request: Request):
    request.session.clear()
    return RedirectResponse("/", status_code=302)