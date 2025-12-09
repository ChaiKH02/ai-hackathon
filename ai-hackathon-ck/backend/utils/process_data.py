"""
Data Processing Pipeline Script
Processes CSV data through:
1. classify_festival_date - Festival classification
2. get_quarter - Quarter extraction
3. combined_nlp_pipeline - NLP analysis (rephrasing, categories, sentiment)

Saves all results to a new CSV file with original columns preserved.
"""

import pandas as pd
import json
import os
from datetime import datetime
from utils.season_detect import classify_festival_date
from utils.quarter import get_quarter
from utils.nlp_engine import combined_nlp_pipeline, ai_rephrase, ai_extract_categories, ai_evaluate_sentiment, get_sentiment_label
import malaya
import inspect

# Fix for Malaya compatibility
if not hasattr(inspect, 'getargspec'):
    inspect.getargspec = inspect.getfullargspec


def process_single_comment(original_text, corrector, transformer):
    """
    Process a single comment through the NLP pipeline.
    
    Args:
        original_text: Original comment text
        corrector: Malaya normalizer
        transformer: Malaya translator
        
    Returns:
        dict with rephrased, categories, sentiment_score, and sentiment_label
    """
    # Skip empty comments
    if pd.isna(original_text) or (isinstance(original_text, str) and not original_text.strip()):
        return {
            "rephrased": "",
            "categories": "",
            "sentiment_score": 5,
            "sentiment_label": "neutral"
        }
    
    try:
        # Normalize using Malaya
        normalized_dict = corrector.normalize(original_text)
        normalized_text = normalized_dict['normalize']
        
        # Translate using Malaya (MS -> EN)
        translated_text = transformer.generate([normalized_text], to_lang='en')[0]
        
        # Rephrase using AI (maintaining meaning)
        rephrased_text = ai_rephrase(original_text, translated_text)
        
        # Extract categories using AI
        extraction = ai_extract_categories(rephrased_text)
        
        # Evaluate sentiment (AI determines both score and label)
        sentiment = ai_evaluate_sentiment(rephrased_text)
        
        return {
            "rephrased": rephrased_text,
            "categories": extraction.categories,
            "sentiment_score": sentiment.sentiment_score,
            "sentiment_label": sentiment.sentiment_label  # Now from AI, not threshold
        }
    except Exception as e:
        print(f"Error processing comment: {e}")
        return {
            "rephrased": str(original_text),
            "categories": "",
            "sentiment_score": 5,
            "sentiment_label": "neutral"
        }


def process_csv_data(input_csv_path: str, output_csv_path: str):
    """
    Main function to process CSV data through all three functions.
    
    Args:
        input_csv_path: Path to input CSV file
        output_csv_path: Path to save output CSV file
    """
    print("=" * 60)
    print("DATA PROCESSING PIPELINE")
    print("=" * 60)
    
    # Load the CSV file
    print(f"\n[1/5] Loading CSV file: {input_csv_path}")
    df = pd.read_csv(input_csv_path)
    print(f"   ✓ Loaded {len(df)} rows with {len(df.columns)} columns")
    print(f"   Columns: {list(df.columns)}")
    
    # Initialize Malaya models for NLP processing
    print("\n[2/5] Initializing Malaya models...")
    try:
        corrector = malaya.normalize.normalizer(date=False, time=False, money=False)
    except AttributeError:
        corrector = malaya.normalizer.rules.normalizer(date=False, time=False, money=False)
    
    transformer = malaya.translation.huggingface(
        model='mesolitica/translation-t5-base-standard-bahasa-cased'
    )
    print("   ✓ Malaya models loaded")
    
    # Process each row
    print("\n[3/5] Processing data...")
    
    # Step 1: Apply classify_festival_date
    print("   → Applying classify_festival_date...")
    if 'Submission_Date' in df.columns:
        df['Event_Season'] = df['Submission_Date'].apply(
            lambda x: ', '.join(classify_festival_date(x, year=2024)) if pd.notna(x) else "normal day"
        )
        print(f"      ✓ Festival classification complete")
    else:
        print("      ⚠ 'Submission_Date' column not found, skipping festival classification")
        df['Event_Season'] = "normal day"
    
    # Step 2: Apply get_quarter
    print("   → Applying get_quarter...")
    if 'Submission_Date' in df.columns:
        df['Quarter'] = df['Submission_Date'].apply(
            lambda x: get_quarter(x) if pd.notna(x) else ""
        )
        print(f"      ✓ Quarter calculation complete")
    else:
        print("      ⚠ 'Submission_Date' column not found, skipping quarter calculation")
        df['Quarter'] = ""
    
    # Step 3: Apply combined NLP pipeline (comment by comment)
    print("   → Applying NLP pipeline (rephrasing, categories, sentiment)...")
    if 'Comments' in df.columns:
        nlp_results = []
        for idx, comment in enumerate(df['Comments'], 1):
            print(f"      Processing comment {idx}/{len(df)}...", end='\r')
            result = process_single_comment(comment, corrector, transformer)
            nlp_results.append(result)
        
        # Add NLP results to dataframe
        df['Rephrased_Comment'] = [r['rephrased'] for r in nlp_results]
        df['Categories'] = [r['categories'] for r in nlp_results]
        df['Sentiment_Score'] = [r['sentiment_score'] for r in nlp_results]
        df['Sentiment_Label'] = [r['sentiment_label'] for r in nlp_results]
        print(f"\n      ✓ NLP processing complete for {len(df)} comments")
    else:
        print("      ⚠ 'Comments' column not found, skipping NLP pipeline")
        df['Rephrased_Comment'] = ""
        df['Categories'] = ""
        df['Sentiment_Score'] = 5
        df['Sentiment_Label'] = "neutral"
    
    # Save to new CSV
    print(f"\n[4/5] Saving results to: {output_csv_path}")
    df.to_csv(output_csv_path, index=False, encoding='utf-8-sig')
    print(f"   ✓ Saved {len(df)} rows")
    
    # Display summary
    print("\n[5/5] Processing Summary")
    print("=" * 60)
    print(f"Total rows processed: {len(df)}")
    print(f"New columns added:")
    print(f"  - Event_Season")
    print(f"  - Quarter")
    print(f"  - Rephrased_Comment")
    print(f"  - Categories")
    print(f"  - Sentiment_Score")
    print(f"  - Sentiment_Label")
    print("=" * 60)
    
    # Show sample of results
    print("\nSample Results (first 3 rows):")
    print("-" * 60)
    sample_cols = ['Submission_Date', 'Quarter', 'Event_Season', 
                   'Comments', 'Rephrased_Comment', 'Categories', 'Sentiment_Score', 'Sentiment_Label']
    available_cols = [col for col in sample_cols if col in df.columns]
    print(df[available_cols].head(3).to_string())
    print("-" * 60)


if __name__ == "__main__":
    # This script is designed to be imported and called from the upload API
    # If you need to run it standalone, provide input_csv_path and output_csv_path as arguments
    print("This module should be imported and used via the upload API endpoint.")
    print("Use: process_csv_data(input_csv_path, output_csv_path)")

