from fastapi import APIRouter

from gateway_service.api.product_service import category, product

api_router = APIRouter(prefix="/product_service")

api_router.include_router(category.router, prefix='/categories', tags=["categories"])
api_router.include_router(product.router, prefix='/products', tags=["products"])