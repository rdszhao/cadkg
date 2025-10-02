#!/usr/bin/env python3
"""Gradio chat interface for the Unified GraphRAG system."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv
import gradio as gr

sys.path.insert(0, str(Path(__file__).parent))

from unified_graphrag import UnifiedGraphRAG

load_dotenv()


class GraphRAGChatInterface:
    """Gradio chat interface for GraphRAG Q&A."""

    def __init__(self):
        """Initialize the chat interface."""
        # Configuration
        neo4j_uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
        neo4j_user = os.getenv("NEO4J_USER", "neo4j")
        neo4j_password = os.getenv("NEO4J_PASSWORD", "password")

        # Initialize GraphRAG system
        print("Initializing GraphRAG system...")
        self.rag = UnifiedGraphRAG(neo4j_uri, neo4j_user, neo4j_password)
        print("✅ GraphRAG system ready!\n")

    def chat(self, message: str, history: list) -> str:
        """Process a chat message and return response.

        Args:
            message: User's question
            history: Chat history (list of [user_msg, assistant_msg] pairs)

        Returns:
            Assistant's response
        """
        if not message.strip():
            return "Please ask a question about the system."

        try:
            # Get answer from GraphRAG
            answer = self.rag.answer_question(message)
            return answer

        except Exception as e:
            return f"❌ Error: {str(e)}\n\nPlease ensure:\n1. Neo4j is running\n2. Knowledge graph is populated\n3. Ollama models are available"

    def launch(self, share: bool = False, server_port: int = 7860):
        """Launch the Gradio interface.

        Args:
            share: Whether to create a public share link
            server_port: Port to run the server on
        """
        # Create Gradio ChatInterface
        interface = gr.ChatInterface(
            fn=self.chat,
            title="🤖 cadKG - Unified GraphRAG System",
            description="""
Ask questions about the integrated system across CAD, Documentation, and Code domains.

**Example questions:**
- What is the system architecture and how does hardware relate to software?
- What requirements does the system satisfy?
- How do the algorithms and CAD components relate?
- What does the main control module do?
- List all assemblies in the CAD model
- What are the critical requirements?

**Note:** Responses take ~25-45 seconds depending on query complexity.
            """,
            examples=[
                "What is the system architecture?",
                "What requirements does the system satisfy?",
                "How do the algorithms relate to the hardware?",
                "What does the control module do?",
                "List all assemblies in the CAD model",
                "What are the critical requirements?"
            ],
            type="messages",
            theme=gr.themes.Soft(),
        )

        # Launch
        print(f"\n{'='*80}")
        print("🚀 Launching Gradio Chat Interface")
        print(f"{'='*80}\n")
        print(f"📍 Local URL: http://localhost:{server_port}")
        if share:
            print("🌐 Creating public share link...")
        print(f"\n{'='*80}\n")

        interface.launch(
            share=share,
            server_port=server_port,
            server_name="0.0.0.0"
        )


def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Launch Gradio chat interface for GraphRAG system"
    )
    parser.add_argument(
        "--share",
        action="store_true",
        help="Create a public share link"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=7860,
        help="Port to run the server on (default: 7860)"
    )

    args = parser.parse_args()

    # Create and launch interface
    chat_interface = GraphRAGChatInterface()
    chat_interface.launch(share=args.share, server_port=args.port)


if __name__ == "__main__":
    main()
