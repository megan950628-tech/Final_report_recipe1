from fastapi import FastAPI, Query
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Optional
from fastapi.middleware.cors import CORSMiddleware
import random
import json
import os
from database import load_recipes

app = FastAPI(
    title="食譜查詢 API",
    version="2.2.0",
    description="支援分類、複選食材、模糊搜尋，並提供收藏功能的食譜 API"
)


# =========================
# 載入食譜資料
# =========================
recipes = load_recipes()

# =========================
# 收藏功能（JSON 儲存）
# =========================
FAVORITE_FILE = "favorites.json"


def load_favorites():
    if not os.path.exists(FAVORITE_FILE):
        return set()
    with open(FAVORITE_FILE, "r", encoding="utf-8") as f:
        return set(json.load(f))


def save_favorites(favorites: set):
    with open(FAVORITE_FILE, "w", encoding="utf-8") as f:
        json.dump(list(favorites), f, ensure_ascii=False, indent=2)


favorites = load_favorites()

# =========================
# 首頁
# =========================
@app.get("/")
def root():
    return {"message": "歡迎使用強化版食譜查詢 API！（含收藏功能）"}


# =========================
# 搜尋功能（原本功能）
# =========================
@app.get(
    "/search",
    summary="依分類＋多食材（支援模糊）搜尋食譜",
    description=(
        "📌 **使用說明：**\n"
        "- 可同時選擇「分類」＋「多個食材」\n"
        "- 食材支援 **模糊搜尋**（例：輸入「飯」可找到「白飯」）\n\n"
        "📌 **甜點食材可選：**\n"
        "🍓 水果：草莓、香蕉、蘋果、芒果、酪梨、藍莓、地瓜、南瓜\n"
        "🥛 乳製品：鮮奶、豆漿、優格、乳酪\n"
        "🥚 蛋類：雞蛋、蛋黃\n"
        "🍯 甜味：蜂蜜、砂糖、黑糖、冰糖、楓糖漿\n"
        "🍫 烘焙：可可粉、巧克力豆、肉桂粉、泡打粉、吉利丁\n"
        "🥣 穀類：燕麥、紫米、糯米粉、低筋、中筋、餅乾\n"
        "🥑 豆類：豆腐、豆渣、紅豆\n\n"
        "📌 **家常菜食材可選：**\n"
        "🥬 蔬菜：蔥、蒜、洋蔥、青江菜、番茄\n"
        "🥩 肉類：雞肉、豬肉、牛肉、絞肉\n"
        "🐟 海鮮：蝦、魚肉、鮪魚罐頭\n"
        "🍳 基礎：雞蛋、醬油、鹽、糖、油\n"
        "🍚 主食：白飯、麵條、米粉\n"
    )
)
def search_recipes(
    category: Optional[str] = Query(
        None,
        description="分類：dessert（甜點） 或 home（家常菜）"
    ),
    ingredient: Optional[List[str]] = Query(
        None,
        description="可輸入多個食材，如：?ingredient=飯&ingredient=蛋"
    )
):
    result = recipes
    fuzzy_hit_count = 0

    # 1️⃣ 分類篩選
    if category:
        # 定義對照表：讓 home 也能對應到 中文「家常菜」
        category_map = {
            "home": ["home", "家常菜"],
            "dessert": ["dessert", "甜點"]
        }
        
        target_tags = category_map.get(category.lower(), [category])
        
        # 只要資料庫裡的 category 屬於 target_tags 其中之一，就留下來
        result = [
            r for r in result 
            if str(r.get("category")).lower() in target_tags
        ]

    # 2️⃣ 多食材 + 模糊搜尋
    if ingredient:
        filtered = []

        for recipe in result:
            matched_all = True
            local_hit = 0

            for q in ingredient:
                if any(q in ing for ing in recipe["ingredients"]):
                    local_hit += 1
                else:
                    matched_all = False
                    break

            if matched_all:
                # ⭐ 加上是否已收藏（加分）
                recipe_copy = recipe.copy()
                recipe_copy["is_favorite"] = recipe["name"] in favorites

                filtered.append(recipe_copy)
                fuzzy_hit_count += local_hit

        result = filtered
    else:
        # 沒搜尋條件時也標示是否收藏
        result = [
            {**r, "is_favorite": r["name"] in favorites}
            for r in result
        ]

    return {
        "category": category,
        "ingredients_query": ingredient,
        "fuzzy_match_count": fuzzy_hit_count,
        "count": len(result),
        "results": result
    }


# =========================
# 其他原本 API
# =========================
@app.get("/list", summary="列出全部食譜")
def list_recipes():
    return {
        "count": len(recipes),
        "recipes": [
            {**r, "is_favorite": r["name"] in favorites}
            for r in recipes
        ]
    }


@app.get("/random", summary="隨機推薦一道食譜")
def random_recipe():
    recipe = random.choice(recipes)
    return {**recipe, "is_favorite": recipe["name"] in favorites}


@app.get("/detail", summary="依完整名稱查詢食譜")
def recipe_detail(
    name: str = Query(..., description="請輸入完整食譜名稱")
):
    for r in recipes:
        if r["name"] == name:
            return {**r, "is_favorite": name in favorites}
    return {"error": f"找不到名為 {name} 的食譜"}


# =========================
# 收藏 API（新增）
# =========================
@app.post("/favorite", summary="收藏一份食譜")
def add_favorite(
    name: str = Query(..., description="要收藏的食譜名稱")
):
    for r in recipes:
        if r["name"] == name:
            favorites.add(name)
            save_favorites(favorites)
            return {
                "message": f"已收藏：{name}",
                "favorites_count": len(favorites)
            }

    return {"error": f"找不到名為 {name} 的食譜"}


@app.get("/favorite", summary="查看收藏的食譜")
def list_favorites():
    result = [r for r in recipes if r["name"] in favorites]
    return {
        "count": len(result),
        "favorites": result
    }


@app.delete("/favorite", summary="取消收藏")
def remove_favorite(
    name: str = Query(..., description="要取消收藏的食譜名稱")
):
    if name in favorites:
        favorites.remove(name)
        save_favorites(favorites)
        return {"message": f"已取消收藏：{name}"}

<<<<<<< HEAD
    return {"error": f"{name} 不在收藏清單中"}
=======
    return {"error": f"{name} 不在收藏清單中"}
>>>>>>> 5320946 (Front-end)
