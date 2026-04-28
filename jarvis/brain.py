"""AI Brain for Jarvis using LangChain and Ollama."""
from langchain_ollama import OllamaLLM
from langchain_core.prompts import ChatPromptTemplate
from jarvis.config import OLLAMA_MODEL
from jarvis.logger import logger

class BrainManager:
    """Manages AI conversation logic."""

    def __init__(self):
        """Initialize the LLM and prompt template."""
        self.model = OllamaLLM(model=OLLAMA_MODEL)
        self.history = []

        # Template for summarizing answers as per original requirement
        template = """
        Answer the following question in summarized form.

        Here's the conversation history: {context}

        Question: {question}

        Answer:
        """
        self.prompt = ChatPromptTemplate.from_template(template)
        self.chain = self.prompt | self.model

    def generate_response(self, question: str) -> str:
        """
        Generate a response based on conversation history and the new question.

        Args:
            question: The user's input text.

        Returns:
            str: The AI's generated response.
        """
        if not question:
            return "I didn't hear anything."

        logger.info(f"[BRAIN_QUERY] Question: {question}")

        # Build context from history
        context = "\n".join(self.history)

        try:
            response = self.chain.invoke({
                "context": context,
                "question": question
            })

            # Update history
            self.history.append(f"User: {question}")
            self.history.append(f"Assistant: {response}")

            # Keep history manageable (last 10 interactions)
            if len(self.history) > 20:
                self.history = self.history[-20:]

            return response
        except Exception as exc:
            logger.error(f"[BRAIN_ERROR] Message: {exc}")
            return f"I encountered an error while thinking: {exc}"

    def add_to_history(self, user_text: str, assistant_text: str) -> None:
        """Manually add an interaction to history."""
        self.history.append(f"User: {user_text}")
        self.history.append(f"Assistant: {assistant_text}")
