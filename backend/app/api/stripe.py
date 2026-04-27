import os
import stripe
from fastapi import APIRouter, HTTPException, Depends, Request, Header
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from app.db.session import get_db
from app.db.models import User
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)

router = APIRouter()
stripe.api_key = settings.STRIPE_SECRET_KEY
webhook_secret = settings.STRIPE_WEBHOOK_SECRET

@router.post("/checkout-session")
async def create_checkout_session(payload: dict):
    user_email = payload.get("email")
    # In real app verify user identity via token/session
    stripe_price_id = settings.STRIPE_PRICE_ID

    if not stripe_price_id:
        raise HTTPException(status_code=500, detail="Missing STRIPE_PRICE_ID configuration")
    
    try:
        session = stripe.checkout.Session.create(
            customer_email=user_email,
            payment_method_types=['card'],
            line_items=[{
                'price': stripe_price_id,
                'quantity': 1,
            }],
            mode='subscription',
            allow_promotion_codes=True, # Enables users to enter your ENDSEASON coupon
            # Use configurable FRONTEND_URL instead of hardcoded localhost
            success_url=f'{settings.FRONTEND_URL}?success=true',
            cancel_url=f'{settings.FRONTEND_URL}?canceled=true',
        )
        return {"url": session.url}
    except Exception as e:
        logger.exception("Stripe checkout failed")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/webhook")
async def stripe_webhook(request: Request, stripe_signature: str = Header(None), db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    
    try:
        if webhook_secret:
            event = stripe.Webhook.construct_event(
                payload, stripe_signature, webhook_secret
            )
        else:
            # If no secret (dev mode), just parse JSON but warn
            # THIS IS INSECURE FOR PROD
            import json
            event = json.loads(payload)
            
    except ValueError as e:
        # Invalid payload
        raise HTTPException(status_code=400, detail="Invalid payload")
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        raise HTTPException(status_code=400, detail="Invalid signature")

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        customer_email = session.get('customer_email') or session.get('customer_details', {}).get('email')
        stripe_customer_id = session.get('customer')
        
        if customer_email:
            # Update user in DB
            result = await db.execute(select(User).where(User.email == customer_email))
            user = result.scalars().first()
            
            if user:
                user.subscription_status = "active"
                user.stripe_customer_id = stripe_customer_id
                await db.commit()
                logger.info(f"Subscription activated for {customer_email}")
            else:
                logger.warning(f"User {customer_email} not found for subscription activation")
        else:
            logger.warning("No email found in Stripe session")

    return {"status": "success"}


@router.post("/customer-portal")
async def create_customer_portal(payload: dict, db: AsyncSession = Depends(get_db)):
    user_email = payload.get("email")
    if not user_email:
        raise HTTPException(status_code=400, detail="Missing email")

    result = await db.execute(select(User).where(User.email == user_email))
    user = result.scalars().first()
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    customer_id = user.stripe_customer_id
    if not customer_id:
        # Fallback lookup by email if webhook has not yet populated the customer id.
        customers = stripe.Customer.list(email=user_email, limit=1)
        if customers.data:
            customer_id = customers.data[0].id
            user.stripe_customer_id = customer_id
            await db.commit()
        else:
            raise HTTPException(status_code=400, detail="No Stripe customer found for this email")

    try:
        session = stripe.billing_portal.Session.create(
            customer=customer_id,
            return_url=settings.FRONTEND_URL,
        )
        return {"url": session.url}
    except Exception as e:
        logger.exception("Stripe billing portal failed")
        raise HTTPException(status_code=500, detail=str(e))
