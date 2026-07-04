"""Unit tests for AccountService.

Regression coverage for a bug where get_account()/set_default() raised
ResourceNotFoundError without the required `code` argument, causing a
TypeError instead of the intended 404.
"""

import pytest

from core.exceptions import ResourceNotFoundError
from services.account_service import AccountService


@pytest.mark.asyncio
async def test_get_account_not_found_raises_resource_not_found_error(async_session):
    service = AccountService(async_session)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.get_account(999)

    assert exc_info.value.code == "ACCT_001"


@pytest.mark.asyncio
async def test_set_default_not_found_raises_resource_not_found_error(async_session):
    service = AccountService(async_session)

    with pytest.raises(ResourceNotFoundError) as exc_info:
        await service.set_default(999)

    assert exc_info.value.code == "ACCT_001"


@pytest.mark.asyncio
async def test_get_account_returns_existing_account(async_session):
    service = AccountService(async_session)
    created = await service.create_account(name="Test Account")

    fetched = await service.get_account(created.id)

    assert fetched.id == created.id
    assert fetched.name == "Test Account"
