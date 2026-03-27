"""Accounts API router for multi-account management."""

from typing import List
from fastapi import APIRouter, HTTPException

from api.dependencies import AccountServiceDep
from api.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountListItem,
    AccountCredentials,
)
from api.schemas.common import create_success_response
from core.exceptions import ResourceNotFoundError

router = APIRouter()


@router.get("", response_model=dict)
async def list_accounts(account_service: AccountServiceDep):
    """List all accounts."""
    accounts = await account_service.list_accounts()
    return create_success_response(data=[AccountListItem.model_validate(a) for a in accounts])


@router.post("", response_model=dict)
async def create_account(body: AccountCreate, account_service: AccountServiceDep):
    """Create a new account."""
    account = await account_service.create_account(
        name=body.name,
        phpsessid=body.phpsessid,
        user_agent=body.user_agent,
    )
    return create_success_response(data=AccountResponse.model_validate(account))


@router.get("/{account_id}", response_model=dict)
async def get_account(account_id: int, account_service: AccountServiceDep):
    """Get a single account by ID."""
    try:
        account = await account_service.get_account(account_id)
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.put("/{account_id}", response_model=dict)
async def update_account(
    account_id: int, body: AccountUpdate, account_service: AccountServiceDep
):
    """Update account settings."""
    try:
        updates = body.model_dump(exclude_none=True)
        account = await account_service.update_account(account_id, **updates)
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{account_id}", response_model=dict)
async def delete_account(account_id: int, account_service: AccountServiceDep):
    """Soft-delete an account (marks inactive). Cannot delete the last account."""
    from workers.scheduler import scheduler_manager

    try:
        success = await account_service.delete_account(account_id)
        if not success:
            raise HTTPException(status_code=400, detail="Cannot delete the last active account")
        # Stop any running automation jobs for this account
        scheduler_manager.remove_job(f"automation_cycle_{account_id}")
        scheduler_manager.remove_job(f"safety_check_{account_id}")
        return create_success_response(data={"deleted": True})
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/credentials", response_model=dict)
async def set_credentials(
    account_id: int, body: AccountCredentials, account_service: AccountServiceDep
):
    """Set SteamGifts credentials for an account."""
    try:
        account = await account_service.set_credentials(
            account_id, phpsessid=body.phpsessid, user_agent=body.user_agent
        )
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))


@router.delete("/{account_id}/credentials", response_model=dict)
async def clear_credentials(account_id: int, account_service: AccountServiceDep):
    """Clear SteamGifts credentials for an account."""
    try:
        account = await account_service.clear_credentials(account_id)
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/test-session", response_model=dict)
async def test_session(account_id: int, account_service: AccountServiceDep):
    """Test if the account's PHPSESSID is valid."""
    try:
        result = await account_service.test_session(account_id)
        return create_success_response(data=result)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/validate", response_model=dict)
async def validate_configuration(account_id: int, account_service: AccountServiceDep):
    """Validate an account's configuration."""
    try:
        result = await account_service.validate_configuration(account_id)
        return create_success_response(data=result)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/reset", response_model=dict)
async def reset_account(account_id: int, account_service: AccountServiceDep):
    """Reset automation settings to defaults (keeps credentials)."""
    try:
        account = await account_service.reset_to_defaults(account_id)
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.post("/{account_id}/set-default", response_model=dict)
async def set_default_account(account_id: int, account_service: AccountServiceDep):
    """Set this account as the default."""
    try:
        account = await account_service.set_default(account_id)
        return create_success_response(data=AccountResponse.model_validate(account))
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/{account_id}/scheduler/status", response_model=dict)
async def get_account_scheduler_status(account_id: int, account_service: AccountServiceDep):
    """Get scheduler status for a specific account."""
    from workers.scheduler import scheduler_manager

    try:
        account = await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    account_job_ids = {f"automation_cycle_{account_id}", f"safety_check_{account_id}", f"win_check_{account_id}"}
    account_jobs = [j for j in scheduler_manager.get_jobs() if j.id in account_job_ids]

    job_info = []
    for job in account_jobs:
        next_run = job.next_run_time
        job_info.append({
            "id": job.id,
            "name": job.name,
            "next_run": next_run.isoformat() if next_run else None,
            "trigger": str(job.trigger),
        })

    return create_success_response(data={
        "running": account.automation_enabled and len(account_jobs) > 0,
        "paused": scheduler_manager.is_paused,
        "job_count": len(account_jobs),
        "jobs": job_info,
    })


