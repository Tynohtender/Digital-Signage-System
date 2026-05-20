from sqlalchemy import Column, Integer, String, ForeignKey
from database import Base


class Client(Base):
    __tablename__ = "clients"

    id = Column(Integer, primary_key=True, index=True)
    business_name = Column(String)
    slug = Column(String, unique=True, index=True)  # ✅ REQUIRED

class Menu(Base):
    __tablename__ = "menus"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String)
    price = Column(String)
    image = Column(String)
    client_id = Column(Integer, ForeignKey("clients.id"))


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True)
    password = Column(String)
    role = Column(String, default="client")  # "admin" or "client"
    client_id = Column(Integer, ForeignKey("clients.id"))
    