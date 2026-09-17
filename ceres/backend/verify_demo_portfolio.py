"""Read-only integration check against the seeded DB using isolated ASGI routes.

The test app resolves a known operator-selected membership; it never creates a
session, changes the running API's authentication, or writes customer data.
"""
import argparse
import asyncio
import json
import logging
from pathlib import Path
from uuid import uuid4

import httpx

from backend.api.main import create_app
from backend.api.dependencies import get_current_principal, get_control_plane_service, get_tenant_data_repository
from backend.repositories.tenant_data import TenantContext
from backend.services.errors import NotFoundError
from backend.seed_demo_portfolio import DEMO_SOURCE


async def verify(email: str, output: Path):
    service = get_control_plane_service()
    repository = get_tenant_data_repository()
    try:
        pool = await service._database()
        rows = await pool.fetch("""SELECT u.id::text, m.organization_id::text, m.role FROM cloud_users u
                                 JOIN organization_memberships m ON m.user_id=u.id WHERE lower(u.email)=lower($1)""", email)
        if len(rows) != 1:
            raise ValueError("Ambiguous target membership")
        principal = dict(rows[0])
        context = TenantContext.from_principal(principal)
        portfolios = await repository.list_portfolios(context)
        demo = next(p for p in portfolios if p['name'].startswith('Demonstração Ceres'))
        estates = await repository.list_estates(context)
        assert len(estates) >= 12
        a, b = [e['id'] for e in estates[:2]]
        foreign = TenantContext(str(uuid4()), str(uuid4()), 'user')
        for operation in [repository.get_estate(foreign, a), repository.get_portfolio(foreign, demo['id'])]:
            try:
                await operation
            except NotFoundError:
                pass
            else:
                raise AssertionError("Cross-tenant data was returned")
        app = create_app()
        app.dependency_overrides[get_current_principal] = lambda: principal
        snapshot = {'/auth/session': {'user': {**principal, 'full_name': 'Demonstração Ceres', 'email': 'demo@example.test'}}}
        paths = ['/portfolios', '/analytics/estates', f"/portfolios/{demo['id']}/overview",
                 f'/estates/{a}', f'/estates/{a}/comparison', f'/estates/{a}/analysis',
                 f'/analytics/estate-pair?a_id={a}&b_id={b}', '/market/regions', '/market/heatmap', '/market/published-metrics']
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            for path in paths:
                response = await client.get('/api/v1'+path)
                body = response.json()
                assert response.status_code == 200, (path, response.status_code, body)
                snapshot[path] = body
                print(json.dumps({'path':path,'status':response.status_code,'components': body.get('timing',{}).get('components',[]) if isinstance(body,dict) else []}), flush=True)
        assert len(snapshot['/market/heatmap']['cells']) >= 1
        assert snapshot[f"/portfolios/{demo['id']}/overview"]['valuation_summary']['active_estate_count'] == 12
        async with repository.transaction(context) as connection:
            count = await connection.fetchval("SELECT count(*) FROM estates WHERE organization_id=$1 AND source_name=$2",context.organization_id,DEMO_SOURCE)
            assert count == 12
        output.parent.mkdir(parents=True,exist_ok=True)
        output.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2),encoding='utf-8')
        print(json.dumps({'cross_tenant':'pass','demo_estate_count':count,'snapshot':str(output)}),flush=True)
    finally:
        await service.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--email',required=True)
    parser.add_argument('--output',required=True,type=Path)
    args=parser.parse_args()
    logging.disable(logging.INFO)
    asyncio.run(verify(args.email,args.output))
