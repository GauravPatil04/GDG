from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from supabase import create_client, Client
import uuid
import os
from ocr_processor import process_bill_file
from typing import Annotated
import logging
from datetime import datetime

# try:
#     from .ocr_processor import process_bill_file  # Relative import
# except ImportError:
#     from ocr_processor import process_bill_file  # Absolute import

app = FastAPI()

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")
logger = logging.getLogger(__name__)

# Supabase configuration
SUPABASE_URL = "https://evqpuqeucgsqafflseug.supabase.co"
SUPABASE_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImV2cXB1cWV1Y2dzcWFmZmxzZXVnIiwicm9sZSI6InNlcnZpY2Vfcm9sZSIsImlhdCI6MTc0NDgyNzM2MywiZXhwIjoyMDYwNDAzMzYzfQ.vBDY4VXNOgNFFk9MMYgf9aAGgSAtgFMMY_fzPI49QQg"
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Session storage
sessions = {}

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.get("/signup", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("signup.html", {"request": request})

@app.post("/signup")
async def signup(email: str = Form(...), password: str = Form(...)):
    try:
        result = supabase.auth.sign_up({"email": email, "password": password})
        if result.user:
            user_id = result.user.id
            supabase.table("users").insert({
                "id": user_id,
                "email": email,
                "income": 0
            }).execute()
            sessions[email] = result.session.access_token
            response = RedirectResponse(url="/dashboard", status_code=302)
            response.set_cookie(key="email", value=email)
            return response
    except Exception as e:
        print(f"Signup error: {e}")
    return RedirectResponse(url="/signup", status_code=302)

@app.post("/login")
async def login(email: str = Form(...), password: str = Form(...)):
    try:
        result = supabase.auth.sign_in_with_password({"email": email, "password": password})
        if result.user:
            sessions[email] = result.session.access_token
            response = RedirectResponse(url="/dashboard", status_code=302)
            response.set_cookie(key="email", value=email)
            return response
    except Exception as e:
        print(f"Login error: {e}")
    return RedirectResponse(url="/login", status_code=302)

@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request):
    email = request.cookies.get("email")
    if not email or email not in sessions:
        return RedirectResponse(url="/", status_code=302)

    try:
        user = supabase.auth.get_user(sessions[email])
        if not user.user:
            return RedirectResponse(url="/", status_code=302)

        user_id = user.user.id
        user_data = supabase.table("users").select("*").eq("id", user_id).single().execute().data
        if not user_data:
            return RedirectResponse(url="/", status_code=302)

        expenses = supabase.table("expenses1").select("*").eq("user_id", user_id).order("expense_date").execute().data
        total_expenses = sum(exp["expense_amount"] for exp in expenses) if expenses else 0
        income = user_data["income"]
        savings = income - total_expenses

        return templates.TemplateResponse("dashboard.html", {
            "request": request,
            "expenses": expenses,
            "income": income,
            "total_expenses": total_expenses,
            "savings": savings,
            "email": email
        })
    except Exception as e:
        print(f"Dashboard error: {e}")
        return RedirectResponse(url="/", status_code=302)

@app.post("/add")
async def add_expense(
    request: Request,
    expense_amount: int = Form(None),
    expense_date: str = Form(None),
    category: str = Form(None),
    income: int = Form(None)
):
    email = request.cookies.get("email")
    if not email or email not in sessions:
        return RedirectResponse(url="/", status_code=302)

    try:
        user = supabase.auth.get_user(sessions[email])
        user_id = user.user.id
        user_data = supabase.table("users").select("*").eq("id", user_id).single().execute().data
        
        if income is not None:
            supabase.table("users").update({"income": income}).eq("id", user_id).execute()
            user_data["income"] = income
            
            expenses = supabase.table("expenses1").select("*").eq("user_id", user_id).execute().data
            total_expenses = sum(exp["expense_amount"] for exp in expenses) if expenses else 0
            savings = income - total_expenses
            
            return JSONResponse(content={
                "income": income,
                "total_expenses": total_expenses,
                "savings": savings
            })

        if expense_amount and expense_date and category:
            new_expense = {
                "id": str(uuid.uuid4()),
                "user_id": user_id,
                "expense_amount": expense_amount,
                "expense_date": expense_date,
                "category": category
            }

            supabase.table("expenses1").insert(new_expense).execute()

            expenses = supabase.table("expenses1").select("*").eq("user_id", user_id).execute().data
            total_expenses = sum(exp["expense_amount"] for exp in expenses) if expenses else 0
            savings = user_data["income"] - total_expenses

            return JSONResponse(content={
                **new_expense,
                "total_expenses": total_expenses,
                "savings": savings,
                "income": user_data["income"]
            })

    except Exception as e:
        print(f"Add expense error: {e}")
    return JSONResponse(content={"error": "Invalid request"}, status_code=400)

