"""Optional Stripe boundary: verified raw-body signatures, replay-safe events."""
import hashlib
import hmac
import json
import time
import os
import httpx
from sqlalchemy import select
from gamedev.database import WebhookEvent,Subscription,User,AuditLog


def verify_signature(raw:bytes,signature:str,secret:str,now=None):
    if not secret or len(raw)>500_000:raise ValueError('Webhook unavailable or too large')
    pieces=signature.split(',');stamps=[v.split('=',1)[1] for v in pieces if v.startswith('t=')]
    signatures=[v.split('=',1)[1] for v in pieces if v.startswith('v1=')]
    if len(stamps)!=1:raise ValueError('Invalid webhook signature')
    try:stamp=int(stamps[0])
    except ValueError:raise ValueError('Invalid timestamp') from None
    if abs((time.time() if now is None else now)-stamp)>300:raise ValueError('Expired webhook signature')
    expected=hmac.new(secret.encode(),str(stamp).encode()+b'.'+raw,hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected,value) for value in signatures):raise ValueError('Invalid webhook signature')
    event=json.loads(raw)
    if not isinstance(event,dict) or not isinstance(event.get('id'),str) or len(event['id'])>150:raise ValueError('Invalid webhook event')
    return event


def process_event(db,event):
    with db.session() as session:
        if session.get(WebhookEvent,event['id']):return {'accepted':True,'duplicate':True}
        kind=event.get('type','unknown');obj=event.get('data',{}).get('object',{})
        if kind=='checkout.session.completed' and obj.get('mode')=='subscription' and obj.get('payment_status') in ('paid','no_payment_required'):
            user_id=obj.get('client_reference_id');user=session.get(User,user_id) if user_id else None
            subscription_id=obj.get('subscription')
            if user and subscription_id:
                existing=session.scalar(select(Subscription).where(Subscription.user_id==user.id,Subscription.plan=='pro'))
                if existing:
                    existing.provider_id=subscription_id;existing.status='active'
                else:session.add(Subscription(user_id=user.id,provider_id=subscription_id,status='active',plan='pro'))
        elif kind in ('customer.subscription.updated','customer.subscription.deleted'):
            record=session.scalar(select(Subscription).where(Subscription.provider_id==obj.get('id')))
            if record:record.status='cancelled' if kind.endswith('deleted') else obj.get('status','unknown')
        session.add(WebhookEvent(id=event['id'],kind=kind))
    return {'accepted':True,'duplicate':False}


def checkout(user,origin,request_key):
    key=os.getenv('STRIPE_SECRET_KEY');price=os.getenv('STRIPE_PRICE_ID')
    if not key or not price:raise RuntimeError('Billing is not configured')
    if not origin.startswith('https://'):raise ValueError('Checkout requires an HTTPS application origin')
    with httpx.Client(timeout=20,follow_redirects=False) as client:
        response=client.post('https://api.stripe.com/v1/checkout/sessions',headers={'Authorization':'Bearer '+key,'Idempotency-Key':user.id+':'+request_key},
            data={'mode':'subscription','line_items[0][price]':price,'line_items[0][quantity]':'1','client_reference_id':user.id,
                  'success_url':origin+'/en/account?checkout=returned','cancel_url':origin+'/en/pro'})
        response.raise_for_status();data=response.json()
    url=data.get('url','')
    if not url.startswith('https://checkout.stripe.com/'):raise RuntimeError('Stripe did not return a valid checkout URL')
    return {'url':url}
