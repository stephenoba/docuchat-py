import asyncio
import httpx
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))
from app.services.openai import OpenAIService

async def test_ollama_connection():
    service = OpenAIService()
    print(f"Testing connection to Ollama at: {service.base_url}")
    print(f"Using model: {service.model}")
    
    # We'll try to list models as a simple connectivity test
    # Ollama's OpenAI compatible API supports /models
    async with service.get_async_client() as client:
        try:
            response = await client.get("/models")
            if response.status_code == 200:
                print("✅ Successfully connected to Ollama!")
                models = response.json().get("data", [])
                print(f"Available models: {[m['id'] for m in models]}")
                
                # Check if our configured model is available
                if any(m['id'] == service.model for m in models):
                    print(f"✅ Configured model '{service.model}' is available.")
                else:
                    print(f"⚠️  Configured model '{service.model}' not found. Run 'ollama pull {service.model}'")
                
                # Test Embeddings
                print(f"\nTesting embeddings with model: {service.embedding_model}")
                embed_body = {
                    "model": service.embedding_model,
                    "input": "This is a test sentence for embeddings."
                }
                try:
                    embed_response = await client.post("/embeddings", json=embed_body)
                    if embed_response.status_code == 200:
                        print("✅ Embedding request successful!")
                        data = embed_response.json().get("data", [])
                        if data and "embedding" in data[0]:
                            print(f"✅ Received embedding of length: {len(data[0]['embedding'])}")
                        else:
                            print("⚠️  Response successful but no embedding found in data.")
                    else:
                        print(f"❌ Embedding request failed. Status code: {embed_response.status_code}")
                        print(f"Response: {embed_response.text}")
                except Exception as e:
                    print(f"❌ Embedding test failed with error: {str(e)}")

            else:
                print(f"❌ Failed to connect. Status code: {response.status_code}")
                print(f"Response: {response.text}")
        except httpx.ConnectError:
            print("❌ Could not connect to Ollama. Is it running? (Run 'ollama serve')")
        except Exception as e:
            print(f"❌ An error occurred: {str(e)}")

if __name__ == "__main__":
    asyncio.run(test_ollama_connection())
