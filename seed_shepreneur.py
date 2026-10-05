import logging
from database import get_db_pool
from vector_store import SpringAIPGVectorStore
from langchain_core.documents import Document

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s]: %(message)s")
logger = logging.getLogger(__name__)

shepreneur_sections = [
    {
        "title": "Project Overview & Problem Statement",
        "content": """SHEPRENEUR — AI-Powered Business Support Platform for Women Entrepreneurs
Tagline: "A Partner, Not Just an App"

1. PROJECT OVERVIEW:
Shepreneur is a final-year full-stack project created to support Indian women who want to start or grow small and home-based businesses but face barriers such as limited capital, lack of guidance, limited market knowledge, uncertainty about pricing, and difficulty finding relevant government support. The platform brings business guidance, AI assistance, pricing support, government-scheme information, and a simple marketplace experience into one place. Instead of requiring a new entrepreneur to search across many websites and apps, Shepreneur provides a single digital starting point for turning an idea into a practical, sustainable business.

2. PROBLEM STATEMENT:
• Many aspiring women entrepreneurs have useful skills or business ideas but do not know how to take the first step.
• Home-based entrepreneurs often have limited access to mentors, business networks, marketing knowledge, and financial guidance.
• New sellers struggle to decide a reasonable selling price after considering costs, profit, packaging, and shipping expenses.
• Information about government schemes and financial support programs is difficult to discover and understand.
• Existing platforms focus mainly on selling products, rather than supporting the entrepreneur throughout the business journey.

3. VISION:
To create a supportive digital ecosystem where women can move from Skills -> Idea -> Guidance -> Product -> Customer -> Growth with practical AI assistance."""
    },
    {
        "title": "Key Objectives & Core Platform Modules",
        "content": """SHEPRENEUR — KEY OBJECTIVES & PLATFORM MODULES

4. KEY OBJECTIVES:
• Provide an easy-to-use digital platform for aspiring and existing women entrepreneurs.
• Use AI to give contextual business guidance rather than only static information.
• Help users estimate prices and understand potential profit before selling.
• Make relevant government schemes easier to discover.
• Create a simple buy-and-sell marketplace for products.
• Encourage women to confidently start, manage, and grow small businesses.

5. PLATFORM MODULES:
• Home Dashboard: The main dashboard acts as the user's starting point and connects the major Shepreneur services in a simple interface.
• Profile & User Modes: Users can maintain their profile and switch between buyer and seller-oriented activities. The experience is designed around a simple, approachable marketplace model.
• LIA AI Business Mentor: LIA AI is the central intelligence feature of Shepreneur. It is intended to act as a digital business mentor that can answer open-ended questions and provide practical guidance.
• Price Estimation: Users can enter product cost and related details to understand an appropriate selling price, expected profit, and basic pricing logic.
• Government Schemes: A dedicated section presents useful government-support information for entrepreneurs, helping users identify possible schemes, loans, or support opportunities.
• Marketplace: The marketplace allows users to explore products and supports seller-side and buyer-side interactions such as product listings, wishlist, cart, and ordering."""
    },
    {
        "title": "LIA AI — The Intelligent Business Mentor",
        "content": """SHEPRENEUR — LIA AI INTELLIGENT BUSINESS MENTOR

6. LIA AI — THE INTELLIGENT BUSINESS MENTOR:
LIA AI is the heart of Shepreneur. It is not a fixed FAQ chatbot; it is a secure, multilingual AI mentor that understands open-ended questions and provides actionable, step-by-step guidance.

Supported Core Scenarios & Business Inquiries:
• Budget-based startup ideas: "I have ₹5,000. What home business can I start?"
  - LIA AI recommends low-investment ideas: handcrafted scented candles, cold-process soaps, cloud bakery / home confectionery, custom embroidery & tailoring, spice blends & pickles, beaded jewelry & hair scrunchies, or customized gift hampers.
• Social Media Marketing: "How should I market my handmade products on Instagram?"
  - LIA AI advises: Behind-the-scenes reels showing creation process, high-resolution aesthetic product photos in natural light, unboxing experiences, localized hashtags (#HandmadeIndia, #WomenInBusiness), and customer testimonials.
• Pricing Logic: "My product costs ₹100. What price should I keep?"
  - LIA AI explains the cost + profit breakdown: (Material ₹100 + Packaging ₹15 + Shipping/Overhead ₹35 = ₹150 base cost) + 30-50% profit margin = Recommended price ₹195 to ₹225.
• Government Schemes & Subsidies: "Are there government schemes or loans that may help women entrepreneurs?"
  - Details on Mudra Yojana (Shishu/Kishore/Tarun), Stand-Up India, Mahila Samridhi Yojana, and Stree Shakti.
• Sales Growth & Customer Retention: Practical strategies for repeat orders, referral discounts, and seasonal bundling.
• Multilingual Support: Detects and responds naturally in the user's language and native script, including English, Telugu (తెలుగు), Hindi (हिन्दी), Marathi (मराठी), and other Indian languages.
• Conversational Memory: Maintains context across previous questions without losing conversation history."""
    },
    {
        "title": "End-to-End User Journey (7 Steps)",
        "content": """SHEPRENEUR — END-TO-END USER JOURNEY (7 STEPS)

The platform is built around a comprehensive 7-step journey for women entrepreneurs:
Step 1: Skills / Idea — The user identifies an existing skill, product idea, or business opportunity.
Step 2: Upload / Product Details — The user provides product information, dimensions, or images.
Step 3: LIA AI Suggestion — LIA AI provides practical validation, market positioning, target audience advice, and next steps.
Step 4: Price Estimation — The user calculates raw materials, packaging, labor, and profit margins to determine an ideal selling price.
Step 5: Marketplace — The user lists the product in the Shepreneur marketplace or explores other creations.
Step 6: Customer Order — Buyers discover products and place orders through the integrated cart and checkout.
Step 7: Delivery & Growth — The seller manages fulfillment, receives customer feedback, and uses LIA AI's growth guidance to scale."""
    },
    {
        "title": "Government Schemes & Loans for Women Entrepreneurs",
        "content": """SHEPRENEUR — KEY GOVERNMENT SCHEMES & FINANCIAL ASSISTANCE

Detailed information on government schemes accessible through Shepreneur:
1. Pradhan Mantri Mudra Yojana (PMMY):
   • Shishu: Collateral-free loans up to ₹50,000 for starting new micro-enterprises.
   • Kishore: Loans from ₹50,000 up to ₹5,00,000 for purchasing equipment or scaling operations.
   • Tarun: Loans from ₹5,00,000 up to ₹10,00,000 for mature small enterprises.
2. Stand-Up India Scheme:
   • Bank loans between ₹10 Lakhs and ₹1 Crore for greenfield projects set up by women and SC/ST entrepreneurs in manufacturing, services, or trading.
3. Mahila Samridhi Yojana:
   • Microfinance and skill development initiative offering subsidized micro-credit to women entrepreneurs, often through Self-Help Groups (SHGs).
4. Stree Shakti Package (State Bank of India):
   • Concessionary interest rates (0.5% discount) on business loans for women who hold at least 50% ownership in an enterprise.
5. TREAD Scheme (Trade Related Entrepreneurship Assistance and Development):
   • Provides training, counseling, and grants up to 30% of the project cost through NGOs to assist women in trade and business."""
    },
    {
        "title": "Technical Architecture & Security Principles",
        "content": """SHEPRENEUR — TECHNICAL STACK & SECURITY PRINCIPLES

8. TECHNICAL ARCHITECTURE:
• Frontend: Semantic HTML5, CSS3 with an elegant Lavender, White, and Gold aesthetic theme, Vanilla JavaScript, Marked.js for fast markdown parsing.
• Backend API: Python FastAPI with asynchronous request handling and Server-Sent Events (SSE) streaming (/ask/stream).
• Vector Store & Database: Supabase PostgreSQL with the pgvector extension (3072-dimensional cosine similarity indexing).
• AI Intelligence: Google Gemini AI (gemini-3.5-flash-lite for blazing fast sub-second text generation, gemini-embedding-001 for embeddings).
• RAG Pipeline: LangChain Core, ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings, multi-turn memory manager.

9. SECURITY & AI PRINCIPLES:
• Never expose private AI API keys in client-side code; all calls are routed through the secure FastAPI backend.
• Strict input validation and sanitization on all endpoints.
• Responses are dynamically generated through RAG context rather than static hardcoded FAQ strings.
• User sessions and chat memory are isolated by conversation_id."""
    },
    {
        "title": "Impact, Unique Value Proposition & Future Scope",
        "content": """SHEPRENEUR — IMPACT, UNIQUE VALUE PROPOSITION & FUTURE SCOPE

10. EXPECTED IMPACT:
• Bridges the critical information and confidence gap for first-time women entrepreneurs.
• Democratizes access to business mentoring 24/7 without needing an expensive human advisor.
• Enables informed financial and pricing decisions that prevent losses.
• Directly connects home skills to commercial market opportunities.
• Encourages self-reliance (Atmanirbhar Bharat) and women's economic empowerment.

11. UNIQUE VALUE PROPOSITION (UVP):
"A Partner, Not Just an App": Shepreneur is the only platform that combines AI Business Mentoring + Profit/Price Estimation + Government Scheme Discovery + Marketplace in a single unified ecosystem focused on the person behind the business.

12. SAMPLE USE CASE:
A home maker in India who excels at designing children's dresses asks LIA AI how to start selling. LIA AI advises her on target audiences, material costs, and Instagram marketing. She calculates her selling price using the Price Estimation module, explores Mudra loan options for buying a motorized sewing machine, and lists her first batch of dresses on the Shepreneur Marketplace.

13. VISUAL IDENTITY:
Lavender, White, and Gold color palette representing dignity, clarity, and prosperity.

14. FUTURE ENHANCEMENTS:
• Multilingual Voice Assistant in Indian regional languages (Telugu, Hindi, Tamil, Kannada, Marathi).
• Computer Vision for product image quality check and automatic description generation.
• Automated personalized business plans based on user budget and geographical location.
• Order tracking, seller analytics dashboards, and logistics partner integration."""
    }
]

def seed_database():
    logger.info("Connecting to Supabase PostgreSQL database...")
    pool = get_db_pool()
    with pool.connection() as conn:
        with conn.cursor() as cur:
            logger.info("Cleaning old chunks for 'Shepreneur_Project_Documentation.pdf'...")
            cur.execute("DELETE FROM vector_store WHERE metadata->>'source' = 'Shepreneur_Project_Documentation.pdf';")
            conn.commit()

    logger.info("Generating embeddings and adding high-quality Shepreneur chunks into pgvector...")
    vs = SpringAIPGVectorStore()
    documents = []
    for idx, sec in enumerate(shepreneur_sections):
        documents.append(Document(
            page_content=sec["content"],
            metadata={
                "source": "Shepreneur_Project_Documentation.pdf",
                "filename": "Shepreneur_Project_Documentation.pdf",
                "title": sec["title"],
                "section_index": idx + 1,
                "total_sections": len(shepreneur_sections)
            }
        ))

    doc_ids = vs.add_documents(documents)
    logger.info(f"Successfully seeded {len(doc_ids)} pristine Shepreneur knowledge chunks into vector_store!")

if __name__ == "__main__":
    seed_database()
