import pandas as pd
import re
import os

def clean_text(text):
    if pd.isna(text):
        return text
    text = str(text)
    
    # 1. Remove commas from numbers (e.g. 4,336 -> 4336)
    text = re.sub(r'(?<=\d),(?=\d)', '', text)
    
    # 2. Replace 'w' or 'W' with * 10000
    def replace_w(match):
        val = float(match.group(1)) * 10000
        if val.is_integer():
            return str(int(val))
        return str(val)
        
    text = re.sub(r'(\d+(?:\.\d+)?)[wW]', replace_w, text)
    
    return text

def parse_quote(quote_str):
    res = {
        'quote_video': None,
        'video_cpe': None,
        'video_cpm': None,
        'quote_post': None,
        'post_cpe': None,
        'post_cpm': None
    }
    if pd.isna(quote_str):
        return pd.Series(res)
    
    lines = [line.strip() for line in str(quote_str).split('\n')]
    current_mode = None
    
    for i, line in enumerate(lines):
        if '视频报价' in line:
            current_mode = 'video'
        elif '图文报价' in line:
            current_mode = 'post'
            
        if line == '达人报价' and i + 1 < len(lines):
            val = lines[i+1]
            if current_mode == 'video':
                res['quote_video'] = val
            elif current_mode == 'post':
                res['quote_post'] = val
        elif line == 'CPE' and i + 1 < len(lines):
            val = lines[i+1]
            if current_mode == 'video':
                res['video_cpe'] = val
            elif current_mode == 'post':
                res['post_cpe'] = val
        elif line == 'CPM' and i + 1 < len(lines):
            val = lines[i+1]
            if current_mode == 'video':
                res['video_cpm'] = val
            elif current_mode == 'post':
                res['post_cpm'] = val
                
    # Format to 2 decimal places
    for k in res:
        if res[k] is not None:
            try:
                res[k] = f"{float(res[k]):.2f}"
            except ValueError:
                pass
                
    return pd.Series(res)

def main():
    file_path = r'd:\investment\DMS\DMS001_raw.csv'
    if not os.path.exists(file_path):
        print(f"File not found: {file_path}")
        return
        
    print("Loading data...")
    df = pd.read_csv(file_path)
    
    print("Applying text cleaning (commas and 'w')...")
    # Apply to all string/object columns
    for col in df.columns:
        if pd.api.types.is_string_dtype(df[col]) or pd.api.types.is_object_dtype(df[col]):
            df[col] = df[col].apply(clean_text)
            
    print("Extracting and formatting quote data...")
    # The clean_text already processed the 'quote' column (removing commas and converting 'w')
    # Now we extract
    extracted_df = df['quote'].apply(parse_quote)
    
    # Overwrite the existing columns with the extracted ones in the requested order
    cols_order = ['quote_video', 'video_cpe', 'video_cpm', 'quote_post', 'post_cpe', 'post_cpm']
    for col in cols_order:
        df[col] = extracted_df[col]
        
    print("Broadcasting quote data to all rows for each koc_id...")
    for col in cols_order:
        df[col] = df.groupby('koc_id')[col].transform(lambda x: x.ffill().bfill())
        
    start_col = 'follower_count'
    end_col = 'is_commercial'
    if start_col in df.columns and end_col in df.columns:
        start_idx = df.columns.get_loc(start_col)
        end_idx = df.columns.get_loc(end_col)
        for col in df.columns[start_idx:end_idx + 1]:
            df[col] = pd.to_numeric(df[col], errors='coerce').fillna(0).astype('int64')

    output_path = r'd:\investment\DMS\DMS001_processed.csv'
    df.to_csv(output_path, index=False, encoding='utf-8-sig')
    print(f"Processing complete! Saved to {output_path}")

if __name__ == '__main__':
    main()
