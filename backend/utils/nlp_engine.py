import os
from openai import OpenAI
import pandas as pd
import json
from typing import List, Optional
from huggingface_hub import login
from dotenv import load_dotenv
from pydantic import BaseModel, Field
import malaya
import inspect

# Fix for Malaya compatibility
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec

load_dotenv()

# Initialize OpenAI client for Ollama
client = OpenAI(
    base_url="http://localhost:11434/v1", 
    api_key="ollama" 
)

# HuggingFace login
hf_token = os.environ.get('HF_TOKEN')
if hf_token:
    login(hf_token, add_to_git_credential=True)


# ==================== Pydantic Models ====================

class ExtractionResponse(BaseModel):
    """Model for keyword and category extraction response"""
    categories: str = Field(
        default="", 
        description="High-level categories or themes (e.g., service, product, complaint, praise)"
    )


class SentimentResponse(BaseModel):
    """Model for sentiment evaluation response"""
    sentiment_score: int = Field(
        ..., 
        ge=1, 
        le=10,
        description="Sentiment score from 1 (extremely negative) to 10 (very positive)"
    )


class CommentAnalysis(BaseModel):
    """Model for complete comment analysis output"""
    original: str = Field(..., description="Original comment in Malay/Manglish")
    rephrased: str = Field(..., description="Rephrased professional English version")
    categories: str = Field(
        default="", 
        description="Identified categories"
    )
    sentiment_score: int = Field(
        default=5, 
        description="Sentiment score from 1 (extremely negative) to 10 (very positive)"
    )


# ==================== Combined NLP Pipeline ====================

def combined_nlp_pipeline(df_path: str) -> str:
    """
    Complete NLP pipeline that:
    1. Uses Malaya to normalize and translate (nlp_engine_local)
    2. Uses AI to rephrase maintaining meaning (nlp_engine_ai)
    3. Extracts categories using AI
    
    Args:
        df_path: Path to CSV file with 'Comments' column
        
    Returns:
        JSON string with structured analysis results
    """
    try:
        # ===== STEP 1: Load Data =====
        df = pd.read_csv(df_path)
        if "Comments" not in df.columns:
            return json.dumps({"error": "Column 'Comments' not found"})
        
        # Take top 4 rows
        df_subset = df.head(4).copy()
        
        # ===== STEP 2: Initialize Malaya Models =====
        print("Loading Malaya Normalizer...")
        try:
            corrector = malaya.normalize.normalizer(date=False, time=False, money=False)
        except AttributeError:
            corrector = malaya.normalizer.rules.normalizer(date=False, time=False, money=False)
        
        print("Loading Malaya MS->EN Transformer...")
        transformer = malaya.translation.huggingface(
            model='mesolitica/translation-t5-base-standard-bahasa-cased'
        )
        
        # ===== STEP 3: Process Each Comment =====
        results = []
        
        for original_text in df_subset['Comments']:
            # Skip empty comments
            if pd.isna(original_text) or (isinstance(original_text, str) and not original_text.strip()):
                results.append({
                    "original": original_text or "",
                    "rephrased": "",
                    "categories": []
                })
                continue
            
            # 3A: Normalize using Malaya
            normalized_dict = corrector.normalize(original_text)
            normalized_text = normalized_dict['normalize']
            
            # 3B: Translate using Malaya (MS -> EN)
            translated_text = transformer.generate([normalized_text], to_lang='en')[0]
            print(translated_text)
            
            # 3C: Rephrase using AI (maintaining meaning)
            rephrased_text = ai_rephrase(original_text, translated_text)
            
            # 3D: Extract categories using AI
            extraction = ai_extract_categories(rephrased_text)
            
            # 3E: Evaluate sentiment
            sentiment = ai_evaluate_sentiment(rephrased_text)
            
            # 3F: Create structured output
            analysis = CommentAnalysis(
                original=original_text,
                rephrased=rephrased_text,
                categories=extraction.categories,
                sentiment_score=sentiment.sentiment_score
            )
            
            results.append(analysis.model_dump())
        
        # ===== STEP 4: Return JSON Output =====
        return json.dumps(results, indent=5, ensure_ascii=False)
    
    except FileNotFoundError:
        return json.dumps({"error": "File not found"})
    except Exception as e:
        return json.dumps({"error": str(e)})


