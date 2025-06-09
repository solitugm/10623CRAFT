import os
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, Path
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from database import Base, engine, SessionLocal
from sqlalchemy.orm import Session
from models import Post, Comment
from typing import Optional
from sqlalchemy import Column, String
import models

app = FastAPI()

# 템플릿, static 파일 연결
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# 루트 경로 처리
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

models.Base.metadata.create_all(bind=engine)

UPLOAD_DIR = "static/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@app.get("/create", response_class=HTMLResponse)
async def create_form(request: Request):
    return templates.TemplateResponse("create.html", {"request": request})

@app.post("/create")
async def create_post(
    request: Request,
    title: str = Form(...),
    description: str = Form(""),
    image: UploadFile = File(None),
    db: Session = Depends(get_db)
):
    image_path = None
    if image:
        filename = f"{UPLOAD_DIR}/{image.filename}"
        with open(filename, "wb") as f:
            f.write(await image.read())
        image_path = filename

    new_post = Post(title=title, description=description, image_path=image_path)
    db.add(new_post)
    db.commit()
    db.refresh(new_post)

    return RedirectResponse(url="/posts", status_code=302)

@app.get("/posts", response_class=HTMLResponse)
def get_posts(request: Request, db: Session = Depends(get_db)):
    posts = db.query(Post).order_by(Post.created_at.desc()).all()
    return templates.TemplateResponse("posts.html", {"request": request, "posts": posts})

@app.post("/complete/{post_id}")
def mark_as_found(
    post_id: int,
    db: Session = Depends(get_db)
):
    post = db.query(Post).filter(Post.id == post_id).first()
    if post:
        post.status = "완료" # type: ignore
        db.commit()
    return RedirectResponse(url="/posts", status_code=302)

@app.get("/post/{post_id}", response_class=HTMLResponse)
def post_detail(post_id: int, request: Request, db: Session = Depends(get_db)):
    post = db.query(Post).filter(Post.id == post_id).first()
    return templates.TemplateResponse("post_detail.html", {"request": request, "post": post})

@app.post("/post/{post_id}/comment")
def add_comment(post_id: int, content: str = Form(...), db: Session = Depends(get_db)):
    comment = Comment(content=content, post_id=post_id)
    db.add(comment)
    db.commit()
    return RedirectResponse(url=f"/post/{post_id}", status_code=302)
