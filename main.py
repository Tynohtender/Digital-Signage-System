from fastapi import FastAPI, Depends, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List
import random
import string
import shutil
import os
import re

import models
from database import engine, SessionLocal

# ------------------------
# APP INIT
# ------------------------
app = FastAPI()

# ------------------------
# CORS
# ------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ------------------------
# IMAGE STORAGE
# ------------------------
UPLOAD_FOLDER = "images"

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

app.mount("/images", StaticFiles(directory="images"), name="images")

# ------------------------
# DB SETUP
# ------------------------
models.Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ------------------------
# HELPERS
# ------------------------
def generate_password(length=6):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))

def generate_slug(name):
    base = re.sub(r'\W+', '-', name.lower()).strip('-')
    random_part = ''.join(random.choices(string.ascii_lowercase + string.digits, k=4))
    return f"{base}-{random_part}"

# ------------------------
# AUTO ADMIN
# ------------------------
def create_admin():
    db: Session = SessionLocal()

    admin = db.query(models.User).filter(models.User.email == "admin@system.com").first()

    if not admin:
        db.add(models.User(
            email="admin@system.com",
            password="admin123",
            role="admin",
            client_id=None
        ))
        db.commit()
        print("✅ Admin created: admin@system.com / admin123")

    db.close()

# ------------------------
# SCHEMAS
# ------------------------
class ClientCreate(BaseModel):
    business_name: str

class ClientUserCreate(BaseModel):
    business_name: str
    email: str

class MenuCreate(BaseModel):
    title: str
    price: str
    client_id: int
    image: str

class MenuUpdate(BaseModel):
    title: str
    price: str

class UserCreate(BaseModel):
    email: str
    password: str
    client_id: int

class LoginData(BaseModel):
    email: str
    password: str

# ------------------------
# ROOT
# ------------------------
@app.get("/")
def home():
    return {"message": "Digital Signage API Running"}

# ------------------------
# CLIENTS
# ------------------------
@app.get("/clients/")
def get_clients(db: Session = Depends(get_db)):
    return db.query(models.Client).all()

@app.post("/create-client/")
def create_client(client: ClientCreate, db: Session = Depends(get_db)):

    slug = generate_slug(client.business_name)

    new_client = models.Client(
        business_name=client.business_name,
        slug=slug
    )

    db.add(new_client)
    db.commit()
    db.refresh(new_client)

    return new_client

@app.delete("/delete-client/{id}")
def delete_client(id: int, db: Session = Depends(get_db)):

    db.query(models.Menu).filter(models.Menu.client_id == id).delete()
    db.query(models.User).filter(models.User.client_id == id).delete()

    client = db.query(models.Client).filter(models.Client.id == id).first()

    if client:
        db.delete(client)
        db.commit()

    return {"message": "Client deleted"}

# ------------------------
# ADMIN CREATE CLIENT + USER (WITH SLUG)
# ------------------------
@app.post("/admin/create-client-user/")
def create_client_user(data: ClientUserCreate, db: Session = Depends(get_db)):
    try:
        slug = generate_slug(data.business_name)

        new_client = models.Client(
            business_name=data.business_name,
            slug=slug
        )

        db.add(new_client)
        db.commit()
        db.refresh(new_client)

        password = generate_password()

        new_user = models.User(
            email=data.email,
            password=password,
            role="client",
            client_id=new_client.id
        )

        db.add(new_user)
        db.commit()

        return {
            "email": data.email,
            "password": password,
            "client_id": new_client.id,
            "slug": slug
        }

    except Exception as e:
        print("ERROR:", str(e))   # 🔥 THIS LINE IS IMPORTANT
        return {"error": str(e)}# ------------------------
    

# MENU SYSTEM
# ------------------------
@app.post("/add-menu/")
def add_menu(item: MenuCreate, db: Session = Depends(get_db)):

    new_item = models.Menu(
        title=item.title,
        price=item.price,
        image=item.image,
        client_id=item.client_id
    )

    db.add(new_item)
    db.commit()
    db.refresh(new_item)

    return new_item

@app.get("/menu/{client_id}")
def get_menu(client_id: int, db: Session = Depends(get_db)):
    return db.query(models.Menu).filter(models.Menu.client_id == client_id).all()

# SaaS ENDPOINT
@app.get("/menu-by-slug/{slug}")
def get_menu_by_slug(slug: str, db: Session = Depends(get_db)):

    client = db.query(models.Client).filter(models.Client.slug == slug).first()

    if not client:
        return {"error": "Client not found"}

    return db.query(models.Menu).filter(models.Menu.client_id == client.id).all()

@app.get("/client-by-slug/{slug}")
def get_client(slug: str, db: Session = Depends(get_db)):
    client = db.query(models.Client).filter(models.Client.slug == slug).first()

    if not client:
        return {"error": "Client not found"}

    return client

@app.put("/update-menu/{id}")
def update_menu(id: int, item: MenuUpdate, db: Session = Depends(get_db)):

    menu_item = db.query(models.Menu).filter(models.Menu.id == id).first()

    if not menu_item:
        return {"error": "Item not found"}

    menu_item.title = item.title
    menu_item.price = item.price

    db.commit()

    return {"message": "Menu updated"}

@app.delete("/delete-menu/{id}")
def delete_menu(id: int, db: Session = Depends(get_db)):

    item = db.query(models.Menu).filter(models.Menu.id == id).first()

    if item:
        db.delete(item)
        db.commit()

    return {"message": "Deleted"}

# ------------------------
# USERS
# ------------------------
@app.post("/register/")
def register(user: UserCreate, db: Session = Depends(get_db)):

    new_user = models.User(
        email=user.email,
        password=user.password,
        client_id=user.client_id,
        role="client"
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)

    return new_user    

@app.post("/login/")
def login(data: LoginData, db: Session = Depends(get_db)):

    user = db.query(models.User).filter(
        models.User.email == data.email,
        models.User.password == data.password
    ).first()

    if not user:
        return {"error": "Invalid credentials"}

    return {
        "message": "Login successful",
        "client_id": user.client_id,
        "role": user.role
    }

# ------------------------
# IMAGE UPLOAD
# ------------------------
@app.post("/upload-image/")
def upload_image(file: UploadFile = File(...)):

    filename = f"{random.randint(1000,9999)}_{file.filename}"
    file_path = os.path.join(UPLOAD_FOLDER, filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return {
        "filename": filename,
        "url": f"/images/{filename}"   # 🔥 READY FOR FRONTEND
    }

# ------------------------
# INIT
# ------------------------
create_admin()