@router.post("/{account_id}/scheduler/start", response_model=dict)
async def start_account_automation(account_id: int, account_service: AccountServiceDep):
    """Start automation for a specific account."""
    from functools import partial
    from workers.scheduler import scheduler_manager
    from workers.automation import automation_cycle
    from workers.safety_checker import safety_check_cycle

    try:
        account = await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    if not account.phpsessid:
        raise HTTPException(status_code=400, detail="Account has no credentials configured")

    # Enable automation in DB
    await account_service.update_account(account_id, automation_enabled=True)

    scheduler_manager.start()
    scan_interval = account.scan_interval_minutes or 30

    # Stagger start times: each additional account gets a 5-minute offset
    # to prevent simultaneous scans from the same IP.
    from datetime import datetime, timedelta, UTC
    running_automation_jobs = [
        j for j in scheduler_manager.get_jobs()
        if j.id.startswith("automation_cycle_") and j.id != f"automation_cycle_{account_id}"
    ]
    offset_minutes = len(running_automation_jobs) * 5
    start_date = datetime.now(UTC) + timedelta(minutes=offset_minutes)

    scheduler_manager.add_interval_job(
        func=partial(automation_cycle, account_id=account_id),
        job_id=f"automation_cycle_{account_id}",
        minutes=scan_interval,
        start_date=start_date,
        name="Automation cycle",
    )

    if account.safety_check_enabled:
        scheduler_manager.add_interval_job(
            func=partial(safety_check_cycle, account_id=account_id),
            job_id=f"safety_check_{account_id}",
            seconds=45,
            name="Safety check",
        )

    return create_success_response(data={"started": True, "account_id": account_id})


@router.post("/{account_id}/scheduler/stop", response_model=dict)
async def stop_account_automation(account_id: int, account_service: AccountServiceDep):
    """Stop automation for a specific account."""
    from workers.scheduler import scheduler_manager

    try:
        await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    # Disable automation in DB
    await account_service.update_account(account_id, automation_enabled=False)

    scheduler_manager.remove_job(f"automation_cycle_{account_id}")
    scheduler_manager.remove_job(f"safety_check_{account_id}")

    return create_success_response(data={"stopped": True, "account_id": account_id})


@router.post("/{account_id}/scheduler/run", response_model=dict)
async def run_account_cycle(account_id: int, account_service: AccountServiceDep):
    """Manually trigger one automation cycle for a specific account."""
    from workers.automation import automation_cycle

    try:
        await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = await automation_cycle(account_id=account_id)
    return create_success_response(data=results)


@router.post("/{account_id}/scheduler/scan", response_model=dict)
async def scan_account(account_id: int, account_service: AccountServiceDep):
    """Manually trigger a giveaway scan for a specific account."""
    from workers.scanner import scan_giveaways

    try:
        await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = await scan_giveaways(account_id=account_id)
    return create_success_response(data=results)


@router.post("/{account_id}/scheduler/process", response_model=dict)
async def process_account(account_id: int, account_service: AccountServiceDep):
    """Manually trigger giveaway processing for a specific account."""
    from workers.processor import process_giveaways

    try:
        await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = await process_giveaways(account_id=account_id)
    return create_success_response(data=results)


@router.post("/{account_id}/scheduler/sync-wins", response_model=dict)
async def sync_account_wins(account_id: int, account_service: AccountServiceDep):
    """Manually trigger win sync for a specific account."""
    from workers.automation import sync_wins_only

    try:
        await account_service.get_account(account_id)
    except ResourceNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))

    results = await sync_wins_only(account_id=account_id)
    return create_success_response(data=results)
