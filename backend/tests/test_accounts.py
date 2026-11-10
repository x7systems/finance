"""Account-type behavior shared by the accounts API and financial summaries."""
from datetime import date

from httpx import AsyncClient

from tests.helpers import money, txn_payload


async def test_debit_card_is_a_liquid_account_type(client: AsyncClient, categories):
    response = await client.post(
        "/accounts",
        json={"name": "Debit card", "type": "debit_card", "currency": "RUB"},
    )

    assert response.status_code == 201
    debit_card = response.json()
    assert debit_card["type"] == "debit_card"

    transaction = await client.post(
        "/transactions",
        json=txn_payload(
            debit_card["id"],
            type="income",
            amount="1000.00",
            category_id=categories["Salary"]["id"],
            date=date.today().isoformat(),
        ),
    )
    assert transaction.status_code == 201

    summary = await client.get("/net-worth/summary", params={"range": "all"})

    assert summary.status_code == 200
    assert money(summary.json()["current"]) == money("1000.00")


async def test_account_keeps_its_own_currency(client: AsyncClient):
    """Accounts in different currencies side by side (the reason the account
    form has a currency picker): each keeps its own code, independent of the
    app's primary currency setting."""
    uah = await client.post("/accounts", json={"name": "Hryvnia card", "type": "debit_card", "currency": "UAH"})
    ron = await client.post("/accounts", json={"name": "Lei cash", "type": "cash", "currency": "RON"})

    assert uah.status_code == 201 and uah.json()["currency"] == "UAH"
    assert ron.status_code == 201 and ron.json()["currency"] == "RON"

    listed = {a["name"]: a["currency"] for a in (await client.get("/accounts")).json()}
    assert listed["Hryvnia card"] == "UAH"
    assert listed["Lei cash"] == "RON"


async def test_account_currency_can_be_changed(client: AsyncClient):
    created = await client.post("/accounts", json={"name": "Wallet", "type": "cash", "currency": "USD"})
    account_id = created.json()["id"]

    response = await client.patch(f"/accounts/{account_id}", json={"currency": "RON"})

    assert response.status_code == 200
    assert response.json()["currency"] == "RON"


async def test_account_currency_must_be_an_uppercase_iso_code(client: AsyncClient):
    created = await client.post("/accounts", json={"name": "Wallet", "type": "cash", "currency": "uah"})
    assert created.status_code == 422

    account = await client.post("/accounts", json={"name": "Wallet", "type": "cash", "currency": "UAH"})
    updated = await client.patch(f"/accounts/{account.json()['id']}", json={"currency": "U4H"})
    assert updated.status_code == 422
