from pathlib import Path

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.staticfiles import StaticFiles
from starlette.templating import Jinja2Templates

from auth_service.api.api_v1.api import api_router
from auth_service.api.errors.http_error import http_error_handler
from auth_service.api.errors.validation_error import http422_error_handler
from auth_service.api.openapi import custom_openapi
from auth_service.api.openapi import use_route_names_as_operation_ids
from auth_service.core.config import get_app_settings
from auth_service.db.init_db import init_db
from auth_service.db.session import SessionLocal, engine
from auth_service.middlewares.http import (
    add_process_time_header,
    catch_exceptions_middleware,
)

current_file = Path(__file__)
current_file_dir = current_file.parent
project_root = current_file_dir.parent
project_root_absolute = project_root.resolve()
project_templates_path = project_root_absolute / "auth_service/templates"
project_templates_html_path = project_templates_path / "html/"

templates = Jinja2Templates(directory=project_templates_html_path)


def get_application() -> FastAPI:
    get_app_settings().configure_logging()

    application = FastAPI(**get_app_settings().fastapi_kwargs)

    application.include_router(api_router, prefix=get_app_settings().api_v1)
    custom_openapi(application)
    use_route_names_as_operation_ids(application)

    application.add_exception_handler(HTTPException, http_error_handler)
    application.add_exception_handler(
        RequestValidationError, http422_error_handler
    )

    application.add_middleware(
        CORSMiddleware,
        allow_origins=get_app_settings().BACKEND_CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        expose_headers=["Content-Range", "Range"],
        allow_headers=[
            "*",
            "Authorization",
            "Content-Type",
            "Content-Range",
            "Range",
        ],
    )

    if get_app_settings().APP_ENV in ["dev", "test"]:
        application.middleware("http")(add_process_time_header)

    if not application.debug and get_app_settings().APP_ENV == "prod":
        application.middleware("http")(catch_exceptions_middleware)

    application.mount(
        "/templates",
        StaticFiles(directory=project_templates_path),
        name="templates",
    )

    return application


app = get_application()


@app.on_event("startup")
async def startup():
    if get_app_settings().APP_ENV.name == "dev":
        await init_db()


@app.on_event("shutdown")
async def shutdown():
    await SessionLocal.close_all()
    await engine.dispose()


@app.get("/")
async def root(request: Request):
    response = templates.TemplateResponse(
        "index.html",
        context={
            "app_name": app.title.replace("_", " "),
            "request": request,
            "proto": "http",
            "host": get_app_settings().DOMAIN,
            "port": get_app_settings().PORT,
            "openapi_path": f"{app.openapi_url}",
        },
    )
    return response