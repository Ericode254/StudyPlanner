# 📚 StudyPlanner - AI-Powered Learning Social Network

StudyPlanner is a modern, AI-driven platform designed to help users master any skill through personalized study plans. It combines the power of LLMs (OpenAI & OpenRouter) with social community features and gamification to keep learners motivated.

## 🚀 Key Features

### 🧠 AI-Powered Personalization
- **Multi-Model Support:** Choose your AI "Brain" from OpenAI (GPT-4o, 3.5) or OpenRouter (Gemini, Claude, Llama 3, Mixtral).
- **Smart Resource Discovery:** Describe a roadblock and get 3 targeted, high-quality resources to get you unstuck.
- **AI Quiz Generation:** Instantly generate 5-question knowledge checks based on your specific plan.
- **Adaptive Rescheduling:** Falling behind? The AI will re-balance your remaining tasks to make them manageable.

### 👥 Social Community
- **Public Plan Gallery:** Share your learning journey or get inspired by others.
- **Plan Forking:** One-click clone any public plan to your personal collection.
- **Engagement:** Like and comment on plans to build a collaborative learning environment.

### 🎮 Gamification
- **XP System:** Earn experience points for creating plans, completing milestones, and helping others.
- **Daily Streaks:** Track consecutive days of learning with the "Fire" streak system.
- **Interactive Dashboards:** Personalized home view with recent plans and real-time progress tracking.

### 🎨 Modern UI/UX
- **Responsive Design:** Fully optimized for mobile, tablet, and desktop using Tailwind CSS.
- **Component-Based Architecture:** Reusable Jinja2 templates for a clean, maintainable codebase.
- **Sticky Layout:** Professional navigation and footer placement.

## 🛠️ Tech Stack
- **Backend:** Python / Flask
- **Database:** SQLite / SQLAlchemy
- **Frontend:** Tailwind CSS, jQuery, Showdown.js (Markdown)
- **AI Integration:** OpenAI SDK (configured for both OpenAI and OpenRouter)
- **Auth:** Flask-Login, Authlib (OAuth support)

## 🏁 Quick Start

1. **Environment Setup:**
   Ensure your `.env` file contains:
   ```env
   OPENAI_API_KEY=your_key
   OPENROUTER_API_KEY=your_key
   SECRET_KEY=your_random_secret
   ```

2. **Run the Application:**
   ```bash
   ./.venv/bin/gunicorn -w 1 -b 0.0.0.0:5000 app:app
   ```

3. **Access the App:**
   Open `http://localhost:5000` in your browser.

## 📝 License
This project is licensed under the MIT License - see the LICENSE file for details.