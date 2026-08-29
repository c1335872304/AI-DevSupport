from __future__ import annotations
import argparse, asyncio, json
from datetime import datetime, timedelta
from sqlalchemy import delete, select
from app.db.models import User, SupportApplication, SupportApiKey, SupportApiCallLog, SupportErrorCode, SupportPlan, SupportSubscription, SupportUsageRecord, SupportInvoice
from app.db.session import SessionLocal

async def seed(username: str, reset: bool=False):
    async with SessionLocal() as db:
        user=await db.scalar(select(User).where(User.username==username))
        if not user: raise SystemExit(f"user not found: {username}")
        uid=str(user.id)
        if reset:
            for model in (SupportInvoice,SupportUsageRecord,SupportSubscription,SupportApiCallLog,SupportApiKey,SupportApplication):
                await db.execute(delete(model).where(model.user_id==uid))
        for row in [
            SupportErrorCode(code="AUTH_KEY_EXPIRED",name="API Key expired",http_status=401,cause="The API Key has expired.",fix_steps="Create/rotate a valid API Key and retry the request."),
            SupportErrorCode(code="AUTH_KEY_INVALID",name="Invalid API Key",http_status=401,cause="The API Key is invalid or disabled.",fix_steps="Verify the masked key identity and use an active key."),
            SupportErrorCode(code="RATE_LIMIT_EXCEEDED",name="Rate limit exceeded",http_status=429,cause="Request rate exceeded the plan QPS limit.",fix_steps="Reduce burst rate, add backoff, or request a higher plan limit."),
        ]:
            if not await db.get(SupportErrorCode,row.code): db.add(row)
        if not await db.get(SupportPlan,"pro"): db.add(SupportPlan(id="pro",name="Professional",qps_limit=50,monthly_quota=1000000,base_price=299.0,overage_price_per_call=0.0005))
        if not await db.get(SupportSubscription,uid): db.add(SupportSubscription(user_id=uid,plan_id="pro",status="ACTIVE"))
        if not await db.get(SupportApplication,"app_demo"): db.add(SupportApplication(id="app_demo",user_id=uid,name="Demo API App",product="OpenAPI"))
        if not await db.get(SupportApiKey,"key_demo"): db.add(SupportApiKey(id="key_demo",app_id="app_demo",user_id=uid,key_masked="ak_****8a2f",status="EXPIRED",expire_at=datetime.utcnow()-timedelta(days=1)))
        if not await db.get(SupportApiCallLog,"req_demo_401"): db.add(SupportApiCallLog(request_id="req_demo_401",user_id=uid,app_id="app_demo",api_key_id="key_demo",endpoint="/v1/chat",http_status=401,error_code="AUTH_KEY_EXPIRED",latency_ms=87,created_at=datetime.utcnow()))
        if not await db.get(SupportApiCallLog,"req_demo_429"): db.add(SupportApiCallLog(request_id="req_demo_429",user_id=uid,app_id="app_demo",api_key_id="key_demo",endpoint="/v1/chat",http_status=429,error_code="RATE_LIMIT_EXCEEDED",latency_ms=44,created_at=datetime.utcnow()))
        if not await db.scalar(select(SupportUsageRecord).where(SupportUsageRecord.user_id==uid,SupportUsageRecord.month=="2026-08")): db.add(SupportUsageRecord(user_id=uid,month="2026-08",call_count=1250000,overage_count=250000))
        if not await db.scalar(select(SupportInvoice).where(SupportInvoice.user_id==uid,SupportInvoice.month=="2026-08")): db.add(SupportInvoice(id=f"inv_{uid}_202608",user_id=uid,month="2026-08",amount=424.0,status="ISSUED",items_json=json.dumps({"baseFee":299.0,"overageFee":125.0})))
        await db.commit()
    print(f"Seeded support demo data for {username}")

if __name__=='__main__':
    ap=argparse.ArgumentParser(); ap.add_argument('--username',default='admin'); ap.add_argument('--reset',action='store_true'); args=ap.parse_args(); asyncio.run(seed(args.username,args.reset))
