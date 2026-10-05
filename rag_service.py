import logging
from typing import List, Dict, Tuple, Optional
from langchain_core.messages import BaseMessage, SystemMessage, HumanMessage, AIMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.documents import Document

from config import get_settings
from vector_store import SpringAIPGVectorStore
from models import Quest

logger = logging.getLogger(__name__)
settings = get_settings()

def extract_text_from_ai_message(content) -> str:
    """Safely extracts string content from LangChain AI message content."""
    if content is None:
        return ""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for item in content:
            if isinstance(item, str):
                parts.append(item)
            elif isinstance(item, dict):
                if "text" in item and item["text"] is not None:
                    parts.append(str(item["text"]))
                elif "content" in item and item["content"] is not None:
                    parts.append(str(item["content"]))
                else:
                    parts.append(str(item))
            elif hasattr(item, "text") and item.text is not None:
                parts.append(str(item.text))
            elif hasattr(item, "content") and item.content is not None:
                parts.append(str(item.content))
            else:
                parts.append(str(item))
        return "".join(parts)
    return str(content)

class ConversationMemoryManager:
    """Manages multi-turn conversation memory per conversation_id."""
    def __init__(self):
        self._history: Dict[str, List[BaseMessage]] = {}

    def get_messages(self, conversation_id: str) -> List[BaseMessage]:
        return list(self._history.get(conversation_id, []))

    def add_turn(self, conversation_id: str, user_message: str, ai_message: str):
        if conversation_id not in self._history:
            self._history[conversation_id] = []
        self._history[conversation_id].append(HumanMessage(content=user_message))
        self._history[conversation_id].append(AIMessage(content=ai_message))

    def clear(self, conversation_id: str):
        if conversation_id in self._history:
            self._history[conversation_id] = []
            logger.info(f"Cleared chat memory for conversation_id='{conversation_id}'")

CONVERSATIONAL_KEYWORDS = {
    "yes", "no", "ok", "okay", "yep", "yeah", "sure", "thanks", "thank you",
    "hi", "hello", "hey", "good morning", "good evening", "good afternoon",
    "bye", "goodbye", "cool", "alright", "got it"
}

def is_conversational_query(query: str) -> bool:
    """Returns True if the query is a simple greeting or acknowledgment."""
    clean = query.strip().lower().rstrip("!.?,")
    return clean in CONVERSATIONAL_KEYWORDS

CANDIDATE_FALLBACK_MODELS = [
    "gemini-3.5-flash-lite",
    "gemini-2.5-flash",
    "gemini-2.5-flash-lite",
    "gemini-3.5-flash",
    "gemini-3.8-flash"
]

