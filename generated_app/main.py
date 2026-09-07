import os
import uuid
from typing import List, Optional
from fastapi import FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field
from dotenv import load_dotenv
from motor.motor_asyncio import AsyncIOMotorClient

load_dotenv()

MONGO_URI = os.getenv("MONGO_URI", "mongodb://localhost:27017")
DB_NAME = os.getenv("DB_NAME", "homedone_db")

client = AsyncIOMotorClient(MONGO_URI)
db = client[DB_NAME]
collection = db["inventory_items"]

app = FastAPI(title="Inventory Management API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ItemBase(BaseModel):
    name: str = Field(..., min_length=1, description="Name of the inventory item")
    quantity: int = Field(..., ge=0, description="Quantity in stock")
    price: float = Field(..., ge=0.0, description="Price per unit")
    category: Optional[str] = Field("General", description="Category of the item")

class Item(ItemBase):
    id: str

@app.get("/")
async def read_index():
    return FileResponse("index.html")

@app.get("/api/items", response_model=List[Item])
async def get_items():
    items = await collection.find({}, {"_id": 0}).to_list(length=1000)
    return items

@app.post("/api/items", response_model=Item, status_code=status.HTTP_201_CREATED)
async def add_item(item: ItemBase):
    item_id = str(uuid.uuid4())
    new_item = Item(id=item_id, **item.model_dump())
    
    # Save directly to MongoDB Compass
    await collection.insert_one(new_item.dict())
    return new_item

@app.delete("/api/items/{item_id}", status_code=status.HTTP_200_OK)
async def delete_item(item_id: str):
    item_to_delete = await collection.find_one({"id": item_id}, {"_id": 0})
    if not item_to_delete:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Item not found"
        )
    
    await collection.delete_one({"id": item_id})
    return {"message": f"Item '{item_to_delete['name']}' deleted successfully", "id": item_id}