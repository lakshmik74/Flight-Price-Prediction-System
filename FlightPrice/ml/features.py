import pandas as pd
import re

def _parse_duration_to_minutes(duration):
    if pd.isna(duration):
        return 0
    if isinstance(duration, str):
        parts = re.findall(r'\d+', duration)
        if not parts:
            return 0
        if len(parts) >= 2:
            return int(parts[0]) * 60 + int(parts[1])
        return int(parts[0]) * 60
    return int(duration)

def _parse_time_component(value):
    if pd.isna(value):
        return 0
    text = str(value).strip()
    if not text:
        return 0
    if ':' in text:
        parts = text.split(':', 1)
        try:
            return int(parts[0])
        except ValueError:
            digits = re.findall(r'\d+', text)
            return int(digits[0]) if digits else 0
    digits = re.findall(r'\d+', text)
    return int(digits[0]) if digits else 0

def _parse_total_stops(value):
    if pd.isna(value):
        return 0
    text = str(value).lower()
    if 'non-stop' in text or 'non stop' in text:
        return 0
    match = re.search(r'(\d+)', text)
    return int(match.group(1)) if match else 0


def prepare_feature_frame(dataframe):
    data = dataframe.copy()
    data['Date_of_Journey'] = pd.to_datetime(data['Date_of_Journey'], errors='coerce', dayfirst=True)
    data['day'] = data['Date_of_Journey'].dt.day
    data['month'] = data['Date_of_Journey'].dt.month
    data['year'] = data['Date_of_Journey'].dt.year
    data['day_of_week'] = data['Date_of_Journey'].dt.dayofweek

    dep_time = data['Dep_Time'].astype(str).str.split(':', n=1, expand=True)
    arrival_time = data['Arrival_Time'].astype(str).str.split(':', n=1, expand=True)
    data['dep_hour'] = dep_time[0].apply(_parse_time_component)
    data['dep_minute'] = dep_time[1].apply(_parse_time_component)
    data['arrival_hour'] = arrival_time[0].apply(_parse_time_component)
    data['arrival_minute'] = arrival_time[1].apply(_parse_time_component)
    data['duration_minutes'] = data['Duration'].apply(_parse_duration_to_minutes)
    data['Total_Stops'] = data['Total_Stops'].apply(_parse_total_stops)

    data['Airline'] = data['Airline'].astype(str).str.strip()
    data['Source'] = data['Source'].astype(str).str.strip()
    data['Destination'] = data['Destination'].astype(str).str.strip()
    data['Additional_Info'] = data['Additional_Info'].astype(str).str.strip().fillna('No info')

    return data.drop(columns=['Date_of_Journey', 'Dep_Time', 'Arrival_Time', 'Duration', 'Route'], errors='ignore')