@app.post("/update/{expense_id}")
async def update_expense(
    request: Request,
    expense_id: str,
    expense_amount: int = Form(...),
    expense_date: str = Form(...),
    category: str = Form(...),
):
    email = request.cookies.get("email")
    if not email or email not in sessions:
        return RedirectResponse(url="/", status_code=302)

    try:
        user = supabase.auth.get_user(sessions[email])
        user_id = user.user.id

        supabase.table("expenses1").update({
            "expense_amount": expense_amount,
            "expense_date": expense_date,
            "category": category
        }).eq("id", expense_id).eq("user_id", user_id).execute()

        user_data = supabase.table("users").select("*").eq("id", user_id).single().execute().data
        expenses = supabase.table("expenses1").select("*").eq("user_id", user_id).execute().data
        total_expenses = sum(exp["expense_amount"] for exp in expenses) if expenses else 0
        savings = user_data["income"] - total_expenses

        return JSONResponse(content={
            "expense_id": expense_id,
            "total_expenses": total_expenses,
            "savings": savings
        })
    except Exception as e:
        print(f"Update expense error: {e}")
    return JSONResponse(content={"error": "Failed to update expense"}, status_code=400)

@app.post("/delete/{expense_id}")
async def delete_expense(request: Request, expense_id: str):
    email = request.cookies.get("email")
    if not email or email not in sessions:
        return RedirectResponse(url="/", status_code=302)

    try:
        user = supabase.auth.get_user(sessions[email])
        user_id = user.user.id
        
        supabase.table("expenses1").delete().eq("id", expense_id).execute()
        
        user_data = supabase.table("users").select("*").eq("id", user_id).single().execute().data
        expenses = supabase.table("expenses1").select("*").eq("user_id", user_id).execute().data
        total_expenses = sum(exp["expense_amount"] for exp in expenses) if expenses else 0
        savings = user_data["income"] - total_expenses
        
        return JSONResponse(content={
            "expense_id": expense_id,
            "total_expenses": total_expenses,
            "savings": savings
        })
    except Exception as e:
        print(f"Delete expense error: {e}")
    return JSONResponse(content={"error": "Failed to delete expense"}, status_code=400)


async def get_current_user(request: Request):
    token = request.session.get("access_token")
    if not token:
        return None

    try:
        user_response = supabase.auth.get_user(token)
        return user_response.user
    except Exception as e:
        logger.error(f"Error fetching user: {e}")
        return None


@app.post("/upload_bill")
async def upload_bill(
    request: Request,
    bill_image: UploadFile = File(...)
):
    email = request.cookies.get("email")
    if not email or email not in sessions:
        raise HTTPException(status_code=401, detail="Not authenticated")

    try:
        content = await bill_image.read()
        if not content:
            raise HTTPException(status_code=400, detail="Empty file")

        extracted_data = await process_bill_file(content, bill_image.content_type)

        if not extracted_data.get("amount") or not extracted_data.get("date"):
            raise HTTPException(status_code=400, detail="Could not extract required data")

        try:
            amount = int(round(float(extracted_data["amount"])))
        except (ValueError, TypeError):
            raise HTTPException(status_code=400, detail="Invalid amount format")

        # Flexible date parsing
        date_str = extracted_data["date"]
        date_formats = ["%d/%m/%Y", "%d-%m-%Y", "%Y-%m-%d", "%d %b %Y"]
        for fmt in date_formats:
            try:
                parsed_date = datetime.strptime(date_str, fmt)
                date = parsed_date.strftime("%Y-%m-%d")
                break
            except:
                continue
        else:
            date = datetime.now().strftime("%Y-%m-%d")

        user = supabase.auth.get_user(sessions[email])

        new_expense = {
            "id": str(uuid.uuid4()),
            "user_id": user.user.id,
            "expense_amount": amount,
            "expense_date": date,
            "category": extracted_data.get("category", "Other")
        }

        supabase.table("expenses1").insert(new_expense).execute()

        return JSONResponse({
            "message": "Bill processed successfully",
            "data": new_expense
        })

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Upload error: {e}")
        raise HTTPException(status_code=500, detail="Processing error")
