"""Protected owner projections, explicit approvals and role-scoped mutations."""

import hmac
import secrets
from pathlib import Path
from typing import cast

from fastapi import APIRouter, Depends, Form, Request
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates

from core.canonical import Json
from core.models import ChildProposal, ExecutionProposal, RootProposal
from services.authorization import DOCUMENTS, Denied, Runtime
from services.exporter import export_pack
from simulated_agents.executor import propose as execution_proposal
from simulated_agents.orchestrator import propose as child_proposal

router = APIRouter()
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")


def runtime(request: Request) -> Runtime:
    """Resolve the isolated application runtime."""
    return cast(Runtime, request.app.state.runtime)


def authenticated(request: Request, rt: Runtime = Depends(runtime)) -> str:
    """Check credentials, origin and CSRF for cookie-authenticated mutations."""
    authorization = request.headers.get("Authorization", "")
    bearer = authorization.startswith("Bearer ")
    token = authorization[7:] if bearer else request.cookies.get("ledger_session", "")
    role = rt.principal(token)
    if not bearer and request.method not in ("GET", "HEAD"):
        supplied = request.headers.get("X-CSRF-Token", "")
        cookie = request.cookies.get("ledger_csrf", "")
        if (
            not supplied
            or not cookie
            or (not hmac.compare_digest(cookie, supplied))
            or (request.headers.get("Origin") != request.app.state.origin)
        ):
            raise Denied("CSRF_REJECTED")
    return role


def owner(role: str = Depends(authenticated)) -> str:
    """Require the owner for reads, approvals, revocations and exports."""
    if role != "owner":
        raise Denied("WRONG_ACTOR")
    return role


@router.get("/health")
def health() -> Json:
    """Expose liveness only, without case data."""
    return {"status": "ok", "mode": "synthetic"}


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request) -> Response:
    """Render a local demo credential prompt without any embedded credentials."""
    return templates.TemplateResponse(request, "login.html", {})


@router.post("/login")
def login(request: Request, token: str = Form(...), rt: Runtime = Depends(runtime)) -> Response:
    """Exchange a provisioned owner credential for a restricted local demo cookie."""
    if request.headers.get("Origin") != request.app.state.origin:
        raise Denied("CSRF_REJECTED")
    if rt.principal(token) != "owner":
        raise Denied("WRONG_ACTOR")
    response = RedirectResponse("/", status_code=303)
    secure = request.url.scheme == "https"
    response.set_cookie("ledger_session", token, httponly=True, samesite="strict", secure=secure)
    response.set_cookie(
        "ledger_csrf", secrets.token_urlsafe(32), httponly=True, samesite="strict", secure=secure
    )
    return response


@router.get("/", response_class=HTMLResponse, dependencies=[Depends(owner)])
def dashboard(request: Request, rt: Runtime = Depends(runtime)) -> Response:
    """Render the three canonical views of the same durable case."""
    state = rt.state()
    csrf = request.cookies.get("ledger_csrf", "")
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {"state": state, "csrf": csrf, "request_id": secrets.token_urlsafe(16)},
    )


@router.get("/api/state", dependencies=[Depends(owner)])
def state(rt: Runtime = Depends(runtime)) -> Json:
    """Read owner-only state and actual isolated receiver messages."""
    return rt.state()


@router.post("/api/roots", dependencies=[Depends(owner)])
def approve(proposal: RootProposal, rt: Runtime = Depends(runtime)) -> Json:
    """Approve the exact document and bounded scope."""
    return rt.approve(proposal)


@router.post("/api/children")
def delegate(
    proposal: ChildProposal, role: str = Depends(authenticated), rt: Runtime = Depends(runtime)
) -> Json:
    """Authenticate the orchestrator independently from the untrusted proposal."""
    return rt.delegate(role, proposal)


@router.post("/api/execute")
def execute(
    proposal: ExecutionProposal, role: str = Depends(authenticated), rt: Runtime = Depends(runtime)
) -> Json:
    """Accept only the signed child's authenticated executor."""
    return rt.execute(role, proposal)


@router.post("/api/roots/{root_id}/revoke", dependencies=[Depends(owner)])
def revoke(root_id: str, rt: Runtime = Depends(runtime)) -> Json:
    """Revoke future reservations without claiming cancellation of past dispatch."""
    return rt.revoke(root_id)


@router.post("/api/attempts/{attempt_id}/reconcile", dependencies=[Depends(owner)])
def reconcile(attempt_id: str, rt: Runtime = Depends(runtime)) -> Json:
    """Read an existing receipt; never retry an external effect."""
    return rt.reconcile(attempt_id)


@router.get("/api/export", dependencies=[Depends(owner)])
def export(rt: Runtime = Depends(runtime)) -> Response:
    """Download signed evidence; private keys and credentials are excluded."""
    return Response(
        export_pack(rt),
        media_type="application/zip",
        headers={"Content-Disposition": 'attachment; filename="evidence.zip"'},
    )


@router.post("/api/demo/delegate/{root_id}/{executor_id}", dependencies=[Depends(owner)])
def scripted_delegate(
    root_id: str, executor_id: str, request: Request, rt: Runtime = Depends(runtime)
) -> Json:
    """Owner explicitly triggers a clearly labeled scripted A proposal."""
    with rt.store.connection() as db:
        record = rt.store.get(db, "root", root_id)
    if record is None:
        raise Denied("INVALID_INPUT", 404)
    recipient = "Mallory" if request.query_params.get("attack") == "scope" else "Anna"
    return rt.delegate(
        "A",
        child_proposal(
            cast(Json, cast(Json, record["envelope"])["payload"]), executor_id, recipient
        ),
    )


@router.post("/api/demo/execute/{child_id}", dependencies=[Depends(owner)])
def scripted_execute(child_id: str, request: Request, rt: Runtime = Depends(runtime)) -> Json:
    """Owner triggers the simulated executor bound to the signed child."""
    with rt.store.connection() as db:
        signed = rt.store.get(db, "child", child_id)
    if signed is None:
        raise Denied("INVALID_INPUT", 404)
    child = cast(Json, signed["payload"])
    document_id = next(
        (
            key
            for key, value in DOCUMENTS.items()
            if value["snapshot_hash"] == cast(str, child["snapshot_hash"])
        )
    )
    if request.query_params.get("attack") == "document":
        document_id = "doc-v1" if document_id == "doc-v2" else "doc-v2"
    return rt.execute(cast(str, child["executor_id"]), execution_proposal(child, document_id))
