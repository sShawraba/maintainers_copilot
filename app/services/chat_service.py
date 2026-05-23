# app/services/chat_service.py
import datetime
from datetime import datetime
from email.mime import message
import os
import json
from typing import List, Dict, Any
from groq import Groq
from app.services.rag_service import RAGService
from app.repositories.memory_repository import MemoryRepository
from app.db.session import SyncSessionLocal
from app.model_loader import dense_model, reranker   # already loaded once

class ChatService:
    def __init__(self):
        self.groq = Groq(api_key=os.getenv("GROQ_API_KEY"))
        self.model = "llama-3.3-70b-versatile"

    def _get_tools(self) -> List[Dict]:
        return [
            {
                "type": "function",
                "function": {
                    "name": "retrieve_docs",
                    "description": "Search documentation or resolved issues. Keep the query very short (max 10 words).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Short search query, e.g. 'drop NaN values' or 'filter rows'"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "classify_issue",
                    "description": "Classify an issue as bug, feature, docs, or question",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "body": {"type": "string"}
                        },
                        "required": ["title", "body"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "write_memory",
                    "description": "Store a short fact into long‑term memory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "content": {"type": "string", "description": "Short fact to remember (max 200 chars)"}
                        },
                        "required": ["content"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "recall_memory",
                    "description": "Retrieve previously stored facts about the user",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "topic": {"type": "string", "description": "Optional topic to filter memories"}
                        },
                        "required": []
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "extract_entities",
                    "description": "Extract named entities (people, code terms, etc.) from text",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "summarize",
                    "description": "Summarize a long text to a short paragraph",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "text": {"type": "string"}
                        },
                        "required": ["text"]
                    }
                }
            }
        
        ]


    def _execute_tool(self, tool_name: str, arguments: Dict, user_id: str, conv_id: str) -> str:
        if tool_name == "retrieve_docs":
            query = arguments.get("query", "")
            if len(query) > 200:
                query = query[:200]
                print(f"[WARN] Truncated too long query to: {query}")
            if not query:
                return "No search query provided."
            try:
                db = SyncSessionLocal()
                rag = RAGService(db, dense_model, reranker)
                chunks = rag.retrieve(query, top_k=3, use_reranker=True, use_hybrid=True)
                db.close()
                if not chunks:
                    return "No relevant documents found."
                # Combine top 3 chunks, limit total length
                combined = "\n\n".join([text for text, _, _ in chunks])[:2000]
                return combined
            except Exception as e:
                return f"Error retrieving documents: {str(e)}"
        elif tool_name == "classify_issue":
            title = arguments.get("title", "")
            body = arguments.get("body", "")
            text = f"Title: {title}\nBody: {body}"
            from app.model_loader import classifier
            result = classifier(text)[0]
            raw_label = result['label']
            confidence = result.get('score', 0)
            
            # Map Hugging Face labels to our categories
            label_map = {
                "LABEL_0": "bug",
                "LABEL_1": "feature",
                "LABEL_2": "docs",
                "LABEL_3": "question"
            }
            label = label_map.get(raw_label, raw_label)
            
            return f"Classification: {label} (confidence: {confidence:.2f})"
        elif tool_name == "write_memory":
            content = arguments.get("content", "")
            if len(content) > 500:
                content = content[:500]
            db = SyncSessionLocal()
            mem_repo = MemoryRepository(db)
            mem_repo.create_memory(user_id, "episodic", content)
            db.close()
            return "Memory saved"
        elif tool_name == "recall_memory":
            topic = arguments.get("topic", "")
            db = SyncSessionLocal()
            mem_repo = MemoryRepository(db)
            # Get all memories for this user (you may later filter by topic)
            memories = mem_repo.get_memories_by_user(user_id)
            db.close()
            if not memories:
                return "No stored memories found."
            # Format memories
            formatted = []
            for mem in memories[:5]:  # limit to 5 most recent
                formatted.append(f"- {mem.content} (saved on {mem.created_at.strftime('%Y-%m-%d')})")
            return "\n".join(formatted)
        elif tool_name == "extract_entities":
            text = arguments.get("text", "")
            if not text:
                return "No text provided."
            from app.model_loader import ner
            entities = ner(text)
            if not entities:
                return "No entities found."
            # Format: "PER:John, LOC:Paris, CODE:pd.read_csv"
            formatted = []
            for e in entities[:10]:
                word = e['word']
                # Remove leading ## for subwords
                if word.startswith('##'):
                    word = word[2:]
                formatted.append(f"{e['entity_group']}:{word}")
            return "Entities: " + ", ".join(formatted)

        elif tool_name == "summarize":
            text = arguments.get("text", "")
            if len(text) < 20:
                return "Text too short to summarize."
            if len(text) > 4000:
                text = text[:4000]
            prompt = f"Summarize the following text concisely in 2-3 sentences:\n\n{text}\n\nSummary:"
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0.3,
                max_tokens=150
            )
            return response.choices[0].message.content.strip()
        else:
            return f"Unknown tool: {tool_name}"

    from datetime import datetime

    def _ensure_conversation_index(self, user_id: str, conv_id: str, first_message: str):
        from app.infra.redis_client import redis_client
        print(f"[DEBUG] _ensure_conversation_index called: user_id={user_id}, conv_id={conv_id}")

        user_conv_key = f"user:{user_id}:conversations"
        redis_client.sadd(user_conv_key, conv_id)
        meta_key = f"conv_meta:{conv_id}"
        if not redis_client.exists(meta_key):
            title = first_message[:50] + "..." if len(first_message) > 50 else first_message
            redis_client.hset(meta_key, mapping={
                "title": title,
                "last_updated": datetime.now().isoformat()
            })
            print(f"[DEBUG] Created meta {meta_key} with title {title}")

        else:
            redis_client.hset(meta_key, "last_updated", datetime.now().isoformat())
            print(f"[DEBUG] Updated meta {meta_key}")

    async def chat(self, user_id: str, conversation_id: str, message: str) -> str:
        try:
            from app.infra.redis_client import get_conversation, store_conversation
            history = get_conversation(conversation_id)  # list of dicts with 'role' and 'content'

            if not history:  # new 
                self._ensure_conversation_index(user_id, conversation_id, message)
                print(f"[DEBUG] history empty? {not history}")

            messages = history + [{"role": "user", "content": message}]

            # First call: let the model decide if tools are needed
            response = self.groq.chat.completions.create(
                model=self.model,
                messages=messages,
                tools=self._get_tools(),
                tool_choice="auto",
                temperature=0.3
            )

            assistant_msg = response.choices[0].message

            # If there are tool calls, execute them
            if assistant_msg.tool_calls:
                tool_results = []
                for tc in assistant_msg.tool_calls:
                    args = json.loads(tc.function.arguments)
                    result = self._execute_tool(tc.function.name, args, user_id, conversation_id)
                    tool_results.append(f"[{tc.function.name}] result: {result[:1500]}")

                context = "\n\n".join(tool_results)

                # Second call: answer the original user question using the retrieved context
                second_prompt = f"""You are a helpful assistant for a software maintainer. Use the following retrieved information to answer the user's question concisely. If the information is not sufficient, say so.

Retrieved information:
{context}

User's original question: {message}

Answer:"""
                final_response = self.groq.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": second_prompt}],
                    temperature=0.3,
                    max_tokens=500
                )
                reply = final_response.choices[0].message.content.strip()
            else:
                reply = assistant_msg.content


            # Save the conversation (both user message and assistant reply) to Redis
            updated_history = messages + [{"role": "assistant", "content": reply}]
            store_conversation(conversation_id, updated_history, ttl=3600)
            return reply

        except Exception as e:
            error_msg = str(e)
            if "tool_use_failed" in error_msg:
                return "I'm sorry, I had trouble using a tool. Could you rephrase your question?"
            else:
                return f"An error occurred: {error_msg[:200]}"