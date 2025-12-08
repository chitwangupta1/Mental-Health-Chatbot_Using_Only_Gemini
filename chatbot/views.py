from django.shortcuts import render
from langchain_google_genai.chat_models import ChatGoogleGenerativeAI
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
import google.generativeai as genai
import os
# Configure Gemini API
gemini_model = ChatGoogleGenerativeAI(
    model="gemini-2.0-flash",
    google_api_key=os.getenv("GOOGLE_API_KEY")  # explicitly pass key
)


import re

def checklist(request):
    return render(request, 'Checklist.html')

def home(request):
    return render(request, 'homepage.html')

def Journal(request):
    return render(request, 'Journal.html')


def moodtracker(request):
    return render(request, 'moodtracker.html')

def motivation(request):
    return render(request, 'motivation.html')

def Resources(request):
    return render(request, 'Resources.html')

def format_gemini_response(text):
    """
    Formats Gemini's raw text to ensure clean bullet points and proper structure.
    """
    # Clean up leading/trailing whitespace
    formatted = text.strip()

    # Normalize line breaks
    formatted = re.sub(r'\r\n|\r', '\n', formatted)

    # Convert numbered lists to bullets (if any)
    formatted = re.sub(r'^\d+\.\s+', '- ', formatted, flags=re.MULTILINE)

    # Convert asterisks or dashes at start to bullets
    formatted = re.sub(r'^(\*|-)\s+', '- ', formatted, flags=re.MULTILINE)

    # Add bullet points to lines that seem like list items but lack formatting
    lines = formatted.split('\n')
    formatted_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith(('-', '•', '*')) and not re.match(r'^\d+\.', stripped) and not stripped.endswith(':'):
            # If it's not a heading or already a list item, bullet it
            formatted_lines.append(f"- {stripped}")
        else:
            formatted_lines.append(line)
    formatted = '\n'.join(formatted_lines)

    # Convert **Bold Headers** (if Gemini gives) to just uppercase
    formatted = re.sub(r'\*\*(.*?)\*\*', lambda m: m.group(1).upper(), formatted)

    # Optional: Capitalize the first letter of each line
    formatted = '\n'.join([line.capitalize() if line else '' for line in formatted.split('\n')])

    return formatted



def chatbot_ui(request):
    return render(request, "index.html")


def get_chat_history(request):
    return request.session.get("chat_history", [])

def update_chat_history(request, user_message, bot_response):
    history = request.session.get("chat_history", [])
    history.append({"user": user_message, "bot": bot_response})
    # Keep only last 3
    request.session["chat_history"] = history[-3:]
    request.session.modified = True


@csrf_exempt
def chatbot_response(request):
    if request.method == "POST":
        data = json.loads(request.body)
        user_input = data.get("message", "")

        # Get last 3 interactions
        history = get_chat_history(request)
        context = ""
        for turn in history:
            context += f"User: {turn['user']}\nBot: {turn['bot']}\n"

        # Add new question
        full_prompt = f"""
        You are a licensed professional psychologist. 
        A psychologist is a mental health professional who studies human behavior, emotions, and thought processes to help individuals understand and manage life challenges, mental health conditions, suggest remedies, nearby help centres or hospital recommendations, etc task-related to treating mental health illness and generally can't prescribe medication.
        Anything else is out of their domain, and they hence couldn't answer that.
        You must respond with **only the direct detailed answer** —no reasoning, no extra sentences. 
        You must answer in a detailed manner with clear points. 
        Use the previous conversation ONLY IF the user's new question is clearly related. If it is NOT related, ignore the past conversation completely and answer directly. 
        Conversation history: {context} New question: {user_input} Answer (no rationale): 
        """
        
        try:
            gemini_response = gemini_model.invoke(full_prompt)
            gemini_text = str(gemini_response.content)
            formatted_gemini_response = format_gemini_response(gemini_text)

            # Save to history
            update_chat_history(request, user_input, formatted_gemini_response)

            return JsonResponse({
                "response": formatted_gemini_response,
                "source": "Gemini"
            })
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)

    return JsonResponse({"error": "Invalid request"}, status=400)


from .models import Feedback

@csrf_exempt
def record_feedback(request):
    print("Feedback endpoint hit")
    if request.method == "POST":
        data = json.loads(request.body)
        response_text = data.get("response", "")
        feedback = data.get("feedback", "")
        original_question = data.get("original_question", "")
        model_used = data.get("model_used", "")
        # print("Feedback received:", feedback)

        if feedback == "down":
            try:
                # Regenerate using context (last 3 turns)
                history = get_chat_history(request)
                context = ""
                for turn in history:
                    context += f"User: {turn['user']}\nBot: {turn['bot']}\n"

                full_prompt = f"""
                You are a licensed psychologist. 
                A psychologist is a mental health professional who studies human behavior, emotions, and thought processes to help individuals understand and manage life challenges, mental health conditions, suggest remedies, nearby help centres or hospital recommendations, etc task-related to treating mental health illness and generally can't prescribe medication.
                Anything else is out of their domain, and they hence couldn't answer that.
                Re-answer the user's question with a better answer than the previous one, with a better consultant aligned to the user's question in a well-defined manner. 
                Do NOT give explanations or rationales. Only provide the answer. You must respond with **only the direct answer** —no reasoning, no extra sentences. 
                You must answer in a detailed manner with clear points. 
                Use past conversation ONLY IF the user's question is related; otherwise,e ignore it. If it is NOT related, ignore the past conversation completely and answer directly. 
                Conversation history: {context} User question: {original_question} 
                Your previous answer (for reference only, do NOT repeat reasoning, do NOT repeat the same answer as previous): {response_text} 
                Provide the corrected answer (no rationale)

                """
# If the user’s query is **not** related to mental health (for example: skincare tips, restaurant recommendations, travel advice, gym routines, coding help, business ideas, etc.), you must respond with:
# "I cannot answer this because it is outside my professional domain."

                gemini_response = gemini_model.invoke(full_prompt)
                formatted_gemini_response = format_gemini_response(str(gemini_response.content))
                # print("Regenerated response:", formatted_gemini_response)

                # ✅ Update chat history (session)
                update_chat_history(request, original_question, formatted_gemini_response)

                # ✅ Save only the regenerated response in DB
                Feedback.objects.update_or_create(
                    question=original_question,
                    defaults={
                        "response": formatted_gemini_response,
                        "feedback": feedback,
                        "model_used": model_used,
                    }
                )

                return JsonResponse({
                    "new_response": formatted_gemini_response,
                    "source": "Gemini"
                })

            except Exception as e:
                return JsonResponse({
                    "error": "Failed to regenerate using Gemini",
                    "details": str(e)
                }, status=500)

        else:
            # 👍 For "up" just record as-is
            Feedback.objects.create(
                question=original_question,
                response=response_text,
                feedback=feedback,
                model_used=model_used,
            )
            return JsonResponse({"status": "feedback recorded"})

    return JsonResponse({"error": "Invalid request"}, status=400)















