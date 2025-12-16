from fastapi import FastAPI
import json
from pathlib import Path

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent

with open(BASE_DIR / "data" / "recipes.json", "r", encoding="utf-8") as f:
    RECIPES = json.load(f)

@app.get("/")
def root():
    return {"message": "食譜查詢 API 已啟動 🍳"}

@app.get("/search")
def search_recipe(ingredient: str):
    results = []
    for r in RECIPES:
        if ingredient in r["ingredients"]:
            results.append(r)

    return {
        "query": ingredient,
        "count": len(results),
        "results": results
    }
