import os
import json
import re
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# Initialize Gemini API
api_key = os.getenv("GEMINI_API_KEY", "")
is_mock_mode = not api_key or api_key == "YOUR_GEMINI_API_KEY"

if not is_mock_mode:
    genai.configure(api_key=api_key)

def clean_json_string(text):
    """
    Cleans markdown code block wrapper from AI text response to parse it as raw JSON.
    """
    text = text.strip()
    # Remove markdown code fence if present
    match = re.search(r"```(?:json)?\s*(.*?)\s*```", text, re.DOTALL | re.IGNORECASE)
    if match:
        text = match.group(1)
    return text.strip()

def generate_quiz_ai(lesson_title, lesson_desc, lesson_notes=""):
    """
    Generates 5 multiple choice questions (with options A, B, C, D, correct answer, and explanation)
    based on lesson information.
    """
    if is_mock_mode:
        return _get_mock_quiz(lesson_title)
        
    prompt = f"""
    You are an expert educator. Generate a multiple-choice quiz based on the following lesson details.
    
    Lesson Title: {lesson_title}
    Description: {lesson_desc}
    Notes/Content: {lesson_notes}
    
    Requirements:
    1. Generate exactly 5 multiple choice questions.
    2. Each question must have exactly 4 options.
    3. The options must be represented as an array of 4 strings (indices: 0 to 3 correspond to option indices, but identify correct answer as "A", "B", "C", or "D").
    4. Provide a clear, educational explanation for the correct answer.
    5. Return ONLY a valid JSON array, with no other text, markdown formatting (outside of code blocks if you must, but raw JSON is preferred), or introduction.
    
    JSON Schema:
    [
      {{
        "question_text": "Question text here?",
        "options": ["Option A text", "Option B text", "Option C text", "Option D text"],
        "correct_answer": "A",
        "explanation": "Why Option A is correct..."
      }}
    ]
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        cleaned_text = clean_json_string(response.text)
        questions = json.loads(cleaned_text)
        if isinstance(questions, list) and len(questions) > 0:
            # Validate format
            validated = []
            for q in questions[:5]:
                if all(k in q for k in ("question_text", "options", "correct_answer", "explanation")):
                    # Normalize correct answer to uppercase A, B, C, D
                    ans = str(q["correct_answer"]).upper().strip()
                    if ans not in ["A", "B", "C", "D"]:
                        # Fallback mapping if they returned index or text
                        if ans in ["0", "1", "2", "3"]:
                            ans = ["A", "B", "C", "D"][int(ans)]
                        else:
                            ans = "A"
                    q["correct_answer"] = ans
                    validated.append(q)
            if len(validated) > 0:
                return validated
        raise ValueError("Invalid JSON format from Gemini")
    except Exception as e:
        print(f"Gemini Quiz Generation failed: {str(e)}. Falling back to mock quiz.")
        return _get_mock_quiz(lesson_title)

def chat_study_assistant(user_prompt, chat_history, lesson_title=None, lesson_desc=None):
    """
    Chatbot endpoint. Processes student prompt, passing prior messages and current lesson details as context.
    """
    if is_mock_mode:
        return _get_mock_chat_response(user_prompt, lesson_title)
        
    # Build conversation context
    system_instruction = (
        "You are an friendly, empathetic, and highly knowledgeable AI Study Assistant in a Learning Management System (LMS). "
        "Your goal is to help students understand complex concepts, give clear examples, summarize notes, and guide them in their learning. "
        "Keep your responses educational, helpful, clear, and formatted in Markdown. If the student asks something outside of education, "
        "politely guide them back to their studies."
    )
    
    context = ""
    if lesson_title:
        context = f"Context: The student is currently studying the lesson '{lesson_title}' described as: '{lesson_desc}'. Use this context if relevant.\n\n"
        
    history_prompt = "Conversation History:\n"
    for msg in chat_history[-6:]:  # Send last 6 messages to keep context without hitting token limits
        role = "Student" if msg["sender"] == "user" else "Assistant"
        history_prompt += f"{role}: {msg['text']}\n"
        
    prompt = f"{system_instruction}\n\n{context}{history_prompt}\nStudent: {user_prompt}\nAssistant:"
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        return response.text.strip()
    except Exception as e:
        print(f"Gemini Chat Assistant failed: {str(e)}.")
        return f"I'm sorry, I couldn't connect to my AI brain right now. However, regarding your query: '{user_prompt}', here is some general study advice: Make sure to break down the concept into smaller components, review the lesson materials carefully, and try practicing with short quizzes!"

def get_smart_recommendations(enrolled_courses, completed_courses, quiz_scores, interests, all_courses):
    """
    Recommends courses using the Gemini API based on student profile metrics.
    """
    if not all_courses:
        return []
        
    if is_mock_mode:
        return _get_mock_recommendations(enrolled_courses, all_courses)
        
    # Create text descriptions of student profile
    student_profile = {
        "enrolled_courses": [c["course_title"] for c in enrolled_courses],
        "completed_courses": [c["course_title"] for c in completed_courses],
        "average_quiz_score": sum(q["score"]/q["total_questions"]*100 for q in quiz_scores)/len(quiz_scores) if quiz_scores else 0,
        "interests": interests or "Technology, general studies"
    }
    
    courses_pool = [{"id": str(c["_id"]), "title": c["title"], "category": c["category"], "description": c["description"]} for c in all_courses]
    
    prompt = f"""
    You are an AI Recommendation Engine in an LMS. Suggest the best learning path for the student.
    
    Student Profile:
    - Enrolled Courses: {student_profile['enrolled_courses']}
    - Completed Courses: {student_profile['completed_courses']}
    - Quiz Score Average: {student_profile['average_quiz_score']:.1f}%
    - Learning Interests: {student_profile['interests']}
    
    Available Courses Pool:
    {json.dumps(courses_pool, indent=2)}
    
    Requirements:
    1. Select top 3 courses from the Available Courses Pool that the student is NOT already enrolled in (or fewer if total available is less).
    2. Provide a single custom, motivating recommendation message explaining why this course fits their learning profile.
    3. Return ONLY a valid JSON array of objects, each containing 'course_id' and 'recommendation_reason'. No other text.
    
    JSON Schema:
    [
      {{
        "course_id": "course_id_string",
        "recommendation_reason": "Because you completed Python, this intermediate Django course will help you build backend systems."
      }}
    ]
    """
    
    try:
        model = genai.GenerativeModel("gemini-2.5-flash")
        response = model.generate_content(prompt)
        cleaned_text = clean_json_string(response.text)
        recommendations = json.loads(cleaned_text)
        
        # Match back to full course details
        results = []
        for rec in recommendations:
            course = next((c for c in all_courses if str(c["_id"]) == rec["course_id"]), None)
            if course:
                results.append({
                    "course": course,
                    "reason": rec["recommendation_reason"]
                })
        return results
    except Exception as e:
        print(f"Gemini Recommendations failed: {str(e)}. Using mock recommendations.")
        return _get_mock_recommendations(enrolled_courses, all_courses)

# --- Fallback Mock Data Generators ---

def _get_mock_quiz(lesson_title):
    """
    Returns a sample quiz for the course subject.
    """
    return [
        {
            "question_text": f"Which of the following is a primary objective of studying '{lesson_title}'?",
            "options": [
                "To memorize lines of code or details without understanding",
                "To understand the core design principles, structures, and practical logic",
                "To compile applications without compiling engines",
                "To avoid syntax error exceptions entirely"
            ],
            "correct_answer": "B",
            "explanation": f"Studying '{lesson_title}' aims to build deep understanding of concepts, syntax, and logic rather than rote memorization."
        },
        {
            "question_text": "What is the best practice when writing clean and reusable code/notes?",
            "options": [
                "Write everything in a single massive block",
                "Use cryptic abbreviations for variables and terms",
                "Write modular components with meaningful names and docstrings",
                "Ignore commenting since comments decrease runtime speed"
            ],
            "correct_answer": "C",
            "explanation": "Modular, well-named code with descriptive documentation increases readability, ease of testing, and maintainability."
        },
        {
            "question_text": "How can you debug an unexpected error efficiently in this domain?",
            "options": [
                "Reinstall the operating system immediately",
                "Check error logs, set break points, and read stack traces step-by-step",
                "Delete the failing file and rewrite it blindly from scratch",
                "Ignore it and hope the compiler skips the execution line"
            ],
            "correct_answer": "B",
            "explanation": "Inspecting log records, isolating inputs, and reviewing stack traces is the scientific way to resolve development issues."
        },
        {
            "question_text": "What does scalability refer to in application architectures?",
            "options": [
                "Making the UI look larger on widescreen desktop monitors",
                "The system's capacity to handle increased workloads without degrading quality",
                "Writing code in multiple programming languages simultaneously",
                "Generating PDF reports at faster export compression rates"
            ],
            "correct_answer": "B",
            "explanation": "Scalability is the property of a system to handle a growing amount of work by adding computational resources."
        },
        {
            "question_text": "Which utility is most commonly used to store persistent relational or structured data?",
            "options": [
                "A local text notepad file stored in temporary directories",
                "A database system (like MongoDB for documents, or PostgreSQL for tables)",
                "RAM cache registers inside CPU units",
                "System environment variables"
            ],
            "correct_answer": "B",
            "explanation": "Database management systems provide ACID or base-level storage, query optimizations, indexes, and permanent durability."
        }
    ]

def _get_mock_chat_response(prompt, lesson_title):
    """
    Generates a helpful, educational mock chatbot reply.
    """
    prompt_lower = prompt.lower()
    lesson_context = f" relating to your lesson '{lesson_title}'" if lesson_title else ""
    
    if "python" in prompt_lower:
        return (
            f"Here is a quick summary of Python concepts{lesson_context}:\n\n"
            "### Python Key Points\n"
            "- **Dynamic Typing:** You don't need to declare variable types.\n"
            "- **Readability:** Indentation is syntax, making the codebase highly structured.\n\n"
            "### Code Example:\n"
            "```python\n"
            "def greet(name):\n"
            "    # This is a basic greeting function\n"
            "    return f'Hello, {name}! Welcome to the LMS.'\n\n"
            "print(greet('Developer'))\n"
            "```\n"
            "Let me know if you want to know about Lists, Dicts, or Loop structures!"
        )
    elif "react" in prompt_lower or "hook" in prompt_lower:
        return (
            f"React Hooks allow you to use state and other React features without writing a class{lesson_context}:\n\n"
            "### Core Hooks:\n"
            "1. **`useState`**: Tracks component state.\n"
            "2. **`useEffect`**: Performs side effects (API calls, subscriptions, DOM manipulation).\n\n"
            "### Hook Code Example:\n"
            "```javascript\n"
            "import React, { useState } from 'react';\n\n"
            "function Counter() {\n"
            "  const [count, setCount] = useState(0);\n"
            "  return (\n"
            "    <button onClick={() => setCount(count + 1)}>\n"
            "      Count: {count}\n"
            "    </button>\n"
            "  );\n"
            "}\n"
            "```\n"
            "Hooks let you split one component into smaller functions based on what pieces are related!"
        )
    elif "summarize" in prompt_lower or "summary" in prompt_lower:
        return (
            f"Here is a summary of the topic{lesson_context}:\n\n"
            "1. **Core Concept:** The lesson teaches foundational concepts, terminology, and standard implementation steps.\n"
            "2. **Real-World Use Case:** Applying this structure permits scalable systems and efficient computation.\n"
            "3. **Next Steps:** Try reviewing the PDF notes and practicing by completing the lesson quiz!"
        )
    else:
        return (
            f"That's an interesting question regarding '{prompt}'!\n\n"
            "To learn this topic effectively, I suggest checking out these steps:\n"
            "1. **Read Notes:** Open the PDF study guide attached to this lesson.\n"
            "2. **Interactive Practice:** Write simple test functions in python to verify the concepts.\n"
            "3. **Ask AI:** Ask me specific questions, like 'Give me an example of X' or 'Explain line Y' to get a deeper breakdown."
        )

def _get_mock_recommendations(enrolled_courses, all_courses):
    """
    Selects up to 3 courses that are not enrolled, with custom mock recommendations.
    """
    enrolled_ids = {str(c["course_id"]) for c in enrolled_courses}
    results = []
    
    for course in all_courses:
        c_id = str(course["_id"])
        if c_id not in enrolled_ids:
            # Generate recommendation reason
            reason = f"This course in '{course['category']}' is highly recommended to broaden your skillset. Understanding '{course['title']}' is vital for modern tech paths!"
            results.append({
                "course": course,
                "reason": reason
            })
            if len(results) >= 3:
                break
    return results
