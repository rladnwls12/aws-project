from fastapi import FastAPI, HTTPException, Depends
from sqlalchemy import create_engine, Column, Integer, String, Boolean, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from pydantic import BaseModel, EmailStr
from passlib.context import CryptContext
from typing import Optional
import os, json, boto3

# ── AWS Secrets Manager에서 DB 정보 로드 ─────────────────
def get_secret(secret_name: str, region: str = "ap-northeast-2") -> dict:
    client = boto3.client("secretsmanager", region_name=region)
    secret = client.get_secret_value(SecretId=secret_name)
    return json.loads(secret["SecretString"])

secret = get_secret("/secret/db")

DB_URL = (
    f"mysql+pymysql://{secret['DB_USERNAME']}:{secret['DB_PASSWORD']}"
    f"@{secret['DB_HOST']}:{secret['DB_PORT']}/{secret['DB_NAME']}"
)
engine = create_engine(DB_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine)

class Base(DeclarativeBase): pass

# ── 모델 ─────────────────────────────────────────────────
class User(Base):
    __tablename__ = "users"
    id       = Column(Integer, primary_key=True, autoincrement=True)
    email    = Column(String(255), unique=True, nullable=False)
    name     = Column(String(100), nullable=False)
    password = Column(String(255), nullable=False)
    active   = Column(Boolean, default=True)

Base.metadata.create_all(engine)

# ── 스키마 ────────────────────────────────────────────────
class UserCreate(BaseModel):
    email:    EmailStr
    name:     str
    password: str

class UserResponse(BaseModel):
    id:     int
    email:  str
    name:   str
    active: bool
    model_config = {"from_attributes": True}

# ── 앱 & 유틸 ─────────────────────────────────────────────
app = FastAPI(title="WorldPay User API")
pwd = CryptContext(schemes=["bcrypt"])

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# ── 엔드포인트 ────────────────────────────────────────────
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/health/db")
def health_db(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "db": "connected"}
    except Exception as e:
        return {"status": "error", "db": str(e)}

@app.post("/users", response_model=UserResponse, status_code=201)
def create_user(body: UserCreate, db: Session = Depends(get_db)):
    if db.query(User).filter(User.email == body.email).first():
        raise HTTPException(400, "이미 존재하는 이메일입니다.")
    user = User(email=body.email, name=body.name, password=pwd.hash(body.password))
    db.add(user); db.commit(); db.refresh(user)
    return user

@app.get("/users", response_model=list[UserResponse])
def list_users(db: Session = Depends(get_db)):
    return db.query(User).all()

@app.get("/users/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "유저를 찾을 수 없습니다.")
    return user

@app.patch("/users/{user_id}", response_model=UserResponse)
def update_user(user_id: int, name: Optional[str] = None, active: Optional[bool] = None, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "유저를 찾을 수 없습니다.")
    if name   is not None: user.name   = name
    if active is not None: user.active = active
    db.commit(); db.refresh(user)
    return user

@app.delete("/users/{user_id}")
def delete_user(user_id: int, db: Session = Depends(get_db)):
    user = db.get(User, user_id)
    if not user: raise HTTPException(404, "유저를 찾을 수 없습니다.")
    db.delete(user); db.commit()
    return {"message": f"유저 {user_id} 삭제 완료"}