class AIService:
    """
    Python LangChain equivalent of Spring AI's AIservice.
    Maintains 100% prompt parity, vector search parity, conversation memory,
    and adds low-latency optimizations, resilient multi-model fallbacks, and real-time streaming.
    """

    def __init__(
        self,
        vector_store: Optional[SpringAIPGVectorStore] = None,
        chat_model: Optional[ChatGoogleGenerativeAI] = None,
        memory_manager: Optional[ConversationMemoryManager] = None
    ):
        self.vs = vector_store or SpringAIPGVectorStore()
        self.cc = chat_model or ChatGoogleGenerativeAI(
            model=settings.chat_model,
            google_api_key=settings.google_api_key,
            max_retries=2,
            timeout=25.0
        )
        self.chat_memory = memory_manager or ConversationMemoryManager()

    def asku(self, quest: Quest) -> str:
        """Entrypoint matching Java asku(Quest quest)"""
        conv_id = self.resolve_conversation_id(
            quest.conversationId if quest else None
        )
        question = quest.question if quest and quest.question else ""
        return self.searchres(question, conv_id)

    def searchres(self, que: str, conversation_id: str = "default-session") -> str:
        """Search and synthesize response with conversation memory and vector context."""
        answer, _, _ = self.searchres_with_details(que, conversation_id)
        return answer

    def _prepare_rag_prompt(self, que: str, conv_id: str) -> Tuple[List[BaseMessage], List[str], int]:
        """Prepares retrieved context and LangChain prompt messages."""
        context_builder = []
        sources = []
        retrieved_docs_count = 0

        # Only perform vector search if the query is not a trivial conversational acknowledgment
        if not is_conversational_query(que):
            try:
                threshold = getattr(settings, "similarity_threshold", 0.65)
                db_docs_with_scores = self.vs.similarity_search_with_score(que, k=settings.top_k)
                for doc, score in db_docs_with_scores:
                    if score >= threshold and doc and doc.page_content and doc.page_content.strip():
                        source = (
                            doc.metadata.get("source") or
                            doc.metadata.get("file_name") or
                            doc.metadata.get("filename") or
                            doc.metadata.get("title") or
                            "Uploaded Document"
                        )
                        if source not in sources:
                            sources.append(source)
                        title_info = f" ({doc.metadata['title']})" if doc.metadata.get("title") else ""
                        context_builder.append(
                            f"[{source}{title_info}] (Relevance: {score:.2f}):\n{doc.page_content.strip()}\n\n---\n\n"
                        )
                        retrieved_docs_count += 1
            except Exception as e:
                logger.warning(f"Vector search warning: {e}")

        has_vector_data = len(context_builder) > 0

        if has_vector_data:
            context_snippet = "".join(context_builder).strip()
            data_context_directive = f"""
VECTOR STORE STATUS: RELEVANT DATA FOUND ({retrieved_docs_count} matching snippet(s)).
Prioritize and formulate your answer directly referencing and synthesizing from the Retrieved Documentation Context below.
"""
        else:
            context_snippet = "No matching documentation was found in the vector store for this question."
            data_context_directive = """
VECTOR STORE STATUS: NO RELEVANT DATA FOUND IN VECTOR STORE.

MANDATORY RULES WHEN DATA IS NOT FOUND IN THE VECTOR STORE:
1. DOMAIN CHECK - ANSWER THESE TOPICS FULLY AND EXPERTLY:
   If the user's question relates to ANY of the following domains:
   • Women Empowerment (economic independence, confidence, Self-Help Groups (SHGs), overcoming challenges, community mentorship)
   • Business Ideas (low-investment businesses, home-based businesses, handmade crafts, baking/cloud kitchen, fashion/tailoring, organic food/spices, digital services, beauty & wellness)
   • Profits & Pricing (profit margin calculations, pricing formula: Cost + Packaging + Overhead + Desired Profit Margin, markup %, break-even point, gross vs net profit)
   • Budget Calculations (startup capital allocation, raw materials, equipment, working capital, managing cash flow)
   • Guiding Women to Start a Business (step-by-step launch roadmap: skill identification -> business plan -> registration -> branding & packaging -> pricing -> marketing -> sales & scaling)
   • Government Schemes for Women (PMMY Mudra loans, Stand-Up India, Mahila Samridhi Yojana, Stree Shakti, TREAD, etc.)

   --> ACTION: YOU MUST ANSWER THOROUGHLY, EXPERTLY, AND PRACTICALLY!
   --> Provide concrete mathematical calculations, budget breakdowns with sample rupee (₹) figures, actionable step-by-step guidance, and motivating advice as Lia AI.
   --> You do not need to apologize for missing document context; confidently deliver high-value mentorship.

2. OUT-OF-DOMAIN QUESTIONS:
   If the question is completely UNRELATED to women empowerment, business, profits, budget calculations, or starting a business (e.g. quantum physics, celebrity gossip, sports match scores, unrelated video game lore):
   --> Politely clarify that no relevant information was found in the uploaded documents.
   --> State that as Lia AI, your purpose as the Shepreneur digital mentor is specifically dedicated to women empowerment, business ideas, budget calculations, profit margins, and guiding women to start and scale businesses.
   --> Warmly invite them to ask any question related to business ideas, budgeting, profit calculation, or women entrepreneurship.
"""

        system_prompt = f"""You are Lia AI, an intelligent, inspiring, and versatile AI Knowledge and Digital Business Mentor.
You are the central intelligence and mentor of Shepreneur — an AI-Powered Business Support Platform for Women Entrepreneurs (Tagline: “A Partner, Not Just an App”).

Core Identity & Responsibilities:
1. You act as a supportive, knowledgeable digital business mentor for women entrepreneurs.
2. Ground responses in uploaded documents whenever relevant context is retrieved from the vector store.
3. If data is not found in the vector store, answer all questions related to women empowerment, business ideas, profits, budget calculations, and guiding women to start a business with high-quality, practical, actionable mentorship.
4. Maintain conversational context across previous interactions seamlessly using chat memory.
5. Provide structured, clean markdown output (bullet points, bold highlights, calculation formulas, budget tables where helpful).
6. Multilingual: Fluent in English, Telugu (తెలుగు), Hindi (हिन्दी), Marathi (मराठी), and responds naturally in the user's language and script.

Foundational Shepreneur Knowledge:
- Purpose: Support Indian women entrepreneurs from Skills -> Idea -> Guidance -> Product -> Customer -> Growth.
- Core Platform Modules:
  • Home Dashboard: Central starting point connecting all Shepreneur services.
  • Profile & User Modes: Switch easily between buyer and seller activities.
  • LIA AI Business Mentor: 24/7 intelligent mentorship answering questions on business ideas, marketing, pricing, and scaling.
  • Price Estimation: Formula = (Material + Packaging + Labor + Overheads) + Desired Profit Margin (typically 30%-50%).
  • Government Schemes: Mudra Yojana (Shishu up to ₹50k, Kishore up to ₹5L, Tarun up to ₹10L), Stand-Up India (₹10L - ₹1Cr), Mahila Samridhi Yojana, Stree Shakti Package, TREAD.
  • Marketplace: Buy-and-sell platform for handmade and artisan goods.
- 7-Step User Journey:
  1. Skills / Idea -> 2. Upload / Product Details -> 3. LIA AI Suggestion -> 4. Price Estimation -> 5. Marketplace -> 6. Customer Order -> 7. Delivery & Growth.
- Common Business Inquiries:
  • ₹5,000 budget startups: Handcrafted scented candles, cloud bakery / confectionery, handmade soaps, customized jewellery, organic spice packaging, embroidery & tailoring.
  • Instagram Marketing: Behind-the-scenes creation reels, natural light photography, unboxing packaging, local Indian artisan hashtags, micro-influencer gifting.

{data_context_directive}

Retrieved Documentation Context:
{context_snippet}
"""

        history_messages = self.chat_memory.get_messages(conv_id)
        prompt_messages: List[BaseMessage] = [
            SystemMessage(content=system_prompt),
            *history_messages,
            HumanMessage(content=que)
        ]

        return prompt_messages, sources, retrieved_docs_count


    def searchres_with_details(self, que: str, conversation_id: str = "default-session") -> Tuple[str, List[str], int]:
        """
        Extended method that returns:
        (answer_text, list_of_source_names, retrieved_doc_count)
        """
        conv_id = self.resolve_conversation_id(conversation_id)
        prompt_messages, sources, retrieved_count = self._prepare_rag_prompt(que, conv_id)

        answer = None
        models_to_try = [settings.chat_model] + [
            m for m in CANDIDATE_FALLBACK_MODELS if m != settings.chat_model
        ]

        last_error = None
        for model_name in models_to_try:
            try:
                if model_name == settings.chat_model and self.cc:
                    llm = self.cc
                else:
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=settings.google_api_key,
                        max_retries=1,
                        timeout=15.0
                    )
                response = llm.invoke(prompt_messages)
                extracted = extract_text_from_ai_message(response.content)
                if extracted and extracted.strip():
                    answer = extracted
                    break
            except Exception as err:
                last_error = err
                logger.warning(f"Model '{model_name}' invocation failed: {err}")

        if not answer:
            err_str = str(last_error) if last_error else "Unknown error"
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                answer = (
                    "⚠️ **Gemini Free-Tier Quota Exceeded**: The current API key has reached its "
                    "requests-per-day limit for the selected model. Please wait for the daily quota to reset "
                    "or provide an upgraded Google AI Studio API key in `.env`."
                )
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                answer = (
                    "⚠️ **Service Temporarily Busy**: Google Gemini is experiencing high server demand. "
                    "Please try your question again in a few moments."
                )
            else:
                answer = f"⚠️ **AI Service Notice**: Unable to generate response ({err_str[:180]})."

        # Update chat memory
        self.chat_memory.add_turn(conv_id, que, answer)
        return answer, sources, retrieved_count

    def searchres_stream(self, que: str, conversation_id: str = "default-session"):
        """
        Yields real-time streaming chunks for low-latency perceived response time.
        Yields tuples: (event_type, payload_dict_or_str)
        """
        conv_id = self.resolve_conversation_id(conversation_id)
        prompt_messages, sources, retrieved_count = self._prepare_rag_prompt(que, conv_id)

        yield ("meta", {"sources": sources, "retrieved_count": retrieved_count, "conversation_id": conv_id})

        accumulated_chunks = []
        models_to_try = [settings.chat_model] + [
            m for m in CANDIDATE_FALLBACK_MODELS if m != settings.chat_model
        ]

        stream_success = False
        last_error = None

        for model_name in models_to_try:
            try:
                if model_name == settings.chat_model and self.cc:
                    llm = self.cc
                else:
                    llm = ChatGoogleGenerativeAI(
                        model=model_name,
                        google_api_key=settings.google_api_key,
                        max_retries=1,
                        timeout=15.0
                    )
                
                for chunk in llm.stream(prompt_messages):
                    token_text = extract_text_from_ai_message(chunk.content)
                    if token_text:
                        accumulated_chunks.append(token_text)
                        yield ("token", token_text)

                full_answer = "".join(accumulated_chunks).strip()
                if full_answer:
                    self.chat_memory.add_turn(conv_id, que, full_answer)
                    yield ("done", {"conversation_id": conv_id})
                    stream_success = True
                    break
            except Exception as err:
                last_error = err
                logger.warning(f"Streaming failed on '{model_name}': {err}")

        if not stream_success:
            err_str = str(last_error) if last_error else "Unknown error"
            if "RESOURCE_EXHAUSTED" in err_str or "429" in err_str:
                fallback_msg = (
                    "⚠️ **Gemini Free-Tier Quota Exceeded**: The current API key has reached its "
                    "requests-per-day limit. Please try again later."
                )
            elif "503" in err_str or "UNAVAILABLE" in err_str:
                fallback_msg = (
                    "⚠️ **Service Busy**: Google Gemini is experiencing high server demand. Please retry in a moment."
                )
            else:
                fallback_msg = f"⚠️ **AI Service Notice**: Unable to generate response ({err_str[:160]})."

            yield ("token", fallback_msg)
            self.chat_memory.add_turn(conv_id, que, fallback_msg)
            yield ("done", {"conversation_id": conv_id})

    def clear_memory(self, conversation_id: str):
        """Equivalent to Java clearMemory(String conversationId)"""
        conv_id = self.resolve_conversation_id(conversation_id)
        self.chat_memory.clear(conv_id)

    def resolve_conversation_id(self, conversation_id: Optional[str]) -> str:
        """Equivalent to Java resolveConversationId"""
        if conversation_id is None or not conversation_id.strip():
            return "default-session"
        return conversation_id.strip()