def ai_rephrase(original_comment: str, translated_comment: str) -> str:
    """
    Uses AI to rephrase the comment professionally while maintaining meaning.
    
    Args:
        original_comment: Original Malay/Manglish comment
        translated_comment: Machine-translated English version
        
    Returns:
        Professionally rephrased English comment
    """
    prompt = f"""You are a professional text editor as a Malaysian. Given an original comment in Malay/Manglish and its machine translation, rewrite the comment into clear, natural, professional English. Preserve the exact meaning and sentiment. Do NOT add or remove any information.

Original: "{original_comment}"
Translation: "{translated_comment}"

Output ONLY the refined English version.
"""

    try:
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=150,
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        # Fallback to translated version if AI fails
        return translated_comment


# ---------------------- Risk Engine ----------------------
def ai_extract_categories(comment: str) -> ExtractionResponse:
    """
    Uses AI to identify categories from a comment.
    
    Args:
        comment: The rephrased English comment
        
    Returns:
        ExtractionResponse with categories only
    """
    prompt = f""" You are a professional HR analyst.
Analyze the following employee comment and generate 1 high-level CATEGORY that best describes the main theme expressed by the employee.

The categories should:
- Be abstract, high-level themes (e.g., "service quality", "work environment", "leadership", "communication issues", "process inefficiency", etc.)
- Be derived entirely from the content of the comment.
- NOT be restricted to any predefined list.
- Capture the main topic or concern/compliment highlighted in the comment.
- Be concise and specific that GOOD or BAD.

Comment: "{comment}"

Respond in JSON format with one field:
- "categories": string with exactly 1 category

Example format:
{{
    "categories": "workload stress high"
}}

Output ONLY valid JSON, nothing else.
"""

    try:
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=30,
        )
        
        # Parse JSON response
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        data = json.loads(content)
        
        return ExtractionResponse(
            categories=data.get("categories", "")
        )
    except Exception as e:
        print(f"Error extracting categories: {e}")
        # Return empty extraction on error
        return ExtractionResponse(categories="")


def ai_evaluate_sentiment(cleaned_comment: str) -> SentimentResponse:
    """
    Uses AI to evaluate sentiment score from a professionally rewritten comment.
    
    Args:
        cleaned_comment: The rephrased/cleaned English comment from combine_nlp_pipeline
        
    Returns:
        SentimentResponse with sentiment_score (1-10)
    """
    prompt = f"""You are a neutral sentiment evaluator.  
Given a professionally rewritten comment, assign a sentiment score from 1 to 10.

Scoring Guidelines:
1-2: Extremely negative
3-4: Negative
5-6: Neutral
7-8: Positive
9-10: Very positive

Comment: "{cleaned_comment}"

Respond ONLY in JSON:
{{
  "sentiment_score": <number>
}}
"""

    try:
        response = client.chat.completions.create(
            model="llama3.2",
            messages=[
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=20,
        )
        
        # Parse JSON response
        content = response.choices[0].message.content.strip()
        
        # Remove markdown code blocks if present
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()
        
        data = json.loads(content)
        
        return SentimentResponse(
            sentiment_score=data.get("sentiment_score", 5)
        )
    except Exception as e:
        print(f"Error evaluating sentiment: {e}")
        # Return neutral score on error
        return SentimentResponse(sentiment_score=5)


# ==================== Example Usage ====================

if __name__ == "__main__":
    # Test the combined pipeline
    result = combined_nlp_pipeline("../mock/mock_data.csv")
    print(result)
    
    # To use the output programmatically:
    # analyses = json.loads(result)
    # for analysis in analyses:
    #     print(f"Original: {analysis['original']}")
    #     print(f"Rephrased: {analysis['rephrased']}")
    #     print(f"Categories: {analysis['categories']}")
    #     
    #     # Evaluate sentiment on the rephrased comment
    #     sentiment = ai_evaluate_sentiment(analysis['rephrased'])
    #     print(f"Sentiment Score: {sentiment.sentiment_score}")
    #     print("-" * 50)