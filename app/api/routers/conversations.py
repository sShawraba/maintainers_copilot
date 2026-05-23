from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from datetime import datetime
import json

from app.api.routers.auth import current_active_user
from app.db.models import User
from app.infra.redis_client import redis_client

router = APIRouter(prefix="/conversations", tags=["conversations"])

class ConversationMeta(BaseModel):
    conversation_id: str
    title: str
    last_updated: str

class ConversationDetail(BaseModel):
    conversation_id: str
    title: str
    messages: List[dict]

def get_user_conv_set_key(user_id: str) -> str:
    return f"user:{user_id}:conversations"

def get_conv_meta_key(conv_id: str) -> str:
    return f"conv_meta:{conv_id}"

def get_conv_messages_key(conv_id: str) -> str:
    return f"conv:{conv_id}"

@router.get("/", response_model=List[ConversationMeta])
async def list_conversations(user: User = Depends(current_active_user)):
    user_id = str(user.id)
    conv_set_key = get_user_conv_set_key(user_id)
    conv_ids = redis_client.smembers(conv_set_key)
    conv_ids = [cid.decode() if isinstance(cid, bytes) else cid for cid in conv_ids]
    
    metas = []
    for cid in conv_ids:
        meta_key = get_conv_meta_key(cid)
        meta = redis_client.hgetall(meta_key)
        if meta:
            title = meta.get(b"title", meta.get("title", "Untitled"))
            if isinstance(title, bytes):
                title = title.decode()
            last_updated = meta.get(b"last_updated", meta.get("last_updated", ""))
            if isinstance(last_updated, bytes):
                last_updated = last_updated.decode()
            metas.append(ConversationMeta(
                conversation_id=cid,
                title=title,
                last_updated=last_updated
            ))
    metas.sort(key=lambda x: x.last_updated, reverse=True)
    return metas

@router.get("/{conversation_id}", response_model=ConversationDetail)
async def get_conversation(conversation_id: str, user: User = Depends(current_active_user)):
    user_id = str(user.id)
    conv_set_key = get_user_conv_set_key(user_id)
    if not redis_client.sismember(conv_set_key, conversation_id):
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    messages_key = get_conv_messages_key(conversation_id)
    raw = redis_client.get(messages_key)
    if raw:
        if isinstance(raw, bytes):
            raw = raw.decode()
        messages = json.loads(raw)
    else:
        messages = []
    
    meta_key = get_conv_meta_key(conversation_id)
    meta = redis_client.hgetall(meta_key)
    title = meta.get(b"title", meta.get("title", "Untitled"))
    if isinstance(title, bytes):
        title = title.decode()
    
    return ConversationDetail(
        conversation_id=conversation_id,
        title=title,
        messages=messages
    )